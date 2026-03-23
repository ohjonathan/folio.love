"""Tests for ingest-time entity resolution."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from folio.pipeline.entity_resolution import resolve_interaction_entities
from folio.tracking.entities import EntityEntry, EntityRegistry


def _entities(**overrides) -> dict[str, list[str]]:
    base = {
        "people": [],
        "departments": [],
        "systems": [],
        "processes": [],
    }
    base.update(overrides)
    return base


def _registry_path(tmp_path: Path) -> Path:
    library = tmp_path / "library"
    library.mkdir(parents=True, exist_ok=True)
    return library / "entities.json"


def _make_registry(tmp_path: Path, entries: list[EntityEntry]) -> Path:
    path = _registry_path(tmp_path)
    reg = EntityRegistry(path)
    reg.load()
    for entry in entries:
        reg.add_entity(entry)
    reg.save()
    return path


def _write_registry_data(tmp_path: Path, data: dict) -> Path:
    path = _registry_path(tmp_path)
    path.write_text(json.dumps(data, indent=2))
    return path


class TestEntityResolution:
    def test_resolve_exact_match(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Jane Smith", type="person", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Jane Smith"]),
            source_text="Jane Smith joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Jane Smith"]
        assert result.registry_changed is False
        assert result.created_entities == []

    def test_resolve_alias_match(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [
                EntityEntry(
                    canonical_name="Alice Chen",
                    type="person",
                    aliases=["the CEO"],
                    source="import",
                )
            ],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["the CEO"]),
            source_text="The CEO asked for a weekly update.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Alice Chen"]
        assert result.registry_changed is False

    def test_resolve_case_insensitive(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Jane Smith", type="person", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["jane smith"]),
            source_text="jane smith joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Jane Smith"]
        assert result.registry_changed is False

    def test_resolve_ambiguous_keeps_original(self, tmp_path):
        path = _write_registry_data(
            tmp_path,
            {
                "_schema_version": 1,
                "updated_at": "2026-03-22T14:30:00+00:00",
                "entities": {
                    "person": {
                        "jane_smith": {
                            "canonical_name": "Jane Smith",
                            "type": "person",
                            "aliases": ["Jane"],
                            "needs_confirmation": False,
                            "source": "import",
                            "first_seen": "2026-03-22T14:30:00+00:00",
                            "created_at": "2026-03-22T14:30:00+00:00",
                            "updated_at": "2026-03-22T14:30:00+00:00",
                        },
                        "jane_doe": {
                            "canonical_name": "Jane Doe",
                            "type": "person",
                            "aliases": ["Jane"],
                            "needs_confirmation": False,
                            "source": "manual",
                            "first_seen": "2026-03-22T14:30:00+00:00",
                            "created_at": "2026-03-22T14:30:00+00:00",
                            "updated_at": "2026-03-22T14:30:00+00:00",
                        },
                    },
                    "department": {},
                    "system": {},
                    "process": {},
                },
            },
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Jane"]),
            source_text="Jane joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Jane"]
        assert any("Ambiguous entity 'Jane'" in warning for warning in result.warnings)
        assert result.registry_changed is False

    def test_resolve_type_strict_miss(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Operations", type="department", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(systems=["Operations"]),
            source_text="Operations is the main platform.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["systems"] == ["Operations"]
        assert result.created_entities[0].entity_type == "system"
        assert result.created_entities[0].key == "operations"

    def test_resolve_confirmed_only_skips_unconfirmed_entities(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [
                EntityEntry(
                    canonical_name="Jane Smith",
                    type="person",
                    needs_confirmation=True,
                    source="extracted",
                )
            ],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Jane Smith"]),
            source_text="Jane Smith joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Jane Smith"]
        assert result.registry_changed is False
        assert any("Could not auto-create person 'Jane Smith'" in warning for warning in result.warnings)

    def test_resolve_no_registry_is_noop(self, tmp_path):
        path = _registry_path(tmp_path)

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Bob"]),
            source_text="Bob joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Bob"]
        assert result.registry_changed is False
        assert path.exists() is False

    def test_resolve_empty_registry_auto_creates(self, tmp_path):
        path = _make_registry(tmp_path, [])

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(systems=["ServiceNow"]),
            source_text="ServiceNow is the target platform.",
            provider_name="openai",
            model="gpt-5.4",
        )

        saved = json.loads(path.read_text())
        entry = saved["entities"]["system"]["servicenow"]
        assert result.entities["systems"] == ["ServiceNow"]
        assert result.registry_changed is True
        assert entry["needs_confirmation"] is True
        assert entry["source"] == "extracted"

    def test_resolve_post_canonicalization_dedupe(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [
                EntityEntry(
                    canonical_name="Jane Smith",
                    type="person",
                    aliases=["Jane"],
                    source="import",
                )
            ],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Jane", "Jane Smith"]),
            source_text="Jane Smith ran the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Jane Smith"]

    def test_resolve_slug_collision_keeps_original(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Jane Smith", type="person", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Jane  Smith"]),
            source_text="Jane  Smith ran the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Jane Smith"]
        assert result.registry_changed is False

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    def test_soft_match_proposed(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = SimpleNamespace(raw_text='{"match":"Alice Chen"}')

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Alyce Chen"]),
            source_text="Alyce Chen asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        saved = json.loads(path.read_text())
        entry = saved["entities"]["person"]["alyce_chen"]
        assert result.registry_changed is True
        assert result.created_entities[0].proposed_match == "alice_chen"
        assert entry["proposed_match"] == "alice_chen"
        assert mock_run.call_count == 1

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    def test_soft_match_proposed_accepts_case_insensitive_canonical_name(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = SimpleNamespace(raw_text='{"match":"alice chen"}')

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Alyce Chen"]),
            source_text="Alyce Chen asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        saved = json.loads(path.read_text())
        entry = saved["entities"]["person"]["alyce_chen"]
        assert result.registry_changed is True
        assert result.created_entities[0].proposed_match == "alice_chen"
        assert entry["proposed_match"] == "alice_chen"

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    def test_soft_match_no_match(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = SimpleNamespace(raw_text='{"match": null}')

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Mystery Person"]),
            source_text="Mystery Person asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        saved = json.loads(path.read_text())
        entry = saved["entities"]["person"]["mystery_person"]
        assert result.created_entities[0].proposed_match is None
        assert "proposed_match" not in entry

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    def test_soft_match_malformed_json_returns_none(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Bob Martinez", type="person", source="import")],
        )
        mock_run.return_value = SimpleNamespace(raw_text="I think it's Bob")

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Mystery Person"]),
            source_text="Mystery Person asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        saved = json.loads(path.read_text())
        entry = saved["entities"]["person"]["mystery_person"]
        assert result.created_entities[0].proposed_match is None
        assert "proposed_match" not in entry

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    def test_soft_match_skipped_when_no_candidates(self, mock_run, tmp_path):
        path = _make_registry(tmp_path, [])

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Mystery Person"]),
            source_text="Mystery Person asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.registry_changed is True
        assert mock_run.call_count == 0

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    def test_soft_match_capped_at_50(self, mock_run, tmp_path):
        people = {}
        for idx in range(60):
            people[f"candidate_{idx:02d}"] = {
                "canonical_name": f"Candidate {idx:02d}",
                "type": "person",
                "aliases": [],
                "needs_confirmation": False,
                "source": "import",
                "first_seen": f"2026-03-22T14:{idx:02d}:00+00:00",
                "created_at": f"2026-03-22T14:{idx:02d}:00+00:00",
                "updated_at": f"2026-03-22T14:{idx:02d}:00+00:00",
            }
        path = _write_registry_data(
            tmp_path,
            {
                "_schema_version": 1,
                "updated_at": "2026-03-22T14:59:00+00:00",
                "entities": {
                    "person": people,
                    "department": {},
                    "system": {},
                    "process": {},
                },
            },
        )
        captured_prompt: dict[str, str] = {}

        def _fake_run_with_fallback(**kwargs):
            captured_prompt["prompt"] = kwargs["prompt"]
            return SimpleNamespace(raw_text='{"match": null}')

        mock_run.side_effect = _fake_run_with_fallback

        resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Mystery Person"]),
            source_text="Mystery Person asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        candidate_lines = [
            line for line in captured_prompt["prompt"].splitlines()
            if line.startswith("- Candidate ")
        ]
        assert len(candidate_lines) == 50
        assert any("Candidate 59" in line for line in candidate_lines)
        assert all("Candidate 00" not in line for line in candidate_lines)

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    def test_soft_match_one_call_per_name(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = SimpleNamespace(raw_text='{"match": null}')

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Mystery Person", "Mystery Person"]),
            source_text="Mystery Person asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert mock_run.call_count == 1
        assert result.entities["people"] == ["Mystery Person"]
