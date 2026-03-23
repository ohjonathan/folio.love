"""Integration tests for `folio ingest` orchestration."""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from folio.config import FolioConfig
from folio.entity_import import import_csv
from folio.ingest import IngestAmbiguityError, IngestError, IngestSubtypeMismatchError, ingest_source
from folio.llm.runtime import EndpointNotAllowedError
from folio.pipeline.interaction_analysis import InteractionAnalysisResult, InteractionFinding, InteractionQuote
from folio.tracking.entities import EntityRegistry
from folio.tracking.registry import save_registry


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ingest"
ROOT_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
ROOT_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _fixture(name: str) -> Path:
    return FIXTURE_DIR / name


def _root_fixture(name: str) -> Path:
    return ROOT_FIXTURE_DIR / name


def _make_library(tmp_path: Path) -> Path:
    library = tmp_path / "library"
    library.mkdir(parents=True, exist_ok=True)
    return library


def _sample_interaction_registry_entry(**overrides) -> dict:
    defaults = {
        "id": "test_interaction_20260310_call",
        "title": "Test Call",
        "markdown_path": "TestClient/interactions/call/call.md",
        "deck_dir": "TestClient/interactions/call",
        "source_relative_path": "../../../sources/call.txt",
        "source_hash": "abc123def456",
        "source_type": None,
        "version": 1,
        "converted": "2026-03-10T02:15:00Z",
        "modified": "2026-03-10T02:15:00Z",
        "client": "TestClient",
        "authority": "captured",
        "curation_level": "L0",
        "staleness_status": "current",
        "type": "interaction",
        "subtype": "expert_interview",
    }
    defaults.update(overrides)
    return defaults


def _analysis_result(
    *,
    llm_status: str = "executed",
    review_status: str = "clean",
    tags: list[str] | None = None,
    entities: dict[str, list[str]] | None = None,
    provider_name: str | None = "anthropic",
    model_name: str | None = "claude-sonnet-4-20250514",
    fallback_used: bool = False,
) -> InteractionAnalysisResult:
    return InteractionAnalysisResult(
        summary="The team described a successful operational change and a follow-up dependency.",
        tags=tags or ["expert-interview", "operations"],
        entities=entities or {
            "people": ["Jane Smith", "Johnny Oh"],
            "departments": ["Engineering"],
            "systems": ["ServiceNow"],
            "processes": ["Incident Triage"],
        },
        claims=[
            InteractionFinding(
                statement="The team reduced downtime materially.",
                quote="We reduced downtime from 12 hours to 2 hours in one quarter.",
                element_type="data_point",
                confidence="high",
                speaker="Jane Smith",
                validated=True,
            )
        ],
        data_points=[],
        decisions=[
            InteractionFinding(
                statement="The team agreed to add a reporting checkpoint.",
                quote="Add a reporting checkpoint.",
                element_type="decision",
                confidence="medium",
                speaker="Johnny Oh",
                validated=True,
            )
        ],
        open_questions=[],
        notable_quotes=[
            InteractionQuote(
                quote="We reduced downtime from 12 hours to 2 hours in one quarter.",
                element_type="statement",
                confidence="high",
                speaker="Jane Smith",
                validated=True,
            )
        ],
        warnings=[],
        review_status=review_status,
        review_flags=[] if review_status == "clean" else ["analysis_unavailable"],
        extraction_confidence=0.87 if llm_status == "executed" else None,
        grounding_summary={
            "total_claims": 2,
            "high_confidence": 1,
            "medium_confidence": 1,
            "low_confidence": 0,
            "validated": 2,
            "unvalidated": 0,
        },
        pass_strategy="single_pass",
        llm_status=llm_status,
        provider_name=provider_name,
        model_name=model_name,
        fallback_used=fallback_used,
    )


def _parse_frontmatter(md_path: Path) -> dict:
    content = md_path.read_text()
    yaml_block = content.split("---", 2)[1].strip()
    return yaml.safe_load(yaml_block)


def _import_org_chart(library: Path) -> Path:
    entities_path = library / "entities.json"
    reg = EntityRegistry(entities_path)
    reg.load()
    import_csv(reg, ROOT_FIXTURE_DIR / "test_org_chart.csv")
    return entities_path


class TestIngestIntegration:
    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_writes_interaction_note_and_registry(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "expert_interview.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("expert_interview.md"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result(
            tags=["expert-interview", "technology"],
            provider_name="openai",
            model_name="gpt-5.4",
            fallback_used=True,
        )

        result = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
            participants=["Jane Smith", "Johnny Oh", "Jane Smith"],
            duration_minutes=45,
        )

        assert result.version == 1
        assert result.review_status == "clean"
        assert result.degraded is False
        assert result.output_path.exists()

        fm = _parse_frontmatter(result.output_path)
        assert fm["type"] == "interaction"
        assert fm["subtype"] == "expert_interview"
        assert fm["status"] == "complete"
        assert fm["date"] == "2026-03-21"
        assert fm["source_hash"]
        assert fm["source_transcript"].endswith("expert_interview.md")
        assert "source" not in fm
        assert "source_type" not in fm
        assert "slide_count" not in fm
        assert fm["participants"] == ["Jane Smith", "Johnny Oh"]
        assert fm["duration_minutes"] == 45
        assert fm["review_status"] == "clean"
        assert fm["review_flags"] == []
        assert fm["grounding_summary"] == {
            "total_claims": 2,
            "high_confidence": 1,
            "medium_confidence": 1,
            "low_confidence": 0,
            "validated": 2,
            "unvalidated": 0,
        }
        assert fm["_llm_metadata"]["ingest"]["status"] == "executed"
        assert fm["_llm_metadata"]["ingest"]["pass_strategy"] == "single_pass"
        assert fm["_llm_metadata"]["ingest"]["provider"] == "openai"
        assert fm["_llm_metadata"]["ingest"]["model"] == "gpt-5.4"
        assert fm["_llm_metadata"]["ingest"]["fallback_used"] is True
        assert "expert-interview" in fm["tags"]

        body = result.output_path.read_text()
        assert "## Summary" in body
        assert "## Entities Mentioned" in body
        assert "## Quotes / Evidence" in body
        assert "## Impact on Hypotheses" in body
        assert "> [!quote]- Raw Transcript" in body
        assert "We reduced downtime from 12 hours to 2 hours" in body

        registry_path = library / "registry.json"
        assert registry_path.exists()
        registry = json.loads(registry_path.read_text())
        entry = registry["decks"][result.interaction_id]
        assert entry["type"] == "interaction"
        assert entry["source_relative_path"].endswith("expert_interview.md")
        assert "source_type" not in entry

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_without_entity_registry_preserves_extracted_names(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "test_transcript_entities.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_root_fixture("test_transcript_entities.txt"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()
        mock_analyze.return_value.entities = {
            "people": ["Bob", "the CEO", "the intern"],
            "departments": ["Engineering"],
            "systems": ["ServiceNow"],
            "processes": [],
        }

        result = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        body = result.output_path.read_text()
        assert "- [[Bob]]" in body
        assert "- [[the CEO]]" in body
        assert "- [[the intern]]" in body
        assert "- [[ServiceNow]]" in body
        assert not (library / "entities.json").exists()

    @patch("folio.pipeline.entity_resolution._run_with_fallback", return_value='{"match": null}')
    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_with_entity_registry_resolves_and_autocreates(self, mock_analyze, _mock_soft_match, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "test_transcript_entities.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_root_fixture("test_transcript_entities.txt"), source)
        (library / "entities.json").write_text(_root_fixture("test_entities.json").read_text())

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()
        mock_analyze.return_value.entities = {
            "people": ["Bob", "the CEO", "the intern"],
            "departments": ["Engineering"],
            "systems": ["ServiceNow"],
            "processes": [],
        }

        result = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        body = result.output_path.read_text()
        assert "- [[Bob Martinez]]" in body
        assert "- [[Alice Chen]]" in body
        assert "- [[Engineering]]" in body
        assert "- [[the intern]]" in body
        assert "- [[ServiceNow]]" in body

        entities = json.loads((library / "entities.json").read_text())
        assert entities["entities"]["person"]["the_intern"]["needs_confirmation"] is True
        assert entities["entities"]["system"]["servicenow"]["needs_confirmation"] is True

    @patch("folio.ingest.analyze_interaction_text")
    def test_reingest_updates_resolution_after_entity_registry_added(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "test_transcript_entities.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_root_fixture("test_transcript_entities.txt"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()
        mock_analyze.return_value.entities = {
            "people": ["Bob"],
            "departments": [],
            "systems": [],
            "processes": [],
        }

        first = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )
        assert "- [[Bob]]" in first.output_path.read_text()

        (library / "entities.json").write_text(_root_fixture("test_entities.json").read_text())

        second = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        assert second.version == 2
        assert "- [[Bob Martinez]]" in second.output_path.read_text()

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_resolution_does_not_modify_frontmatter(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "test_transcript_entities.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_root_fixture("test_transcript_entities.txt"), source)
        (library / "entities.json").write_text(_root_fixture("test_entities.json").read_text())

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()
        mock_analyze.return_value.entities = {
            "people": ["Bob", "the CEO"],
            "departments": ["Engineering"],
            "systems": ["ServiceNow"],
            "processes": [],
        }

        result = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        fm = _parse_frontmatter(result.output_path)
        assert "participants" not in fm
        assert "source" not in fm
        assert "source_type" not in fm
        assert "slide_count" not in fm

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_reingest_same_source_path_reuses_identity(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "expert_interview.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("expert_interview.md"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        first = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )
        second = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        assert first.interaction_id == second.interaction_id
        assert first.output_path == second.output_path
        assert second.version == 2

        fm = _parse_frontmatter(second.output_path)
        assert fm["version"] == 2
        assert fm["source_transcript"].endswith("expert_interview.md")

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_reuses_hash_after_source_move(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source_a = tmp_path / "sources" / "first" / "expert_interview.md"
        source_b = tmp_path / "sources" / "second" / "expert_interview.md"
        source_a.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("expert_interview.md"), source_a)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        first = ingest_source(
            config,
            source_path=source_a,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        source_b.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source_a, source_b)

        second = ingest_source(
            config,
            source_path=source_b,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        assert second.interaction_id == first.interaction_id
        assert second.output_path == first.output_path
        assert second.version == 2
        fm = _parse_frontmatter(second.output_path)
        assert fm["source_transcript"].endswith("expert_interview.md")

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_ambiguity_requires_target(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        source_a = tmp_path / "transcripts" / "one.txt"
        source_b = tmp_path / "transcripts" / "two.txt"
        source_c = tmp_path / "transcripts" / "three.txt"
        source_a.parent.mkdir(parents=True, exist_ok=True)
        for path in (source_a, source_b, source_c):
            path.write_text("Shared transcript body.")

        from folio.tracking.sources import compute_file_hash

        shared_hash = compute_file_hash(source_a)
        note_a = library / "ClientA" / "interactions" / "one" / "one.md"
        note_b = library / "ClientA" / "interactions" / "two" / "two.md"
        for note_path, source_rel, note_id in [
            (note_a, "../../../transcripts/one.txt", "clienta_ddq126_meeting_20260321_alpha"),
            (note_b, "../../../transcripts/two.txt", "clienta_ddq126_meeting_20260321_beta"),
        ]:
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(
                "---\n"
                f"id: {note_id}\n"
                "title: Shared Meeting\n"
                "type: interaction\n"
                "subtype: client_meeting\n"
                "status: complete\n"
                "authority: captured\n"
                "curation_level: L0\n"
                "review_status: clean\n"
                "review_flags: []\n"
                "extraction_confidence: 0.87\n"
                f"source_transcript: {source_rel}\n"
                f"source_hash: {shared_hash}\n"
                "version: 1\n"
                "created: 2026-03-21T00:00:00Z\n"
                "modified: 2026-03-21T00:00:00Z\n"
                "converted: 2026-03-21T00:00:00Z\n"
                "date: 2026-03-21\n"
                "impacts: []\n"
                "---\n"
                "# Shared Meeting\n"
            )

        registry_data = {
            "_schema_version": 1,
            "decks": {
                "clienta_ddq126_meeting_20260321_alpha": {
                    **_sample_interaction_registry_entry(
                        id="clienta_ddq126_meeting_20260321_alpha",
                        title="Shared Meeting",
                        markdown_path="ClientA/interactions/one/one.md",
                        deck_dir="ClientA/interactions/one",
                        source_relative_path="../../../transcripts/one.txt",
                        source_hash=shared_hash,
                        subtype="client_meeting",
                    ),
                    "source_type": None,
                },
                "clienta_ddq126_meeting_20260321_beta": {
                    **_sample_interaction_registry_entry(
                        id="clienta_ddq126_meeting_20260321_beta",
                        title="Shared Meeting",
                        markdown_path="ClientA/interactions/two/two.md",
                        deck_dir="ClientA/interactions/two",
                        source_relative_path="../../../transcripts/two.txt",
                        source_hash=shared_hash,
                        subtype="client_meeting",
                    ),
                    "source_type": None,
                },
            },
        }
        save_registry(library / "registry.json", registry_data)

        with pytest.raises(IngestAmbiguityError):
            ingest_source(
                config,
                source_path=source_c,
                subtype="client_meeting",
                event_date=date(2026, 3, 21),
                client="ClientA",
                engagement="DD Q1 2026",
                title="Gamma",
            )

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_rejects_subtype_mismatch(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "expert_interview.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("expert_interview.md"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        with pytest.raises(IngestSubtypeMismatchError):
            ingest_source(
                config,
                source_path=source,
                subtype="client_meeting",
                event_date=date(2026, 3, 21),
                client="ClientA",
                engagement="DD Q1 2026",
            )

    @patch("folio.pipeline.entity_resolution._run_with_fallback")
    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_with_registry_resolves_and_autocreates(
        self,
        mock_analyze,
        mock_soft_match,
        tmp_path,
    ):
        library = _make_library(tmp_path)
        source = ROOT_FIXTURE_DIR / "test_transcript_entities.txt"
        config = FolioConfig(library_root=library)
        _import_org_chart(library)
        mock_analyze.return_value = _analysis_result(
            entities={
                "people": ["Bob", "the CEO", "the intern"],
                "departments": ["Engineering"],
                "systems": ["ServiceNow"],
                "processes": [],
            }
        )
        mock_soft_match.return_value = type("SoftMatchResult", (), {"raw_text": '{"match": null}'})()

        result = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
        )

        body = result.output_path.read_text()
        assert "[[Bob Martinez]]" in body
        assert "[[Alice Chen]]" in body
        assert "[[Engineering]]" in body
        assert "[[ServiceNow]]" in body
        assert "[[the intern]]" in body

        entities = json.loads((library / "entities.json").read_text())
        assert entities["entities"]["system"]["servicenow"]["needs_confirmation"] is True
        assert entities["entities"]["person"]["the_intern"]["needs_confirmation"] is True
        assert "proposed_match" not in entities["entities"]["person"]["the_intern"]

        registry = json.loads((library / "registry.json").read_text())
        entry = registry["decks"][result.interaction_id]
        assert "source_type" not in entry
        assert "entities" not in entry

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_reingest_updates_resolution_after_registry_import(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = ROOT_FIXTURE_DIR / "test_transcript_entities.txt"
        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result(
            entities={
                "people": ["Bob", "the CEO"],
                "departments": ["Engineering"],
                "systems": [],
                "processes": [],
            }
        )

        first = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
        )
        first_body = first.output_path.read_text()
        assert "[[Bob]]" in first_body
        assert "[[the CEO]]" in first_body

        _import_org_chart(library)

        second = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
        )
        second_body = second.output_path.read_text()
        assert "[[Bob Martinez]]" in second_body
        assert "[[Alice Chen]]" in second_body
        assert "[[Bob]]" not in second_body
        assert "[[the CEO]]" not in second_body

    @patch("folio.ingest.analyze_interaction_text")
    def test_resolution_does_not_modify_frontmatter_or_participants(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = ROOT_FIXTURE_DIR / "test_transcript_entities.txt"
        config = FolioConfig(library_root=library)
        _import_org_chart(library)
        mock_analyze.return_value = _analysis_result(
            entities={
                "people": ["Bob"],
                "departments": ["Engineering"],
                "systems": [],
                "processes": [],
            }
        )

        result = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            participants=["Bob"],
        )

        fm = _parse_frontmatter(result.output_path)
        assert fm["participants"] == ["Bob"]
        assert "people" not in fm
        assert "departments" not in fm
        assert "systems" not in fm
        assert "processes" not in fm

    @patch("folio.ingest.analyze_interaction_text", side_effect=EndpointNotAllowedError())
    def test_ingest_provider_failure_writes_degraded_note(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "client_meeting.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("client_meeting.txt"), source)

        config = FolioConfig(library_root=library)

        result = ingest_source(
            config,
            source_path=source,
            subtype="client_meeting",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        assert result.degraded is True
        assert result.llm_status == "pending"

        fm = _parse_frontmatter(result.output_path)
        assert fm["review_status"] == "flagged"
        assert fm["review_flags"] == ["analysis_unavailable"]
        assert fm["extraction_confidence"] is None
        assert fm["_llm_metadata"]["ingest"]["status"] == "pending"
        body = result.output_path.read_text()
        assert "Analysis Unavailable" in body
        assert "> [!quote]- Raw Transcript" in body

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_explicit_target_warns_on_subtype_override(self, mock_analyze, tmp_path, caplog):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "expert_interview.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("expert_interview.md"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        first = ingest_source(
            config,
            source_path=source,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        caplog.clear()
        with caplog.at_level("WARNING", logger="folio.ingest"):
            second = ingest_source(
                config,
                source_path=source,
                subtype="client_meeting",
                event_date=date(2026, 3, 21),
                client="ClientA",
                engagement="DD Q1 2026",
                target=first.output_path,
            )

        assert second.output_path == first.output_path
        assert "differs from requested ingest subtype" in caplog.text
        fm = _parse_frontmatter(second.output_path)
        assert fm["subtype"] == "client_meeting"

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_strips_markdown_frontmatter_from_raw_transcript(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "markdown_with_frontmatter.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("markdown_with_frontmatter.md"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        result = ingest_source(
            config,
            source_path=source,
            subtype="internal_sync",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        body = result.output_path.read_text()
        assert "title: Example Notes" not in body
        assert "client: ClientA" not in body.split("> [!quote]- Raw Transcript", 1)[1]
        assert "# Wrapped Transcript" in body

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_collision_safe_artifact_naming(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source_a = tmp_path / "a" / "interview.md"
        source_b = tmp_path / "b" / "interview.md"
        source_a.parent.mkdir(parents=True, exist_ok=True)
        source_b.parent.mkdir(parents=True, exist_ok=True)
        source_a.write_text("# Interview\n\nJane Smith: First interview body.")
        source_b.write_text("# Interview\n\nJane Smith: Second interview body.")

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        first = ingest_source(
            config,
            source_path=source_a,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
            title="Interview Notes",
        )
        second = ingest_source(
            config,
            source_path=source_b,
            subtype="expert_interview",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
            title="Interview Notes",
        )

        assert first.output_path.parent != second.output_path.parent
        assert first.output_path.parent.name.startswith("2026-03-21_interview_")
        assert second.output_path.parent.name.startswith("2026-03-21_interview_")
        assert first.output_path.parent.name != second.output_path.parent.name

    def test_ingest_whitespace_only_source_writes_degraded_note(self, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "whitespace_only.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("whitespace_only.txt"), source)

        config = FolioConfig(library_root=library)

        result = ingest_source(
            config,
            source_path=source,
            subtype="internal_sync",
            event_date=date(2026, 3, 21),
            client="ClientA",
            engagement="DD Q1 2026",
        )

        assert result.degraded is True
        fm = _parse_frontmatter(result.output_path)
        assert fm["review_status"] == "flagged"
        assert fm["review_flags"] == ["analysis_unavailable"]
        assert fm["extraction_confidence"] is None
        assert "Analysis Unavailable" in result.output_path.read_text()

    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_rejects_stale_registry_match_with_missing_markdown(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "expert_interview.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("expert_interview.md"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result()

        from folio.tracking.sources import compute_file_hash

        source_hash = compute_file_hash(source)
        save_registry(
            library / "registry.json",
            {
                "_schema_version": 1,
                "decks": {
                    "test_interaction_20260310_call": _sample_interaction_registry_entry(
                        markdown_path="Client/interactions/call/missing.md",
                        deck_dir="Client/interactions/call",
                        source_relative_path="../../../transcripts/expert_interview.md",
                        source_hash=source_hash,
                        subtype="expert_interview",
                    ),
                },
            },
        )

        with pytest.raises(IngestError, match="missing or unreadable"):
            ingest_source(
                config,
                source_path=source,
                subtype="expert_interview",
                event_date=date(2026, 3, 21),
                client="ClientA",
                engagement="DD Q1 2026",
            )
