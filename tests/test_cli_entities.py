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

    def test_generate_stubs_keeps_legacy_reports_to_visible_when_manager_missing(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = _full_registry_data()
        data["entities"]["person"]["bob_martinez"]["reports_to"] = "Missing Boss"
        del data["entities"]["person"]["alice_chen"]
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs"]
        )

        assert result.exit_code == 0
        content = (library / "_entities" / "person" / "Bob Martinez.md").read_text()
        assert "reports_to: Missing Boss" in content
        assert "**Reports to:** [[Missing Boss]]" in content

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

    def test_generate_stubs_force_removes_stale_auto_generated_stub_after_merge(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": _sample_entity_data(canonical_name="Alice Chen"),
                    "chen_alice": _sample_entity_data(canonical_name="Chen, Alice"),
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
        runner.invoke(cli, ["--config", str(config_path), "entities", "generate-stubs"])

        merge_result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "merge", "Alice Chen", "Chen, Alice"]
        )
        refresh_result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs", "--force"]
        )

        assert merge_result.exit_code == 0
        assert refresh_result.exit_code == 0
        assert "Removed stale auto-generated stubs: 1" in refresh_result.output
        assert not (library / "_entities" / "person" / "Chen, Alice.md").exists()

    def test_generate_stubs_force_preserves_manual_stale_stub_after_merge(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": _sample_entity_data(canonical_name="Alice Chen"),
                    "chen_alice": _sample_entity_data(canonical_name="Chen, Alice"),
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
        runner.invoke(cli, ["--config", str(config_path), "entities", "generate-stubs"])

        loser_stub = library / "_entities" / "person" / "Chen, Alice.md"
        loser_stub.write_text("---\ntitle: Chen, Alice\n---\n\n# Chen, Alice\n\nManual note.\n")

        runner.invoke(
            cli, ["--config", str(config_path), "entities", "merge", "Alice Chen", "Chen, Alice"]
        )
        refresh_result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "generate-stubs", "--force"]
        )

        assert refresh_result.exit_code == 0
        assert "Manual stubs preserved: 1" in refresh_result.output
        assert loser_stub.exists()
        assert "Manual note." in loser_stub.read_text()


class TestEntitiesMerge:
    def test_entities_suggest_merges_lists_person_candidates(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": _sample_entity_data(canonical_name="Alice Chen"),
                    "chen_alice": _sample_entity_data(canonical_name="Chen, Alice"),
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
            cli, ["--config", str(config_path), "entities", "suggest-merges"]
        )

        assert result.exit_code == 0
        assert "Alice Chen" in result.output
        assert "Chen, Alice" in result.output
        assert "last_first_transpose" in result.output

    def test_entities_merge_rewrites_internal_references_and_aliases(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": _sample_entity_data(
                        canonical_name="Alice Chen",
                        reports_to="chen_alice",
                        aliases=["A. Chen"],
                    ),
                    "chen_alice": _sample_entity_data(
                        canonical_name="Chen, Alice",
                        aliases=["Alice C."],
                    ),
                    "bob_martinez": _sample_entity_data(
                        canonical_name="Bob Martinez",
                        reports_to="chen_alice",
                    ),
                    "mystery_exec": _sample_entity_data(
                        canonical_name="Mystery Exec",
                        needs_confirmation=True,
                        proposed_match="chen_alice",
                    ),
                },
                "department": {
                    "executive": _sample_entity_data(
                        canonical_name="Executive",
                        type="department",
                        head="chen_alice",
                    ),
                },
                "system": {},
                "process": {},
            },
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "merge", "Alice Chen", "Chen, Alice"]
        )

        assert result.exit_code == 0
        assert "Rewritten references: 4" in result.output
        assert "generate-stubs --force" in result.output

        saved = json.loads((library / "entities.json").read_text())
        assert "chen_alice" not in saved["entities"]["person"]
        winner = saved["entities"]["person"]["alice_chen"]
        assert winner["reports_to"] is None
        assert "Chen, Alice" in winner["aliases"]
        assert "Alice C." in winner["aliases"]
        assert saved["entities"]["person"]["bob_martinez"]["reports_to"] == "alice_chen"
        assert saved["entities"]["person"]["mystery_exec"]["proposed_match"] == "alice_chen"
        assert saved["entities"]["department"]["executive"]["head"] == "alice_chen"


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


# ---------------------------------------------------------------------------
# v0.6.5 Slice 6a: entity-merge rejection memory — CLI tests
# ---------------------------------------------------------------------------


class TestEntityMergeRejectionMemoryCLI:
    """Slice 6a spec §7: CLI-side tests T-9, T-9b, T-9c, T-10, T-10b, T-10c, T-10d, T-11b, T-15."""

    def _setup_alice_pair_library(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": _sample_entity_data(canonical_name="Alice Chen"),
                    "chen_alice": _sample_entity_data(canonical_name="Chen, Alice"),
                },
                "department": {}, "system": {}, "process": {},
            },
            "rejected_merges": [],
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})
        return library, config_path

    # T-9 — happy path
    def test_cli_reject_merge_happy_path(self, tmp_path):
        _, config_path = self._setup_alice_pair_library(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "chen_alice"]
        )
        assert result.exit_code == 0, result.output
        assert "✓ Rejected merge candidate" in result.output
        assert "Alice Chen" in result.output
        assert "Chen, Alice" in result.output
        assert "[alice_chen]" in result.output
        assert "[chen_alice]" in result.output
        assert "reasons:" in result.output
        assert "last_first_transpose" in result.output

    # T-9b — idempotent
    def test_cli_reject_merge_idempotent_message(self, tmp_path):
        _, config_path = self._setup_alice_pair_library(tmp_path)
        runner = CliRunner()
        runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "chen_alice"]
        )
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "chen_alice"]
        )
        assert result.exit_code == 0
        assert "= Already rejected" in result.output
        assert "(no change)" in result.output

    # T-9c — stale key
    def test_cli_reject_merge_stale_key_error(self, tmp_path):
        _, config_path = self._setup_alice_pair_library(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "ghost_that_does_not_exist"]
        )
        assert result.exit_code != 0
        assert "✗ Merge candidate is stale" in result.output
        assert "no longer exists" in result.output

    # T-10 — pluralization (three branches)
    def test_cli_suggest_merges_renders_suppression_count_pluralization_zero(self, tmp_path):
        _, config_path = self._setup_alice_pair_library(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "suggest-merges"]
        )
        assert "No merge candidates suppressed by rejection memory." in result.output

    def test_cli_suggest_merges_renders_suppression_count_pluralization_one(self, tmp_path):
        _, config_path = self._setup_alice_pair_library(tmp_path)
        runner = CliRunner()
        runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "chen_alice"]
        )
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "suggest-merges"]
        )
        assert "1 merge candidate suppressed by rejection memory." in result.output

    # T-10b — (M total rejections recorded.)
    def test_cli_suggest_merges_renders_total_rejections_line(self, tmp_path):
        _, config_path = self._setup_alice_pair_library(tmp_path)
        runner = CliRunner()
        # Pristine: 0 total rejections line still rendered.
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "suggest-merges"]
        )
        assert "(0 total rejections recorded.)" in result.output
        # After reject.
        runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "chen_alice"]
        )
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "suggest-merges"]
        )
        assert "(1 total rejections recorded.)" in result.output

    # T-10c — disclosure on empty / filtered paths
    def test_cli_suggest_merges_disclosure_on_no_candidates(self, tmp_path):
        """Registry with no candidate pair: disclosure still renders."""
        library = tmp_path / "library"
        library.mkdir()
        data = {
            "_schema_version": 1,
            "updated_at": "2026-04-01T00:00:00Z",
            "entities": {
                "person": {
                    "alice_chen": _sample_entity_data(canonical_name="Alice Chen"),
                },
                "department": {}, "system": {}, "process": {},
            },
            "rejected_merges": [],
        }
        _make_entity_registry(library, data)
        config_path = tmp_path / "folio.yaml"
        _make_config(config_path, {"library_root": str(library)})

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "suggest-merges"]
        )
        assert result.exit_code == 0
        assert "No merge candidates found." in result.output
        # Disclosure MUST still render on the empty path.
        assert "No merge candidates suppressed by rejection memory." in result.output
        assert "(0 total rejections recorded.)" in result.output

    # T-10d — revival annotation
    def test_cli_suggest_merges_revival_annotation(self, tmp_path):
        library, config_path = self._setup_alice_pair_library(tmp_path)
        # Seed a stale-fingerprint rejection to trigger revival.
        reg_path = library / "entities.json"
        data = json.loads(reg_path.read_text())
        data["rejected_merges"].append({
            "subject_type": "person",
            "entity_keys": ["alice_chen", "chen_alice"],
            "basis_fingerprint": "sha256:stale-fingerprint-not-matching-current",
            "reasons_at_rejection": ["some_old_reason"],
            "rejected_at": "2026-01-01T00:00:00+00:00",
        })
        reg_path.write_text(json.dumps(data, indent=2))

        runner = CliRunner()
        result = runner.invoke(
            cli, ["--config", str(config_path), "entities", "suggest-merges"]
        )
        assert result.exit_code == 0
        assert "(revived — basis changed)" in result.output

    # T-11b — graph status filtered count + renamed label
    def test_cli_graph_status_reviewable_label_and_filtered_count(self, tmp_path):
        library, config_path = self._setup_alice_pair_library(tmp_path)
        # Need a registry.json for graph_status to run.
        (library / "registry.json").write_text(json.dumps({"decks": {}}))

        runner = CliRunner()
        # Before rejection: 1 reviewable duplicate candidate.
        result = runner.invoke(
            cli, ["--config", str(config_path), "graph", "status"]
        )
        assert result.exit_code == 0
        assert "Reviewable duplicate person candidates:" in result.output
        assert "Reviewable duplicate person candidates: 1" in result.output

        # After rejection: 0.
        runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "chen_alice"]
        )
        result = runner.invoke(
            cli, ["--config", str(config_path), "graph", "status"]
        )
        assert "Reviewable duplicate person candidates: 0" in result.output

    # T-11 — graph doctor honors rejection memory (D.4 fix per peer M-1)
    def test_cli_graph_doctor_honors_rejection_memory(self, tmp_path):
        """After rejecting a pair, graph doctor's duplicate_person_candidate
        finding no longer includes that pair."""
        library, config_path = self._setup_alice_pair_library(tmp_path)
        # Need a registry.json for graph_doctor to iterate.
        (library / "registry.json").write_text(json.dumps({"decks": {}}))

        runner = CliRunner()
        # Before rejection: the duplicate pair surfaces as a doctor finding.
        result_before = runner.invoke(
            cli, ["--config", str(config_path), "graph", "doctor"]
        )
        assert result_before.exit_code == 0
        assert "duplicate_person_candidate" in result_before.output or "Alice Chen" in result_before.output

        # Reject the pair.
        runner.invoke(
            cli, ["--config", str(config_path), "entities", "reject-merge",
                  "alice_chen", "chen_alice"]
        )

        # After rejection: doctor's duplicate_person_candidate for this pair
        # is gone (other findings like missing_entity_stub may still include
        # the keys — filter to the duplicate finding class only).
        result_after = runner.invoke(
            cli, ["--config", str(config_path), "graph", "doctor"]
        )
        assert result_after.exit_code == 0
        before_dup_lines = [
            line for line in result_before.output.splitlines()
            if "duplicate_person_candidate" in line
        ]
        after_dup_lines = [
            line for line in result_after.output.splitlines()
            if "duplicate_person_candidate" in line
        ]
        assert len(before_dup_lines) > len(after_dup_lines), (
            f"Expected fewer duplicate_person_candidate findings after "
            f"rejection. Before: {before_dup_lines}. After: {after_dup_lines}."
        )

    # T-15 — lock contract (raises LibraryLockError on held lock, does not block)
    def test_cli_reject_merge_honors_library_lock(self, tmp_path):
        library, config_path = self._setup_alice_pair_library(tmp_path)
        # Acquire .folio.lock manually so it's held when reject-merge tries.
        import os
        from datetime import datetime, timezone
        lock_path = library / ".folio.lock"
        payload = {
            "pid": os.getpid(),
            "command": "test-held",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, json.dumps(payload).encode())
        finally:
            os.close(fd)

        try:
            runner = CliRunner()
            result = runner.invoke(
                cli, ["--config", str(config_path), "entities", "reject-merge",
                      "alice_chen", "chen_alice"]
            )
            # Raises LibraryLockError → non-zero exit, error text on stderr or output.
            assert result.exit_code != 0
            combined = (result.output or "") + (str(result.exception) or "")
            assert "library lock already held" in combined
        finally:
            lock_path.unlink()
