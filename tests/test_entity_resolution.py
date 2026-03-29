"""Tests for ingest-time entity resolution."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

from folio.pipeline.entity_resolution import (
    _PendingCreation,
    _persist_pending_creations,
    _source_context,
    resolve_interaction_entities,
)
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

    def test_resolve_transposed_person_name(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Rachel Link", type="person", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Link, Rachel"]),
            source_text="Link, Rachel joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Rachel Link"]
        assert result.registry_changed is False

    def test_resolve_transposed_unicode_person_name(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="José Díaz", type="person", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Díaz, José"]),
            source_text="Díaz, José joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["José Díaz"]
        assert result.registry_changed is False

    def test_non_person_comma_phrase_does_not_resolve_to_existing_person(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Architecture Review", type="person", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Review, Architecture"]),
            source_text="Review, Architecture joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Review, Architecture"]
        assert result.registry_changed is True
        assert result.created_entities[0].canonical_name == "Review, Architecture"
        assert all(person != "Architecture Review" for person in result.entities["people"])

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
    def test_resolve_id_suffix_name_stays_unresolved_without_full_name_match(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Rachel Link", type="person", source="import")],
        )
        mock_run.return_value = '{"match": null}'

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Rachelrjlink"]),
            source_text="Rachelrjlink joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Rachelrjlink"]
        assert result.registry_changed is True
        assert result.created_entities[0].canonical_name == "Rachelrjlink"
        assert result.created_entities[0].proposed_match is None

    def test_resolve_transposed_name_with_id_suffix(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Rachel Link", type="person", source="import")],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Link, Rachelrjlink"]),
            source_text="Link, Rachelrjlink joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Rachel Link"]
        assert result.registry_changed is False

    def test_resolve_transposed_suffix_name_does_not_pick_wrong_person(self, tmp_path):
        path = _make_registry(
            tmp_path,
            [
                EntityEntry(canonical_name="Christophe Smith", type="person", source="import"),
                EntityEntry(canonical_name="Christopher Smith", type="person", source="import"),
            ],
        )

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Smith, Christopherjsmith"]),
            source_text="Smith, Christopherjsmith joined the meeting.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert result.entities["people"] == ["Smith, Christopherjsmith"]
        assert any('⚠ Ambiguous entity: "Smith, Christopherjsmith" matches' in warning for warning in result.warnings)
        assert all(person != "Christophe Smith" for person in result.entities["people"])
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
        assert any('⚠ Ambiguous entity: "Jane" matches' in warning for warning in result.warnings)
        assert any("→ Keeping unresolved wikilink: [[Jane]]" in warning for warning in result.warnings)
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

    def test_source_context_returns_sentence_containing_mention(self):
        source_text = (
            "Alice introduced the topic. Bob mentioned ServiceNow during the update. "
            "Carol closed the meeting."
        )

        assert _source_context(source_text, "ServiceNow") == "Bob mentioned ServiceNow during the update."

    def test_source_context_keeps_common_abbreviations_in_sentence(self):
        source_text = (
            "Dr. Smith mentioned ServiceNow during the update. "
            "Carol closed the meeting."
        )

        assert (
            _source_context(source_text, "ServiceNow")
            == "Dr. Smith mentioned ServiceNow during the update."
        )

    def test_source_context_keeps_company_and_place_abbreviations_in_sentence(self):
        source_text = (
            "St. Mary's Inc. mentioned ServiceNow during the update. "
            "Carol closed the meeting."
        )

        assert (
            _source_context(source_text, "ServiceNow")
            == "St. Mary's Inc. mentioned ServiceNow during the update."
        )

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
    def test_soft_match_proposed(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = '{"match":"Alice Chen"}'

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

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
    def test_soft_match_proposed_accepts_case_insensitive_canonical_name(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = '{"match":"alice chen"}'

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

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
    def test_soft_match_no_match(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = '{"match": null}'

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

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
    def test_soft_match_malformed_json_returns_none(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Bob Martinez", type="person", source="import")],
        )
        mock_run.return_value = "I think it's Bob"

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

    def test_soft_match_provider_failure_returns_none(self, tmp_path, caplog):
        class _DummyProvider:
            def create_client(self, *, api_key_env: str, base_url_env: str):
                return object()

        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )

        with (
            patch("folio.pipeline.entity_resolution.get_provider", return_value=_DummyProvider()),
            patch("folio.pipeline.entity_resolution.execute_with_retry", side_effect=RuntimeError("boom")),
            caplog.at_level(logging.WARNING, logger="folio.pipeline.entity_resolution"),
        ):
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
        assert "Entity soft-match provider 'openai/gpt-5.4' failed: boom" in caplog.text

    def test_persist_pending_creations_merges_stale_snapshots(self, tmp_path):
        path = _make_registry(tmp_path, [])

        first_pending = _PendingCreation(
            entry=EntityEntry(
                canonical_name="ServiceNow",
                type="system",
                aliases=[],
                needs_confirmation=True,
                source="extracted",
            )
        )
        second_pending = _PendingCreation(
            entry=EntityEntry(
                canonical_name="Workday",
                type="system",
                aliases=[],
                needs_confirmation=True,
                source="extracted",
            )
        )

        committed_one, warnings_one = _persist_pending_creations(
            entities_path=path,
            pending_creations=[first_pending],
        )
        committed_two, warnings_two = _persist_pending_creations(
            entities_path=path,
            pending_creations=[second_pending],
        )

        saved = json.loads(path.read_text())
        assert warnings_one == []
        assert warnings_two == []
        assert [key for key, _entry in committed_one] == ["servicenow"]
        assert [key for key, _entry in committed_two] == ["workday"]
        assert "servicenow" in saved["entities"]["system"]
        assert "workday" in saved["entities"]["system"]

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
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

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
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

        def _fake_execute_with_fallback(**kwargs):
            captured_prompt["prompt"] = kwargs["prompt"]
            return '{"match": null}'

        mock_run.side_effect = _fake_execute_with_fallback

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

    @patch("folio.pipeline.entity_resolution._execute_with_fallback")
    def test_soft_match_one_call_per_name(self, mock_run, tmp_path):
        path = _make_registry(
            tmp_path,
            [EntityEntry(canonical_name="Alice Chen", type="person", source="import")],
        )
        mock_run.return_value = '{"match": null}'

        result = resolve_interaction_entities(
            entities_path=path,
            extracted_entities=_entities(people=["Mystery Person", "Mystery Person"]),
            source_text="Mystery Person asked for the numbers.",
            provider_name="openai",
            model="gpt-5.4",
        )

        assert mock_run.call_count == 1
        assert result.entities["people"] == ["Mystery Person"]
