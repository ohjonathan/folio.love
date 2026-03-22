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
from folio.ingest import IngestAmbiguityError, IngestSubtypeMismatchError, ingest_source
from folio.llm.runtime import EndpointNotAllowedError
from folio.pipeline.interaction_analysis import InteractionAnalysisResult, InteractionFinding, InteractionQuote
from folio.tracking.registry import save_registry


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ingest"


def _fixture(name: str) -> Path:
    return FIXTURE_DIR / name


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


def _analysis_result(*, llm_status: str = "executed", review_status: str = "clean", tags: list[str] | None = None) -> InteractionAnalysisResult:
    return InteractionAnalysisResult(
        summary="The team described a successful operational change and a follow-up dependency.",
        tags=tags or ["expert-interview", "operations"],
        entities={
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
    )


def _parse_frontmatter(md_path: Path) -> dict:
    content = md_path.read_text()
    yaml_block = content.split("---", 2)[1].strip()
    return yaml.safe_load(yaml_block)


class TestIngestIntegration:
    @patch("folio.ingest.analyze_interaction_text")
    def test_ingest_writes_interaction_note_and_registry(self, mock_analyze, tmp_path):
        library = _make_library(tmp_path)
        source = tmp_path / "transcripts" / "expert_interview.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_fixture("expert_interview.md"), source)

        config = FolioConfig(library_root=library)
        mock_analyze.return_value = _analysis_result(tags=["expert-interview", "technology"])

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
