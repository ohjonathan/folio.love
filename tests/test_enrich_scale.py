"""Scale test with 50+ fixture notes for folio enrich.

Exercises incremental processing, continue-on-error, summary reporting,
protected/conflict paths, diagram-note skip behavior, dry-run planning,
and pre-run call estimation output (spec section 16.4).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from folio.config import FolioConfig, LLMConfig, LLMProfile, LLMRoute
from folio.enrich import enrich_batch, plan_enrichment
from folio.pipeline.enrich_data import EnrichOutcome, ENRICH_SPEC_VERSION
from folio.pipeline.enrich_analysis import EnrichAnalysisOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path) -> FolioConfig:
    library_root = tmp_path / "library"
    library_root.mkdir(exist_ok=True)
    return FolioConfig(
        library_root=library_root,
        llm=LLMConfig(
            profiles={
                "default": LLMProfile(name="default", provider="anthropic", model="test-model"),
            },
            routing={
                "default": LLMRoute(primary="default"),
                "enrich": LLMRoute(primary="default"),
            },
        ),
    )


def _make_evidence_note(note_id, client="ClientA", engagement="DD_Q1",
                         curation_level="L0", review_status="clean",
                         enrich_meta=None, tags=None):
    fm = {
        "id": note_id,
        "title": note_id.replace("_", " ").title(),
        "type": "evidence",
        "status": "active",
        "curation_level": curation_level,
        "review_status": review_status,
        "source": "deck.pptx",
        "source_hash": f"hash_{note_id}",
        "version": 1,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-01-01T00:00:00Z",
        "client": client,
        "engagement": engagement,
        "tags": tags or ["auto-tag"],
    }
    if enrich_meta:
        fm["_llm_metadata"] = {"enrich": enrich_meta}
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"""\
---
{yaml_str}---

# {fm['title']}

**Source:** `deck.pptx`

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> Some text.

### Analysis

**Slide Type:** data
**Framework:** none
**Visual Description:** Chart.
**Key Data:** Data point.
**Main Insight:** Insight.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2026-03-01 | Initial |
"""


def _make_interaction_note(note_id, client="ClientA", engagement="DD_Q1"):
    fm = {
        "id": note_id,
        "title": note_id.replace("_", " ").title(),
        "type": "interaction",
        "status": "complete",
        "curation_level": "L0",
        "review_status": "clean",
        "source_hash": f"hash_{note_id}",
        "version": 1,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-01-01T00:00:00Z",
        "source_transcript": "transcript.md",
        "impacts": [],
        "client": client,
        "engagement": engagement,
        "tags": ["meeting"],
    }
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"""\
---
{yaml_str}---

# {fm['title']}

Source transcript: `transcript.md` | Version: 1

## Summary

Discussion summary.

## Key Findings

### Claims

- A claim.
  - quote: "Quote"
  - details: strategic, high

### Data Points

- None captured.

### Decisions

- None captured.

### Open Questions

- None captured.

## Entities Mentioned

### People

- None

### Departments

- None

### Systems

- None

### Processes

- None

## Quotes / Evidence

- "Quote"
  - details: strategic, high
  - validated: yes

## Impact on Hypotheses

[STUB at L0]

> [!quote]- Raw Transcript
> Transcript here.
"""


def _setup_scale_fixture(tmp_path: Path) -> tuple[FolioConfig, dict]:
    """Create 50+ notes across multiple clients/engagements.

    Mix:
    - 30 evidence notes (L0, various clients)
    - 10 interaction notes (L0)
    - 5 evidence notes (L1, protected)
    - 3 evidence notes (reviewed, protected)
    - 2 evidence notes (with stale enrich)
    - 5 diagram entries (should be skipped)
    """
    config = _make_config(tmp_path)
    lr = config.library_root
    entries: dict = {}

    # 30 L0 evidence notes across 3 clients
    for i in range(30):
        client = f"Client{chr(65 + i % 3)}"  # A, B, C
        engagement = f"Eng_{i // 10}"
        note_id = f"evidence_{i:03d}"
        rel_path = f"{client}/{engagement}/{note_id}.md"
        content = _make_evidence_note(note_id, client, engagement)
        (lr / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (lr / rel_path).write_text(content)
        entries[note_id] = {
            "id": note_id,
            "title": note_id.replace("_", " ").title(),
            "type": "evidence",
            "markdown_path": rel_path,
            "deck_dir": str(Path(rel_path).parent),
            "source_relative_path": "deck.pptx",
            "source_hash": f"hash_{note_id}",
            "version": 1,
            "converted": "2026-01-01T00:00:00Z",
            "client": client,
            "engagement": engagement,
        }

    # 10 L0 interaction notes
    for i in range(10):
        client = f"Client{chr(65 + i % 3)}"
        engagement = f"Eng_{i // 5}"
        note_id = f"interaction_{i:03d}"
        rel_path = f"{client}/{engagement}/{note_id}.md"
        content = _make_interaction_note(note_id, client, engagement)
        (lr / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (lr / rel_path).write_text(content)
        entries[note_id] = {
            "id": note_id,
            "title": note_id.replace("_", " ").title(),
            "type": "interaction",
            "markdown_path": rel_path,
            "deck_dir": str(Path(rel_path).parent),
            "source_relative_path": "transcript.md",
            "source_hash": f"hash_{note_id}",
            "version": 1,
            "converted": "2026-01-01T00:00:00Z",
            "client": client,
            "engagement": engagement,
        }

    # 5 L1 evidence notes (protected)
    for i in range(5):
        note_id = f"protected_l1_{i:03d}"
        rel_path = f"ClientA/Eng_0/{note_id}.md"
        content = _make_evidence_note(note_id, curation_level="L1")
        (lr / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (lr / rel_path).write_text(content)
        entries[note_id] = {
            "id": note_id,
            "title": note_id.replace("_", " ").title(),
            "type": "evidence",
            "markdown_path": rel_path,
            "deck_dir": str(Path(rel_path).parent),
            "source_relative_path": "deck.pptx",
            "source_hash": f"hash_{note_id}",
            "version": 1,
            "converted": "2026-01-01T00:00:00Z",
            "client": "ClientA",
            "engagement": "Eng_0",
        }

    # 3 reviewed evidence notes (protected)
    for i in range(3):
        note_id = f"reviewed_{i:03d}"
        rel_path = f"ClientA/Eng_0/{note_id}.md"
        content = _make_evidence_note(note_id, review_status="reviewed")
        (lr / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (lr / rel_path).write_text(content)
        entries[note_id] = {
            "id": note_id,
            "title": note_id.replace("_", " ").title(),
            "type": "evidence",
            "markdown_path": rel_path,
            "deck_dir": str(Path(rel_path).parent),
            "source_relative_path": "deck.pptx",
            "source_hash": f"hash_{note_id}",
            "version": 1,
            "converted": "2026-01-01T00:00:00Z",
            "client": "ClientA",
            "engagement": "Eng_0",
        }

    # 2 stale evidence notes
    for i in range(2):
        note_id = f"stale_{i:03d}"
        rel_path = f"ClientA/Eng_0/{note_id}.md"
        enrich_meta = {"status": "stale"}
        content = _make_evidence_note(note_id, enrich_meta=enrich_meta)
        (lr / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (lr / rel_path).write_text(content)
        entries[note_id] = {
            "id": note_id,
            "title": note_id.replace("_", " ").title(),
            "type": "evidence",
            "markdown_path": rel_path,
            "deck_dir": str(Path(rel_path).parent),
            "source_relative_path": "deck.pptx",
            "source_hash": f"hash_{note_id}",
            "version": 1,
            "converted": "2026-01-01T00:00:00Z",
            "client": "ClientA",
            "engagement": "Eng_0",
        }

    # 5 diagram entries (should be skipped at eligibility)
    for i in range(5):
        note_id = f"diagram_{i:03d}"
        entries[note_id] = {
            "id": note_id,
            "title": f"Diagram {i}",
            "type": "diagram",
            "markdown_path": f"ClientA/Eng_0/diagrams/{note_id}.md",
            "deck_dir": "ClientA/Eng_0/diagrams",
            "source_relative_path": "deck.pptx",
            "source_hash": f"hash_{note_id}",
            "version": 1,
            "converted": "2026-01-01T00:00:00Z",
        }

    # Write registry
    reg_data = {
        "_schema_version": 1,
        "decks": entries,
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (lr / "registry.json").write_text(json.dumps(reg_data))

    # Write empty entities.json
    entities = {
        "_schema_version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "entities": {"person": {}, "department": {}, "system": {}, "process": {}},
    }
    (lr / "entities.json").write_text(json.dumps(entities))

    return config, entries


# ---------------------------------------------------------------------------
# Scale tests
# ---------------------------------------------------------------------------

class TestScaleBatch:
    """Scale test with 50+ fixture notes."""

    def test_fixture_has_50_plus_notes(self, tmp_path):
        """Verify the fixture produces enough notes."""
        config, entries = _setup_scale_fixture(tmp_path)
        # 30 + 10 + 5 + 3 + 2 + 5 = 55 entries
        assert len(entries) == 55
        # Diagram entries should be filtered at eligibility
        eligible_types = sum(
            1 for e in entries.values()
            if e.get("type") in ("evidence", "interaction")
        )
        assert eligible_types == 50

    def test_dry_run_planning(self, tmp_path):
        """Dry-run plans all notes without LLM calls."""
        config, _ = _setup_scale_fixture(tmp_path)

        messages = []
        result = enrich_batch(config, dry_run=True, echo=messages.append)

        # Should not have failed
        assert result.failed == 0

        # Summary should include all disposition counts
        summary = messages[-1]
        assert "would_analyze" in summary
        assert "would_protect" in summary

        # Protected count should include L1 + reviewed
        assert result.protected >= 8  # 5 L1 + 3 reviewed

    def test_call_estimation_output(self, tmp_path):
        """Pre-run output shows estimated calls."""
        config, _ = _setup_scale_fixture(tmp_path)

        messages = []
        enrich_batch(config, dry_run=True, echo=messages.append)

        # Should have scope and estimated calls lines
        scope_line = [m for m in messages if "eligible document" in m]
        assert len(scope_line) == 1

        calls_line = [m for m in messages if "Estimated calls" in m]
        assert len(calls_line) == 1
        assert "primary=" in calls_line[0]
        assert "relationship<=" in calls_line[0]

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships", return_value=[])
    def test_incremental_processing(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        """First run processes all, second run skips unchanged."""
        config, _ = _setup_scale_fixture(tmp_path)

        mock_analyze.return_value = EnrichAnalysisOutput(
            tag_candidates=["scale-tag"],
            entity_mention_candidates={},
            relationship_cues=[],
        )
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )

        # First run
        messages1 = []
        result1 = enrich_batch(config, echo=messages1.append)
        first_run_analyzed = result1.updated + result1.unchanged

        # Second run (without force) should skip most
        messages2 = []
        result2 = enrich_batch(config, echo=messages2.append)
        # Many should be skipped as unchanged
        assert result2.unchanged > 0

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships", return_value=[])
    def test_continue_on_error(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        """Batch continues after per-file failures."""
        config, _ = _setup_scale_fixture(tmp_path)

        call_count = [0]

        def _failing_analyze(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise RuntimeError("Simulated LLM failure")
            return EnrichAnalysisOutput(
                tag_candidates=[],
                entity_mention_candidates={},
                relationship_cues=[],
            )

        mock_analyze.side_effect = _failing_analyze
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )

        messages = []
        result = enrich_batch(config, echo=messages.append)

        # Should have some failures but also some successes
        assert result.failed >= 2
        # Should not have aborted early — other notes processed
        total_processed = result.updated + result.unchanged + result.protected + result.conflicted + result.failed
        assert total_processed > 2

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships", return_value=[])
    def test_summary_reporting(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        """Summary line contains all disposition counts."""
        config, _ = _setup_scale_fixture(tmp_path)

        mock_analyze.return_value = EnrichAnalysisOutput(
            tag_candidates=["new-tag"],
            entity_mention_candidates={},
            relationship_cues=[],
        )
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )

        messages = []
        result = enrich_batch(config, echo=messages.append)

        summary = messages[-1]
        assert "updated" in summary
        assert "unchanged" in summary
        assert "protected" in summary
        assert "conflicted" in summary
        assert "failed" in summary

    def test_diagram_notes_skipped(self, tmp_path):
        """Diagram entries are not included in the plan."""
        config, entries = _setup_scale_fixture(tmp_path)

        plan = plan_enrichment(config)
        plan_ids = {e.entry.id for e in plan}

        # No diagram entries should be in the plan
        for note_id, entry_data in entries.items():
            if entry_data.get("type") == "diagram":
                assert note_id not in plan_ids

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships", return_value=[])
    def test_protected_and_conflict_paths(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        """Protected (L1, reviewed) notes are reported correctly."""
        config, _ = _setup_scale_fixture(tmp_path)

        mock_analyze.return_value = EnrichAnalysisOutput()
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )

        messages = []
        result = enrich_batch(config, echo=messages.append)

        # Should have protected notes (L1 + reviewed = 8)
        assert result.protected >= 8

        # Check that protected notes appear in output
        protected_messages = [m for m in messages if "protected" in m]
        assert len(protected_messages) >= 8

    def test_scope_filtering(self, tmp_path):
        """Scope filter limits to matching entries."""
        config, _ = _setup_scale_fixture(tmp_path)

        # Filter to ClientA only
        plan = plan_enrichment(config, scope="ClientA")
        for entry in plan:
            assert entry.entry.markdown_path.startswith("ClientA/") or \
                   entry.entry.deck_dir.startswith("ClientA/")

        # Filter to specific engagement
        plan_narrow = plan_enrichment(config, scope="ClientA/Eng_0")
        assert len(plan_narrow) < len(plan) or len(plan_narrow) == len(plan)
        for entry in plan_narrow:
            path = entry.entry.markdown_path
            assert "ClientA/Eng_0" in path or entry.entry.deck_dir.startswith("ClientA/Eng_0")
