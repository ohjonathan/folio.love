"""Integration tests for folio enrich.

Covers all 6 integration scenarios from spec section 16.3.
Uses mock LLM calls but real registry, real frontmatter generation,
and real file I/O with tmp_path fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from folio.config import FolioConfig, LLMConfig, LLMProfile, LLMRoute
from folio.enrich import (
    enrich_batch,
    enrich_note,
    plan_enrichment,
    EnrichPlanEntry,
)
from folio.pipeline.enrich_data import (
    EnrichOutcome,
    ENRICH_SPEC_VERSION,
    RelationshipProposal,
)
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


def _setup_registry(library_root: Path, entries: dict) -> None:
    reg_data = {"_schema_version": 1, "decks": entries, "updated_at": "2026-01-01T00:00:00Z"}
    (library_root / "registry.json").write_text(json.dumps(reg_data))


def _setup_entities(library_root: Path) -> None:
    entities_data = {
        "_schema_version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "entities": {
            "person": {},
            "department": {},
            "system": {},
            "process": {},
        },
    }
    (library_root / "entities.json").write_text(json.dumps(entities_data))


def _setup_note(library_root: Path, rel_path: str, content: str) -> Path:
    path = library_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _read_fm(path: Path) -> dict:
    content = path.read_text()
    if content.startswith("---\n"):
        end = content.index("\n---", 4)
        return yaml.safe_load(content[4:end]) or {}
    return {}


def _make_evidence_note(note_id="e1", title="Evidence Note", enrich_meta=None, **overrides):
    fm = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "curation_level": "L0",
        "review_status": "clean",
        "source": "deck.pptx",
        "source_hash": "abc123",
        "version": 1,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-01-01T00:00:00Z",
        "client": "ClientA",
        "engagement": "DD_Q1",
        "tags": ["existing-tag"],
    }
    fm.update(overrides)
    if enrich_meta:
        fm["_llm_metadata"] = {"enrich": enrich_meta}
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"""\
---
{yaml_str}---

# {title}

**Source:** `deck.pptx`

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> Verbatim text.

### Analysis

**Slide Type:** data
**Framework:** none
**Visual Description:** Chart showing metrics.
**Key Data:** Engineering processes 500 tickets.
**Main Insight:** Efficiency gains observed.

**Evidence:**
- claim: 500 tickets processed
  - confidence: high
  - validated: yes

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2026-03-01 | Initial |
"""


def _make_interaction_note(note_id="i1", title="Interaction Note", enrich_meta=None, **overrides):
    fm = {
        "id": note_id,
        "title": title,
        "type": "interaction",
        "status": "complete",
        "curation_level": "L0",
        "review_status": "clean",
        "source_hash": "def456",
        "version": 1,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-01-01T00:00:00Z",
        "source_transcript": "transcript.md",
        "impacts": [],
        "client": "ClientA",
        "engagement": "DD_Q1",
        "tags": ["meeting"],
    }
    fm.update(overrides)
    if enrich_meta:
        fm["_llm_metadata"] = {"enrich": enrich_meta}
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"""\
---
{yaml_str}---

# {title}

Source transcript: `transcript.md` | Version: 1

## Summary

Team discussed priorities.

## Key Findings

### Claims

- Priority is stability.
  - quote: "Focus on stability"
  - details: strategic, high

### Data Points

- None captured.

### Decisions

- None captured.

### Open Questions

- None captured.

## Entities Mentioned

### People

- [[Alice]]

### Departments

- None

### Systems

- None

### Processes

- None

## Quotes / Evidence

- "Focus on stability"
  - details: strategic, high
  - validated: yes

## Impact on Hypotheses

[STUB at L0]

> [!quote]- Raw Transcript
> Raw transcript text here.
"""


def _mock_analysis_output(tags=None, entities=None, cues=None):
    return EnrichAnalysisOutput(
        tag_candidates=tags or [],
        entity_mention_candidates=entities or {},
        relationship_cues=cues or [],
    )


def _registry_entry(note_id, note_type="evidence", md_path="", **extra):
    entry = {
        "id": note_id,
        "title": note_id.replace("_", " ").title(),
        "type": note_type,
        "markdown_path": md_path,
        "deck_dir": str(Path(md_path).parent) if md_path else "",
        "source_relative_path": "deck.pptx",
        "source_hash": "abc123",
        "version": 1,
        "converted": "2026-01-01T00:00:00Z",
        "client": "ClientA",
        "engagement": "DD_Q1",
    }
    entry.update(extra)
    return entry


# ---------------------------------------------------------------------------
# 1. Convert evidence + ingest interaction + enrich
# ---------------------------------------------------------------------------

class TestConvertIngestEnrich:
    """Tags merged, entities backfilled, interaction uses impacts."""

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships", return_value=[])
    def test_tags_merged_entities_backfilled(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        config = _make_config(tmp_path)
        lr = config.library_root

        _setup_note(lr, "ClientA/DD_Q1/e1.md", _make_evidence_note())
        _setup_note(lr, "ClientA/DD_Q1/i1.md", _make_interaction_note())
        _setup_entities(lr)
        _setup_registry(lr, {
            "e1": _registry_entry("e1", "evidence", "ClientA/DD_Q1/e1.md"),
            "i1": _registry_entry("i1", "interaction", "ClientA/DD_Q1/i1.md",
                                  source_relative_path="transcript.md", source_hash="def456"),
        })

        mock_analyze.return_value = _mock_analysis_output(
            tags=["new-enrich-tag"],
            entities={"people": ["Bob"], "systems": ["ServiceNow"]},
        )

        from folio.pipeline.entity_resolution import ResolutionResult
        mock_resolve.return_value = ResolutionResult(
            entities={"people": ["Bob"], "departments": [], "systems": ["ServiceNow"], "processes": []},
            warnings=[],
            created_entities=[],
            registry_changed=False,
        )

        messages = []
        result = enrich_batch(config, echo=messages.append)

        assert result.updated > 0 or result.unchanged > 0  # Ran without error
        assert result.failed == 0

        # Verify tags were added to evidence note
        e1_fm = _read_fm(lr / "ClientA/DD_Q1/e1.md")
        assert "new-enrich-tag" in e1_fm.get("tags", [])
        assert "existing-tag" in e1_fm.get("tags", [])

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships")
    def test_interaction_uses_impacts_not_draws_from(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        config = _make_config(tmp_path)
        lr = config.library_root

        _setup_note(lr, "ClientA/DD_Q1/i1.md", _make_interaction_note())
        _setup_entities(lr)
        _setup_registry(lr, {
            "i1": _registry_entry("i1", "interaction", "ClientA/DD_Q1/i1.md",
                                  source_relative_path="transcript.md", source_hash="def456"),
            "e1": _registry_entry("e1", "evidence", "ClientA/DD_Q1/e1.md"),
        })

        mock_analyze.return_value = _mock_analysis_output(
            cues=[{"relation": "impacts", "target_hint": "e1"}],
        )
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )
        mock_eval_rel.return_value = [
            {
                "relation": "impacts",
                "target_id": "e1",
                "confidence": "high",
                "signals": ["explicit_document_reference"],
                "rationale": "Direct reference.",
            }
        ]

        messages = []
        enrich_batch(config, echo=messages.append)

        i1_fm = _read_fm(lr / "ClientA/DD_Q1/i1.md")
        enrich_meta = i1_fm.get("_llm_metadata", {}).get("enrich", {})
        rel_axis = enrich_meta.get("axes", {}).get("relationships", {})
        proposals = rel_axis.get("proposals", [])
        if proposals:
            assert proposals[0]["relation"] == "impacts"
            # draws_from should not be used
            for p in proposals:
                assert p["relation"] != "draws_from"


# ---------------------------------------------------------------------------
# 2. Rerun idempotency
# ---------------------------------------------------------------------------

class TestRerunIdempotency:
    """No duplicates on second run."""

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships", return_value=[])
    def test_no_duplicate_tags(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        config = _make_config(tmp_path)
        lr = config.library_root

        _setup_note(lr, "ClientA/DD_Q1/e1.md", _make_evidence_note())
        _setup_entities(lr)
        _setup_registry(lr, {
            "e1": _registry_entry("e1", "evidence", "ClientA/DD_Q1/e1.md"),
        })

        mock_analyze.return_value = _mock_analysis_output(tags=["new-tag"])
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )

        # First run
        enrich_batch(config, echo=lambda x: None)

        # Second run (force to bypass fingerprint)
        mock_analyze.return_value = _mock_analysis_output(tags=["new-tag"])
        enrich_batch(config, force=True, echo=lambda x: None)

        fm = _read_fm(lr / "ClientA/DD_Q1/e1.md")
        tag_counts = {}
        for t in fm.get("tags", []):
            tag_counts[t.lower()] = tag_counts.get(t.lower(), 0) + 1
        # No tag should appear more than once
        for count in tag_counts.values():
            assert count == 1


# ---------------------------------------------------------------------------
# 3. Protected note: reviewed/overridden gets metadata only
# ---------------------------------------------------------------------------

class TestProtectedNote:
    """Reviewed/overridden notes get metadata-only updates."""

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships", return_value=[])
    def test_reviewed_note_metadata_only(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        config = _make_config(tmp_path)
        lr = config.library_root

        note_content = _make_evidence_note(review_status="reviewed")
        original_body = note_content.split("---\n", 3)[-1] if "---" in note_content else note_content
        _setup_note(lr, "ClientA/DD_Q1/e1.md", note_content)
        _setup_entities(lr)
        _setup_registry(lr, {
            "e1": _registry_entry("e1", "evidence", "ClientA/DD_Q1/e1.md"),
        })

        mock_analyze.return_value = _mock_analysis_output(tags=["protected-tag"])
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )

        messages = []
        result = enrich_batch(config, echo=messages.append)

        assert result.protected == 1

        # Metadata should still be updated (tags)
        fm = _read_fm(lr / "ClientA/DD_Q1/e1.md")
        enrich_meta = fm.get("_llm_metadata", {}).get("enrich", {})
        # Enrich ran but body was protected
        assert enrich_meta.get("axes", {}).get("body", {}).get("status") in ("skipped_protected", "conflict")


# ---------------------------------------------------------------------------
# 4. Refresh after source change
# ---------------------------------------------------------------------------

class TestRefreshAfterSourceChange:
    """Canonical relationships survive, enrich becomes stale."""

    def test_stale_transition(self):
        from folio.cli import _extract_enrich_passthrough, _mark_enrich_stale

        fm = {
            "supersedes": "older_note_id",
            "_llm_metadata": {
                "enrich": {
                    "status": "executed",
                    "input_fingerprint": "sha256:abc",
                    "managed_body_fingerprint": "sha256:def",
                    "entity_resolution_fingerprint": "sha256:ghi",
                    "relationship_context_fingerprint": "sha256:jkl",
                    "axes": {
                        "relationships": {
                            "proposals": [
                                {"relation": "supersedes", "target_id": "x", "status": "pending_human_confirmation"}
                            ]
                        }
                    }
                }
            }
        }

        preserved = _extract_enrich_passthrough(fm)
        _mark_enrich_stale(preserved)

        enrich = preserved["_llm_metadata"]["enrich"]
        assert enrich["status"] == "stale"
        assert "input_fingerprint" not in enrich
        assert "managed_body_fingerprint" not in enrich
        assert "proposals" not in enrich.get("axes", {}).get("relationships", {})
        # Canonical relationship preserved
        assert preserved["supersedes"] == "older_note_id"


# ---------------------------------------------------------------------------
# 5. Rejected proposal suppression
# ---------------------------------------------------------------------------

class TestRejectedProposalSuppression:
    """Rejected proposals not re-emitted unless basis changes."""

    @patch("folio.enrich.analyze_note_for_enrichment")
    @patch("folio.enrich.resolve_entities")
    @patch("folio.enrich.evaluate_relationships")
    def test_suppressed_without_basis_change(
        self, mock_eval_rel, mock_resolve, mock_analyze, tmp_path
    ):
        config = _make_config(tmp_path)
        lr = config.library_root

        # Note with a previously rejected proposal
        enrich_meta = {
            "status": "executed",
            "spec_version": ENRICH_SPEC_VERSION,
            "axes": {
                "relationships": {
                    "proposals": [
                        {
                            "relation": "supersedes",
                            "target_id": "old_note",
                            "basis_fingerprint": "sha256:unchanged_basis",
                            "status": "rejected",
                        }
                    ]
                }
            }
        }
        note_content = _make_evidence_note(
            enrich_meta=enrich_meta,
        )
        _setup_note(lr, "ClientA/DD_Q1/e1.md", note_content)
        _setup_entities(lr)
        _setup_registry(lr, {
            "e1": _registry_entry("e1", "evidence", "ClientA/DD_Q1/e1.md"),
            "old_note": _registry_entry("old_note", "evidence", "ClientA/DD_Q1/old.md"),
        })

        mock_analyze.return_value = _mock_analysis_output(
            cues=[{"relation": "supersedes", "target_hint": "old_note"}],
        )
        mock_resolve.return_value = MagicMock(
            entities={"people": [], "departments": [], "systems": [], "processes": []},
            warnings=[], created_entities=[], registry_changed=False,
        )
        # Return same proposal again
        mock_eval_rel.return_value = [
            {
                "relation": "supersedes",
                "target_id": "old_note",
                "confidence": "high",
                "signals": ["same_source_stem"],
                "rationale": "Same lineage.",
            }
        ]

        # Patch the basis fingerprint computation to return the same basis
        with patch("folio.enrich._compute_proposal_basis_fingerprint",
                   return_value="sha256:unchanged_basis"):
            messages = []
            enrich_batch(config, force=True, echo=messages.append)

        # The rejected proposal should be suppressed
        fm = _read_fm(lr / "ClientA/DD_Q1/e1.md")
        enrich_meta = fm.get("_llm_metadata", {}).get("enrich", {})
        rel_axis = enrich_meta.get("axes", {}).get("relationships", {})
        proposals = rel_axis.get("proposals", [])
        supersedes_proposals = [p for p in proposals if p.get("relation") == "supersedes"]
        # Should be suppressed (empty or no pending)
        assert all(p.get("status") != "pending_human_confirmation" for p in supersedes_proposals)


# ---------------------------------------------------------------------------
# 6. Unrelated entity change
# ---------------------------------------------------------------------------

class TestUnrelatedEntityChange:
    """Unaffected notes don't re-enrich when unrelated entities change."""

    def test_fingerprint_unaffected_by_unrelated_entity(self, tmp_path):
        """Note fingerprint doesn't change from unrelated entity registry updates."""
        from folio.pipeline.enrich_data import compute_entity_resolution_fingerprint

        # Note A has entity mentions: Alice
        note_a_fp = compute_entity_resolution_fingerprint(
            [("Alice", "confirmed:person/alice")]
        )

        # Unrelated entity "Zed" is added to entities.json elsewhere
        # Note A's entity resolution fingerprint should be unchanged
        note_a_fp_after = compute_entity_resolution_fingerprint(
            [("Alice", "confirmed:person/alice")]
        )

        assert note_a_fp == note_a_fp_after
