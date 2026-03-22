"""Tests for CSV import into entity registry."""

import json
from pathlib import Path

import pytest

from folio.entity_import import ImportResult, import_csv
from folio.tracking.entities import EntityEntry, EntityRegistry


def _make_csv(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _make_registry(tmp_path: Path) -> EntityRegistry:
    reg = EntityRegistry(tmp_path / "entities.json")
    reg.load()
    return reg


# ---------------------------------------------------------------------------
# Basic import
# ---------------------------------------------------------------------------

class TestImportBasic:
    def test_import_minimal_csv(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name\nAlice Chen\nBob Martinez\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.people_imported == 2
        assert reg.entity_count() == 2

    def test_import_full_csv(self, tmp_path):
        csv_path = Path(__file__).parent / "fixtures" / "test_org_chart.csv"
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.people_imported == 5
        assert result.departments_created == 3
        assert reg.get_entity("person", "alice_chen") is not None
        assert reg.get_entity("department", "engineering") is not None

    def test_import_empty_csv(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        _make_csv(csv_path, "name\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.people_imported == 0
        assert reg.entity_count() == 0

    def test_import_idempotent(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,title\nAlice Chen,CEO\n")
        reg = _make_registry(tmp_path)
        result1 = import_csv(reg, csv_path)
        assert result1.people_imported == 1

        # Second import — should skip
        result2 = import_csv(reg, csv_path)
        assert result2.people_imported == 0
        assert result2.people_skipped == 1
        assert reg.entity_count() == 1


# ---------------------------------------------------------------------------
# Department handling
# ---------------------------------------------------------------------------

class TestImportDepartments:
    def test_import_department_auto_creation(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,department\nAlice,Engineering\nBob,Operations\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.departments_created == 2
        assert reg.get_entity("department", "engineering") is not None
        assert reg.get_entity("department", "operations") is not None


# ---------------------------------------------------------------------------
# reports_to resolution
# ---------------------------------------------------------------------------

class TestImportReportsTo:
    def test_import_reports_to_resolution(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,reports_to\nAlice Chen,\nBob Martinez,Alice Chen\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        bob = reg.get_entity("person", "bob_martinez")
        assert bob.reports_to == "alice_chen"

    def test_import_reports_to_unresolved(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,reports_to\nAlice,Unknown Boss\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        alice = reg.get_entity("person", "alice")
        assert alice.reports_to == "Unknown Boss"
        assert any("not found" in w for w in result.warnings)

    def test_import_reports_to_order_independent(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        # Bob references Alice but appears first
        _make_csv(csv_path, "name,reports_to\nBob,Alice\nAlice,\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        bob = reg.get_entity("person", "bob")
        assert bob.reports_to == "alice"


# ---------------------------------------------------------------------------
# Duplicate handling
# ---------------------------------------------------------------------------

class TestImportDuplicates:
    def test_import_duplicate_skip(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,title\nAlice Chen,CEO\n")
        reg = _make_registry(tmp_path)
        # Pre-populate
        reg.add_entity(EntityEntry(
            canonical_name="Alice Chen",
            type="person",
            source="import",
            title="CEO",
        ))
        reg.save()
        result = import_csv(reg, csv_path)
        assert result.people_skipped == 1

    def test_import_duplicate_update(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,title\nAlice Chen,CEO\n")
        reg = _make_registry(tmp_path)
        # Pre-populate without title
        reg.add_entity(EntityEntry(
            canonical_name="Alice Chen",
            type="person",
            source="import",
        ))
        reg.save()
        result = import_csv(reg, csv_path)
        assert result.people_updated == 1
        alice = reg.get_entity("person", "alice_chen")
        assert alice.title == "CEO"

    def test_import_upgrades_extracted_entity(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,title\nAlice Chen,CEO\n")
        reg = _make_registry(tmp_path)
        # Pre-populate as extracted/unconfirmed
        reg.add_entity(EntityEntry(
            canonical_name="Alice Chen",
            type="person",
            source="extracted",
            needs_confirmation=True,
        ))
        reg.save()
        result = import_csv(reg, csv_path)
        assert result.people_updated == 1
        alice = reg.get_entity("person", "alice_chen")
        assert alice.source == "import"
        assert alice.needs_confirmation is False

    def test_import_alias_collision_warning(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name\nJane\n")
        reg = _make_registry(tmp_path)
        # Pre-populate with alias "jane"
        reg.add_entity(EntityEntry(
            canonical_name="Jane Smith",
            type="person",
            aliases=["Jane"],
            source="import",
        ))
        reg.save()
        result = import_csv(reg, csv_path)
        assert any("collision" in w.lower() or "collides" in w.lower() for w in result.warnings)

    def test_import_duplicate_rows(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name\nAlice\nAlice\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.people_imported == 1
        assert any("duplicate" in w.lower() for w in result.warnings)

    def test_import_slug_collision_skips_row(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name\nJane  Smith\n")  # double space
        reg = _make_registry(tmp_path)
        reg.add_entity(EntityEntry(
            canonical_name="Jane Smith",
            type="person",
            source="import",
        ))
        reg.save()
        result = import_csv(reg, csv_path)
        # "Jane  Smith" produces same slug as "Jane Smith"
        # Should be treated as an update (existing entity)
        assert reg.entity_count() == 1


# ---------------------------------------------------------------------------
# Aliases
# ---------------------------------------------------------------------------

class TestImportAliases:
    def test_import_aliases_semicolon_split(self, tmp_path):
        csv_path = tmp_path / "people.csv"
        _make_csv(csv_path, "name,aliases\nAlice Chen,Alice;the CEO;AC\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        alice = reg.get_entity("person", "alice_chen")
        assert "Alice" in alice.aliases
        assert "the CEO" in alice.aliases
        assert "AC" in alice.aliases


# ---------------------------------------------------------------------------
# Encoding / parsing edge cases
# ---------------------------------------------------------------------------

class TestImportEncoding:
    def test_import_utf8_bom(self, tmp_path):
        csv_path = tmp_path / "bom.csv"
        bom = b"\xef\xbb\xbf"
        csv_path.write_bytes(bom + b"name\nAlice Chen\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.people_imported == 1

    def test_import_non_utf8_error(self, tmp_path):
        csv_path = tmp_path / "latin.csv"
        csv_path.write_bytes(b"name\n\xff\xfe\n")
        reg = _make_registry(tmp_path)
        with pytest.raises(ValueError, match="UTF-8"):
            import_csv(reg, csv_path)

    def test_import_malformed_row_warning(self, tmp_path):
        csv_path = tmp_path / "short.csv"
        _make_csv(csv_path, "name,title,department\nAlice\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.people_imported == 1
        assert any("fewer columns" in w for w in result.warnings)

    def test_import_unparseable_row_aborts(self, tmp_path):
        csv_path = tmp_path / "bad.csv"
        # csv module in Python is lenient, so we test missing name column
        _make_csv(csv_path, "title,department\nCEO,Exec\n")
        reg = _make_registry(tmp_path)
        with pytest.raises(ValueError, match="Missing required 'name' column"):
            import_csv(reg, csv_path)

    def test_import_unrecognized_columns_warning(self, tmp_path):
        csv_path = tmp_path / "extra.csv"
        _make_csv(csv_path, "name,location,phone\nAlice,NYC,555-1234\n")
        reg = _make_registry(tmp_path)
        result = import_csv(reg, csv_path)
        assert result.people_imported == 1
        assert any("location" in w for w in result.warnings)
        assert any("phone" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Batch rollback
# ---------------------------------------------------------------------------

class TestImportBatchRollback:
    def test_import_batch_rollback(self, tmp_path):
        """Bad encoding should prevent any writes."""
        csv_path = tmp_path / "bad_encoding.csv"
        csv_path.write_bytes(b"\xff\xfe" + b"name\nAlice\n")
        reg = _make_registry(tmp_path)
        with pytest.raises(ValueError):
            import_csv(reg, csv_path)
        assert reg.entity_count() == 0
