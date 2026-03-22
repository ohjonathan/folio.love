"""Tests for entity registry core module."""

import json
import os
import stat
from pathlib import Path

import pytest

from folio.tracking.entities import (
    EntityAliasCollisionError,
    EntityAmbiguousError,
    EntityEntry,
    EntityRegistry,
    EntityRegistryError,
    EntitySchemaVersionError,
    EntitySlugCollisionError,
    entity_from_dict,
    sanitize_wikilink_name,
    slugify,
)


def _sample_entity(**overrides) -> EntityEntry:
    defaults = dict(
        canonical_name="Jane Smith",
        type="person",
        aliases=[],
        needs_confirmation=False,
        source="import",
    )
    defaults.update(overrides)
    return EntityEntry(**defaults)


# ---------------------------------------------------------------------------
# Slugify / sanitize
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_entity_key_derivation(self):
        assert slugify("Jane Smith") == "jane_smith"
        assert slugify("SAP ERP") == "sap_erp"
        assert slugify("Incident Triage") == "incident_triage"
        assert slugify("Jane  Smith") == "jane_smith"
        assert slugify("  Jane Smith  ") == "jane_smith"

    def test_wikilink_sanitization(self):
        assert sanitize_wikilink_name("Jane [Smith]") == "Jane Smith"
        assert sanitize_wikilink_name("Dept|Eng") == "DeptEng"
        assert sanitize_wikilink_name("Topic#Heading") == "TopicHeading"
        assert sanitize_wikilink_name("Item^ref") == "Itemref"
        assert sanitize_wikilink_name("  padded  ") == "padded"


# ---------------------------------------------------------------------------
# EntityEntry
# ---------------------------------------------------------------------------

class TestEntityEntry:
    def test_to_dict_excludes_none(self):
        entry = _sample_entity()
        d = entry.to_dict()
        assert "title" not in d
        assert "department" not in d
        assert "proposed_match" not in d

    def test_to_dict_preserves_empty_aliases(self):
        entry = _sample_entity(aliases=[])
        d = entry.to_dict()
        assert "aliases" in d
        assert d["aliases"] == []

    def test_entity_from_dict_filters_unknown(self):
        d = {
            "canonical_name": "Test",
            "type": "person",
            "unknown_field": "should be ignored",
        }
        entry = entity_from_dict(d)
        assert entry.canonical_name == "Test"
        assert not hasattr(entry, "unknown_field")


# ---------------------------------------------------------------------------
# EntityRegistry — basic CRUD
# ---------------------------------------------------------------------------

class TestEntityRegistryCRUD:
    def test_empty_registry_creation(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        assert reg.entity_count() == 0
        reg.save()
        data = json.loads((tmp_path / "entities.json").read_text())
        assert data["_schema_version"] == 1
        assert len(data["entities"]["person"]) == 0

    def test_add_entity_basic(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        entry = _sample_entity()
        key = reg.add_entity(entry)
        assert key == "jane_smith"
        assert reg.entity_count() == 1

    def test_add_entity_with_aliases(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        entry = _sample_entity(aliases=["Jane", "the CTO", "J. Smith"])
        key = reg.add_entity(entry)
        assert key == "jane_smith"
        retrieved = reg.get_entity("person", key)
        assert "Jane" in retrieved.aliases
        assert "the CTO" in retrieved.aliases

    def test_add_entity_duplicate_key(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        with pytest.raises(EntitySlugCollisionError):
            reg.add_entity(_sample_entity())

    def test_slug_collision_rejected(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Jane Smith"))
        with pytest.raises(EntitySlugCollisionError, match="jane_smith"):
            reg.add_entity(_sample_entity(canonical_name="Jane  Smith"))

    def test_slug_collision_across_types_allowed(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Operations", type="department"))
        reg.add_entity(_sample_entity(canonical_name="Operations", type="process"))
        assert reg.entity_count() == 2

    def test_alias_collision_detection(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Jane Smith", aliases=["Jane"]))
        with pytest.raises(EntityAliasCollisionError):
            reg.add_entity(
                _sample_entity(canonical_name="John Doe", aliases=["Jane"])
            )

    def test_first_seen_preserved_on_update(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        entry = _sample_entity(first_seen="2025-01-01T00:00:00Z")
        reg.add_entity(entry)
        reg.update_entity("person", "jane_smith", {"title": "CTO"})
        updated = reg.get_entity("person", "jane_smith")
        assert updated.first_seen == "2025-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# EntityRegistry — lookup
# ---------------------------------------------------------------------------

class TestEntityRegistryLookup:
    def test_lookup_exact_match(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        results = reg.lookup("Jane Smith")
        assert len(results) == 1
        assert results[0][0] == "person"
        assert results[0][1] == "jane_smith"

    def test_lookup_alias_match(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(aliases=["Jane"]))
        results = reg.lookup("Jane")
        assert len(results) == 1

    def test_lookup_case_insensitive(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        results = reg.lookup("jane smith")
        assert len(results) == 1
        results = reg.lookup("JANE SMITH")
        assert len(results) == 1

    def test_lookup_confirmed_only(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(needs_confirmation=True))
        results = reg.lookup("Jane Smith", confirmed_only=True)
        assert len(results) == 0
        results = reg.lookup("Jane Smith", confirmed_only=False)
        assert len(results) == 1

    def test_lookup_no_match(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        results = reg.lookup("John Doe")
        assert len(results) == 0

    def test_lookup_ambiguous_within_type(self, tmp_path):
        """Two entities in different types with same name → ambiguous."""
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(canonical_name="Operations", type="department"))
        reg.add_entity(_sample_entity(canonical_name="Operations", type="process"))
        results = reg.lookup("Operations")
        assert len(results) == 2

        with pytest.raises(EntityAmbiguousError):
            reg.lookup_unique("Operations")

        # With type filter → unique
        result = reg.lookup_unique("Operations", entity_type="department")
        assert result is not None
        assert result[0] == "department"


# ---------------------------------------------------------------------------
# EntityRegistry — confirmation
# ---------------------------------------------------------------------------

class TestEntityRegistryConfirmation:
    def test_confirm_entity(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(
            needs_confirmation=True,
            proposed_match="some_key"
        ))
        assert reg.unconfirmed_count() == 1
        changed = reg.confirm_entity("person", "jane_smith")
        assert changed is True
        assert reg.unconfirmed_count() == 0
        entity = reg.get_entity("person", "jane_smith")
        assert entity.needs_confirmation is False
        assert entity.proposed_match is None

    def test_confirm_already_confirmed(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity(needs_confirmation=False))
        changed = reg.confirm_entity("person", "jane_smith")
        assert changed is False


# ---------------------------------------------------------------------------
# EntityRegistry — durability
# ---------------------------------------------------------------------------

class TestEntityRegistryDurability:
    def test_atomic_write(self, tmp_path):
        reg = EntityRegistry(tmp_path / "entities.json")
        reg.load()
        reg.add_entity(_sample_entity())
        reg.save()

        # Reload and verify
        reg2 = EntityRegistry(tmp_path / "entities.json")
        reg2.load()
        assert reg2.entity_count() == 1
        entity = reg2.get_entity("person", "jane_smith")
        assert entity.canonical_name == "Jane Smith"

    def test_corrupt_json_error(self, tmp_path):
        path = tmp_path / "entities.json"
        path.write_text("not valid json{{{")
        reg = EntityRegistry(path)
        with pytest.raises(EntityRegistryError, match="Cannot parse"):
            reg.load()

    def test_invalid_entry_skipped(self, tmp_path):
        path = tmp_path / "entities.json"
        data = {
            "_schema_version": 1,
            "entities": {
                "person": {
                    "valid": {"canonical_name": "Valid", "type": "person", "aliases": []},
                    "invalid": {"aliases": []},  # missing canonical_name
                },
                "department": {},
                "system": {},
                "process": {},
            },
        }
        path.write_text(json.dumps(data))
        reg = EntityRegistry(path)
        reg.load()
        assert reg.entity_count() == 1
        assert reg.get_entity("person", "valid") is not None
        assert reg.get_entity("person", "invalid") is None

    def test_schema_version_migration(self, tmp_path):
        path = tmp_path / "entities.json"
        data = {
            "_schema_version": 1,
            "entities": {
                "person": {"js": {"canonical_name": "JS", "type": "person", "aliases": []}},
                "department": {},
                "system": {},
                "process": {},
            },
        }
        path.write_text(json.dumps(data))
        reg = EntityRegistry(path)
        reg.load()
        assert reg.entity_count() == 1

    def test_schema_version_too_new(self, tmp_path):
        path = tmp_path / "entities.json"
        data = {"_schema_version": 999, "entities": {}}
        path.write_text(json.dumps(data))
        reg = EntityRegistry(path)
        with pytest.raises(EntitySchemaVersionError, match="999"):
            reg.load()

    def test_read_only_fallback(self, tmp_path):
        path = tmp_path / "entities.json"
        reg = EntityRegistry(path)
        reg.load()
        reg.add_entity(_sample_entity())

        # Make directory read-only to prevent write
        path.parent.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            with pytest.raises(OSError):
                reg.save()
        finally:
            path.parent.chmod(stat.S_IRWXU)
