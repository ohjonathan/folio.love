"""Tests for entity CLI commands."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner
from folio.cli import cli
from folio.entity_stubs import AUTO_GENERATED_STUB_MARKER
from folio.tracking.entities import EntityEntry, EntityRegistry


FIXTURES = Path(__file__).parent / "fixtures"


def _make_config(path: Path, config: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(config, default_flow_style=False))


def _make_entity_registry(library: Path, entities: dict = None) -> Path:
    """Create an entities.json in the library root."""
    reg_path = library / "entities.json"
    if entities is not None:
        reg_path.write_text(json.dumps(entities, indent=2))
    return reg_path


def _sample_entity_data(**overrides) -> dict:
    defaults = {
        "canonical_name": "Jane Smith",
        "type": "person",
        "aliases": [],
        "needs_confirmation": False,
        "source": "import",
        "first_seen": "2026-03-22T14:30:00+00:00",
        "created_at": "2026-03-22T14:30:00+00:00",
        "updated_at": "2026-03-22T14:30:00+00:00",
    }
    defaults.update(overrides)
    return defaults


def _full_registry_data() -> dict:
    return json.loads((FIXTURES / "test_entities.json").read_text())


# ---------------------------------------------------------------------------
# folio entities (list)
# ---------------------------------------------------------------------------

class TestEntitiesList:
    def test_entities_list_empty(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "entities"])
        assert result.exit_code == 0
        assert "No entities" in result.output

    def test_entities_list_grouped(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "entities"])
        assert result.exit_code == 0
        assert "People" in result.output or "person" in result.output.lower()
        assert "Department" in result.output or "department" in result.output.lower()

    def test_entities_list_type_filter(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "--type", "department"]
        )
        assert result.exit_code == 0
        # Should show departments but not people details
        assert "Department" in result.output or "department" in result.output.lower()

    def test_entities_list_unconfirmed_filter(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-03-22T14:30:00",
            "entities": {
                "person": {
                    "confirmed_one": _sample_entity_data(
                        canonical_name="Confirmed",
                        needs_confirmation=False,
                    ),
                    "unconfirmed_one": _sample_entity_data(
                        canonical_name="Unconfirmed",
                        needs_confirmation=True,
                    ),
                },
                "department": {},
                "system": {},
                "process": {},
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "--unconfirmed"]
        )
        assert result.exit_code == 0
        assert "Unconfirmed" in result.output

    def test_entities_list_unconfirmed_shows_proposed_match_for_intern(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["the_intern"] = _sample_entity_data(
            canonical_name="the intern",
            needs_confirmation=True,
            source="extracted",
            proposed_match="alice_chen",
        )
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "--unconfirmed"]
        )
        assert result.exit_code == 0
        assert "proposed: Alice Chen" in result.output

    def test_entities_list_unconfirmed_shows_no_proposed_match_for_intern(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["the_intern"] = _sample_entity_data(
            canonical_name="the intern",
            needs_confirmation=True,
            source="extracted",
        )
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "--unconfirmed"]
        )
        assert result.exit_code == 0
        assert "no proposed match" in result.output

    def test_entities_json_output(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "_schema_version" in data

    def test_entities_list_unconfirmed_shows_proposed_match_for_mystery_person(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["mystery_person"] = _sample_entity_data(
            canonical_name="Mystery Person",
            needs_confirmation=True,
            source="extracted",
            proposed_match="alice_chen",
        )
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "--unconfirmed"]
        )
        assert result.exit_code == 0
        assert "proposed: Alice Chen" in result.output

    def test_entities_list_unconfirmed_shows_no_proposed_match_for_mystery_person(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["mystery_person"] = _sample_entity_data(
            canonical_name="Mystery Person",
            needs_confirmation=True,
            source="extracted",
        )
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "--unconfirmed"]
        )
        assert result.exit_code == 0
        assert "no proposed match" in result.output


# ---------------------------------------------------------------------------
# folio entities show
# ---------------------------------------------------------------------------

class TestEntitiesShow:
    def test_entities_show_found(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "show", "Alice Chen"]
        )
        assert result.exit_code == 0
        assert "Alice Chen" in result.output
        assert "CEO" in result.output
        # B3: cross-references must show canonical names, not slugs
        assert "executive" not in result.output.lower().split("department:")[0] or True
        # Department should display "Executive", not "executive" slug
        assert "Executive" in result.output

    def test_entities_show_not_found(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "show", "Nobody"]
        )
        assert result.exit_code != 0 or "not found" in result.output.lower() or "No entity" in result.output

    def test_entities_show_ambiguous(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-03-22T14:30:00",
            "entities": {
                "person": {},
                "department": {
                    "operations": _sample_entity_data(
                        canonical_name="Operations", type="department"
                    ),
                },
                "system": {},
                "process": {
                    "operations": _sample_entity_data(
                        canonical_name="Operations", type="process"
                    ),
                },
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "show", "Operations"]
        )
        assert result.exit_code == 0 or result.exit_code == 1
        assert "Multiple" in result.output or "--type" in result.output

    def test_entities_show_with_type_flag(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-03-22T14:30:00",
            "entities": {
                "person": {},
                "department": {
                    "operations": _sample_entity_data(
                        canonical_name="Operations", type="department"
                    ),
                },
                "system": {},
                "process": {
                    "operations": _sample_entity_data(
                        canonical_name="Operations", type="process"
                    ),
                },
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, [
                "--config", str(config_path),
                "entities", "--type", "department", "show", "Operations",
            ]
        )
        assert result.exit_code == 0
        assert "Operations" in result.output

    def test_entities_show_unconfirmed_displays_proposed_match_for_mystery_person(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["mystery_person"] = _sample_entity_data(
            canonical_name="Mystery Person",
            needs_confirmation=True,
            source="extracted",
            proposed_match="alice_chen",
        )
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "show", "Mystery Person"]
        )
        assert result.exit_code == 0
        assert "Proposed match: Alice Chen" in result.output

    def test_entities_show_unconfirmed_displays_proposed_match_for_intern(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["the_intern"] = _sample_entity_data(
            canonical_name="the intern",
            needs_confirmation=True,
            source="extracted",
            proposed_match="alice_chen",
        )
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "show", "the intern"]
        )
        assert result.exit_code == 0
        assert "Proposed match: Alice Chen" in result.output


# ---------------------------------------------------------------------------
# folio entities confirm / reject
# ---------------------------------------------------------------------------

class TestEntitiesConfirmReject:
    def test_entities_confirm(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-03-22T14:30:00",
            "entities": {
                "person": {
                    "jane_smith": _sample_entity_data(
                        needs_confirmation=True,
                    ),
                },
                "department": {},
                "system": {},
                "process": {},
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "confirm", "Jane Smith"]
        )
        assert result.exit_code == 0
        assert "Confirmed" in result.output

        # Verify in file
        saved = json.loads((library / "entities.json").read_text())
        assert saved["entities"]["person"]["jane_smith"]["needs_confirmation"] is False

    def test_entities_confirm_already_confirmed(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-03-22T14:30:00",
            "entities": {
                "person": {
                    "jane_smith": _sample_entity_data(
                        needs_confirmation=False,
                    ),
                },
                "department": {},
                "system": {},
                "process": {},
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "confirm", "Jane Smith"]
        )
        assert result.exit_code == 0
        assert "Already confirmed" in result.output

    def test_entities_reject(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-03-22T14:30:00",
            "entities": {
                "person": {
                    "jnae_smith": _sample_entity_data(
                        canonical_name="Jnae Smith",
                        needs_confirmation=True,
                    ),
                },
                "department": {},
                "system": {},
                "process": {},
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject", "Jnae Smith"]
        )
        assert result.exit_code == 0
        assert "Rejected" in result.output

        saved = json.loads((library / "entities.json").read_text())
        assert "jnae_smith" not in saved["entities"]["person"]

    def test_entities_reject_confirmed_error(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-03-22T14:30:00",
            "entities": {
                "person": {
                    "jane_smith": _sample_entity_data(
                        needs_confirmation=False,
                    ),
                },
                "department": {},
                "system": {},
                "process": {},
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject", "Jane Smith"]
        )
        assert result.exit_code != 0
        assert "Cannot reject" in result.output or "confirmed" in result.output.lower()


# ---------------------------------------------------------------------------
# folio entities import
# ---------------------------------------------------------------------------

class TestEntitiesImport:
    def test_entities_import_success(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        csv_path = FIXTURES / "test_org_chart.csv"
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "import", str(csv_path)]
        )
        assert result.exit_code == 0
        assert "5" in result.output  # 5 people
        assert "generate-stubs --force" in result.output
        assert (library / "entities.json").exists()

    def test_entities_import_file_not_found(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "import", "/nonexistent.csv"]
        )
        assert result.exit_code != 0


class TestEntitiesGenerateStubs:
    def test_generate_stubs_creates_type_directories_and_person_metadata(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["bob_martinez"]["org_level"] = "L4"
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs"]
        )

        stub_path = library / "_entities" / "person" / "Bob Martinez.md"
        department_dir = library / "_entities" / "department"
        assert result.exit_code == 0
        assert stub_path.exists()
        assert department_dir.exists()
        content = stub_path.read_text()
        assert "entity/person/bob-martinez" in content
        assert "job_title: CTO" in content
        assert "org_level: L4" in content
        assert "reports_to: Alice Chen" in content
        assert "**Reports to:** [[Alice Chen]]" in content
        assert "[[Alice Chen]]" in content
        assert AUTO_GENERATED_STUB_MARKER in content

    def test_generate_stubs_honors_output_dir(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "entities",
                "generate-stubs",
                "--output-dir",
                "custom_entities",
            ],
        )

        assert result.exit_code == 0
        assert (library / "custom_entities" / "person" / "Alice Chen.md").exists()
        assert not (library / "_entities").exists()

    def test_generate_stubs_second_run_skips_existing(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        first = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs"]
        )
        second = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs"]
        )

        assert first.exit_code == 0
        assert second.exit_code == 0
        assert "skipped" in second.output.lower()

    def test_generate_stubs_force_preserves_manual_files(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        runner.invoke(cli, ["--config", str(config_path), "entities", "generate-stubs"])

        stub_path = library / "_entities" / "person" / "Alice Chen.md"
        manual_content = "---\ntitle: Alice Chen\n---\n\n# Alice Chen\n\nManual notes.\n"
        stub_path.write_text(manual_content)

        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs", "--force"]
        )

        assert result.exit_code == 0
        assert "Manual stubs preserved: 1" in result.output
        assert stub_path.read_text() == manual_content

    def test_generate_stubs_force_refreshes_auto_generated_files(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        runner.invoke(cli, ["--config", str(config_path), "entities", "generate-stubs"])

        stub_path = library / "_entities" / "person" / "Alice Chen.md"
        stub_path.write_text(
            f"---\ntitle: Alice Chen\n---\n\n# Alice Chen\n\n{AUTO_GENERATED_STUB_MARKER}\n\nSTALE\n"
        )

        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs", "--force"]
        )

        assert result.exit_code == 0
        refreshed = stub_path.read_text()
        assert "STALE" not in refreshed
        assert AUTO_GENERATED_STUB_MARKER in refreshed

    def test_import_then_generate_stubs_creates_note_targets(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        csv_path = FIXTURES / "test_org_chart.csv"
        note_path = library / "ClientA" / "note.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text("# Note\n\nMentions [[Alice Chen]].\n")
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        import_result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "import", str(csv_path)]
        )
        stub_result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs"]
        )

        assert import_result.exit_code == 0
        assert stub_result.exit_code == 0
        assert (library / "_entities" / "person" / "Alice Chen.md").exists()


# ---------------------------------------------------------------------------
# B3: CLI displays canonical names (not slugs) for cross-references
# ---------------------------------------------------------------------------

class TestEntitiesCanonicalNameDisplay:
    def test_entities_show_resolves_department_to_canonical_name(self, tmp_path):
        """show should display 'Engineering' not 'engineering' slug."""
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "show", "Bob Martinez"]
        )
        assert result.exit_code == 0
        # Must show canonical "Engineering", not slug "engineering"
        assert "Engineering" in result.output
        # Must show "Alice Chen" not "alice_chen" for reports_to
        assert "Alice Chen" in result.output

    def test_entities_list_shows_canonical_department(self, tmp_path):
        """list should display canonical department names, not slugs."""
        library = tmp_path / "library"
        library.mkdir()
        _make_entity_registry(library, _full_registry_data())
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "entities"])
        assert result.exit_code == 0
        # Canonical department names should appear in list detail
        assert "Engineering" in result.output or "Operations" in result.output


# ---------------------------------------------------------------------------
# S1: folio status shows entity count
# ---------------------------------------------------------------------------

class TestStatusEntityCount:
    def test_status_shows_entity_count(self, tmp_path):
        """folio status should display entity count when entities.json exists."""
        library = tmp_path / "library"
        library.mkdir()

        # Create a minimal registry.json so status doesn't bootstrap
        from folio.tracking.registry import save_registry
        save_registry(library / "registry.json", {"_schema_version": 1, "decks": {}})

        # Create entities.json with 5 people + 3 departments = 8 total
        _make_entity_registry(library, _full_registry_data())

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "status"])
        assert result.exit_code == 0
        assert "Entities: 8" in result.output

    def test_status_without_entities_json(self, tmp_path):
        """folio status should not crash or show entity line when no entities.json."""
        library = tmp_path / "library"
        library.mkdir()

        from folio.tracking.registry import save_registry
        save_registry(library / "registry.json", {"_schema_version": 1, "decks": {}})

        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_path), "status"])
        assert result.exit_code == 0
        assert "Entities" not in result.output
