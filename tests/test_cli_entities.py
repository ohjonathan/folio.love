"""Tests for entity CLI commands."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner
from folio.cli import cli
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
