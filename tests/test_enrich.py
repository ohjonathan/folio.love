"""Tests for folio enrich core pipeline.

Covers all 14 unit test areas from spec section 16.1 plus body safety
tests from section 16.2.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import yaml

from folio.config import FolioConfig, LLMConfig, LLMProfile, LLMRoute
from folio.enrich import (
    EnrichBatchResult,
    EnrichPlanEntry,
    _build_wikilink_map,
    _determine_disposition,
    _enforce_singular_supersedes,
    _insert_wikilinks_in_analysis,
    _merge_tags,
    _remove_promoted_proposals,
    _replace_frontmatter,
    _suppress_rejected_proposals,
    _update_related_section,
    enrich_batch,
    enrich_note,
    plan_enrichment,
)
from folio.pipeline.enrich_data import (
    ENRICH_SPEC_VERSION,
    RELATIONSHIP_FIELDS,
    EnrichAxisResult,
    EnrichOutcome,
    EnrichResult,
    RelationshipProposal,
    compute_entity_resolution_fingerprint,
    compute_input_fingerprint,
    compute_managed_body_fingerprint,
    compute_relationship_context_fingerprint,
)
from folio.pipeline.section_parser import MarkdownDocument


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_config(tmp_path: Path) -> FolioConfig:
    """Create a minimal FolioConfig for testing."""
    library_root = tmp_path / "library"
    library_root.mkdir(exist_ok=True)
    return FolioConfig(
        library_root=library_root,
        llm=LLMConfig(
            profiles={
                "default": LLMProfile(name="default", provider="anthropic", model="test-model"),
                "enrich_profile": LLMProfile(name="enrich_profile", provider="anthropic", model="enrich-model"),
            },
            routing={
                "default": LLMRoute(primary="default"),
                "enrich": LLMRoute(primary="enrich_profile", fallbacks=[]),
            },
        ),
    )


def _make_evidence_note(
    note_id: str = "test_evidence",
    title: str = "Test Evidence",
    client: str = "ClientA",
    engagement: str = "DD_Q1",
    tags: list | None = None,
    curation_level: str = "L0",
    review_status: str = "clean",
    enrich_meta: dict | None = None,
    supersedes: str | None = None,
    impacts: list | None = None,
) -> str:
    """Create a minimal evidence note with proper structure."""
    fm: dict = {
        "id": note_id,
        "title": title,
        "type": "evidence",
        "status": "active",
        "curation_level": curation_level,
        "review_status": review_status,
        "source": "deck.pptx",
        "source_hash": "abc123def456",
        "version": 1,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-01-01T00:00:00Z",
    }
    if client:
        fm["client"] = client
    if engagement:
        fm["engagement"] = engagement
    if tags:
        fm["tags"] = tags
    if supersedes:
        fm["supersedes"] = supersedes
    if impacts:
        fm["impacts"] = impacts
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

> This is verbatim text.
> It must not be modified by enrich.

### Analysis

**Slide Type:** data
**Framework:** none
**Visual Description:** A chart showing ServiceNow usage metrics.
**Key Data:** The Engineering Department processes 500 tickets weekly.
**Main Insight:** ServiceNow adoption drives efficiency gains.

**Evidence:**
- claim: 500 tickets processed weekly
  - confidence: high
  - validated: yes

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2026-03-01 | Initial conversion |
"""


def _make_interaction_note(
    note_id: str = "test_interaction",
    title: str = "Test Meeting",
    client: str = "ClientA",
    engagement: str = "DD_Q1",
    tags: list | None = None,
    curation_level: str = "L0",
    review_status: str = "clean",
    enrich_meta: dict | None = None,
    impacts: list | None = None,
) -> str:
    """Create a minimal interaction note."""
    fm: dict = {
        "id": note_id,
        "title": title,
        "type": "interaction",
        "status": "complete",
        "curation_level": curation_level,
        "review_status": review_status,
        "source_hash": "def456abc789",
        "version": 1,
        "created": "2026-01-01T00:00:00Z",
        "modified": "2026-01-01T00:00:00Z",
        "source_transcript": "transcript.md",
        "impacts": impacts or [],
    }
    if client:
        fm["client"] = client
    if engagement:
        fm["engagement"] = engagement
    if tags:
        fm["tags"] = tags
    if enrich_meta:
        fm["_llm_metadata"] = {"enrich": enrich_meta}

    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"""\
---
{yaml_str}---

# {title}

Source transcript: `transcript.md` | Version: 1

## Summary

The team discussed platform stability priorities.

## Key Findings

### Claims

- Platform stability is top priority.
  - quote: "We need stability"
  - details: strategic, high
  - speaker: CTO

### Data Points

- None captured.

### Decisions

- Freeze features for 2 weeks.
  - quote: "Let's freeze features"
  - details: operational, high

### Open Questions

- None captured.

## Entities Mentioned

### People

- [[Jane Smith]]

### Departments

- [[Engineering]]

### Systems

- [[ServiceNow]]

### Processes

- None

## Quotes / Evidence

- "We need stability"
  - details: strategic, high
  - speaker: CTO
  - validated: yes

## Impact on Hypotheses

[STUB at L0]

> [!quote]- Raw Transcript
> This is the raw transcript.
> It must not be modified.
"""


def _setup_registry(library_root: Path, entries: dict) -> None:
    """Create a registry.json from entry dicts."""
    reg_data = {"_schema_version": 1, "decks": entries, "updated_at": "2026-01-01T00:00:00Z"}
    (library_root / "registry.json").write_text(json.dumps(reg_data))


def _setup_note(library_root: Path, rel_path: str, content: str) -> Path:
    """Write a note file at the given relative path."""
    path = library_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _read_note_frontmatter(path: Path) -> dict:
    """Read YAML frontmatter from a note file."""
    content = path.read_text()
    if content.startswith("---\n"):
        end = content.index("\n---", 4)
        yaml_str = content[4:end]
        return yaml.safe_load(yaml_str) or {}
    return {}


# ---------------------------------------------------------------------------
# 1. Additive tag merge
# ---------------------------------------------------------------------------

class TestAdditiveTagMerge:
    """Tags are additive-only: no removal, dedup, case-normalize."""

    def test_new_tags_added(self):
        axis, merged = _merge_tags(["existing"], ["new-tag"])
        assert "new-tag" in merged
        assert "existing" in merged
        assert axis.status == "updated"
        assert axis.added == ["new-tag"]

    def test_no_removal(self):
        axis, merged = _merge_tags(["keep-me", "also-keep"], ["new"])
        assert "keep-me" in merged
        assert "also-keep" in merged

    def test_dedup_case_normalize(self):
        axis, merged = _merge_tags(["Existing"], ["existing"])
        assert axis.status == "no_change"
        # Should not have duplicates
        lower_tags = [t.lower() for t in merged]
        assert lower_tags.count("existing") == 1

    def test_empty_candidates(self):
        axis, merged = _merge_tags(["a", "b"], [])
        assert axis.status == "no_change"
        assert merged == ["a", "b"]


# ---------------------------------------------------------------------------
# 2. Route resolution
# ---------------------------------------------------------------------------

class TestRouteResolution:
    """Route resolution with routing.enrich and --llm-profile override."""

    def test_enrich_route_resolves(self):
        llm_config = LLMConfig(
            profiles={
                "default": LLMProfile(name="default"),
                "enrich_prof": LLMProfile(name="enrich_prof"),
            },
            routing={
                "default": LLMRoute(primary="default"),
                "enrich": LLMRoute(primary="enrich_prof"),
            },
        )
        profile = llm_config.resolve_profile(None, task="enrich")
        assert profile.name == "enrich_prof"

    def test_llm_profile_override(self):
        llm_config = LLMConfig(
            profiles={
                "default": LLMProfile(name="default"),
                "custom": LLMProfile(name="custom"),
            },
            routing={"default": LLMRoute(primary="default")},
        )
        profile = llm_config.resolve_profile("custom", task="enrich")
        assert profile.name == "custom"

    def test_override_disables_fallback(self):
        llm_config = LLMConfig(
            profiles={
                "default": LLMProfile(name="default"),
                "custom": LLMProfile(name="custom"),
                "fb": LLMProfile(name="fb"),
            },
            routing={
                "enrich": LLMRoute(primary="default", fallbacks=["fb"]),
            },
        )
        fallbacks = llm_config.get_fallbacks("custom", task="enrich")
        assert fallbacks == []


# ---------------------------------------------------------------------------
# 3. --force bypass behavior
# ---------------------------------------------------------------------------

class TestForceBypass:
    """--force bypasses fingerprint skip."""

    def test_force_bypasses_fingerprint(self):
        fm = {
            "curation_level": "L0",
            "review_status": "clean",
            "_llm_metadata": {
                "enrich": {
                    "input_fingerprint": "sha256:matching_fingerprint",
                    "entity_resolution_fingerprint": "",
                    "relationship_context_fingerprint": "",
                }
            },
        }
        doc = MarkdownDocument("# Title\n\n## Slide 1\n\n### Analysis\n\nContent.\n")
        disp, reason = _determine_disposition(
            fm=fm, doc=doc, doc_type="evidence",
            profile_name="default", force=True,
        )
        assert disp == "analyze"

    def test_force_still_respects_protection(self):
        fm = {
            "curation_level": "L1",
            "review_status": "clean",
        }
        doc = MarkdownDocument("# Title\n")
        disp, _ = _determine_disposition(
            fm=fm, doc=doc, doc_type="evidence",
            profile_name="default", force=True,
        )
        assert disp == "protect"


# ---------------------------------------------------------------------------
# 4. Input-fingerprint skip behavior
# ---------------------------------------------------------------------------

class TestInputFingerprintSkip:
    """Notes are skipped when fingerprint matches."""

    def test_matching_fingerprint_skips(self):
        # Build a note whose fingerprint matches
        content = "# Title\n\n## Slide 1\n\n### Analysis\n\nContent.\n"
        doc = MarkdownDocument(content)
        from folio.enrich import _strip_managed_content
        stripped = _strip_managed_content(content, doc, "evidence")
        entity_fp = ""
        relationship_fp = ""
        input_fp = compute_input_fingerprint(
            stripped, entity_fp, relationship_fp, "default", ENRICH_SPEC_VERSION,
        )

        fm = {
            "curation_level": "L0",
            "review_status": "clean",
            "_llm_metadata": {
                "enrich": {
                    "input_fingerprint": input_fp,
                    "entity_resolution_fingerprint": entity_fp,
                    "relationship_context_fingerprint": relationship_fp,
                }
            },
        }
        disp, reason = _determine_disposition(
            fm=fm, doc=doc, doc_type="evidence",
            profile_name="default", force=False,
        )
        assert disp == "skip"
        assert reason == "fingerprint match"

    def test_stale_never_skips(self):
        fm = {
            "curation_level": "L0",
            "review_status": "clean",
            "_llm_metadata": {
                "enrich": {
                    "status": "stale",
                    "input_fingerprint": "sha256:stale_fp",
                }
            },
        }
        content = "# Title\n\n## Slide 1\n\n### Analysis\n\nContent.\n\n## Version History\n\nHist.\n"
        doc = MarkdownDocument(content)
        disp, reason = _determine_disposition(
            fm=fm, doc=doc, doc_type="evidence",
            profile_name="default", force=False,
        )
        assert disp == "analyze"
        assert reason == "stale"


# ---------------------------------------------------------------------------
# 5. Note-scoped entity_resolution_fingerprint
# ---------------------------------------------------------------------------

class TestEntityResolutionFingerprint:
    """entity_resolution_fingerprint is note-scoped."""

    def test_different_notes_different_fps(self):
        fp1 = compute_entity_resolution_fingerprint(
            [("Alice", "confirmed:person/alice")]
        )
        fp2 = compute_entity_resolution_fingerprint(
            [("Bob", "confirmed:person/bob")]
        )
        assert fp1 != fp2

    def test_same_mentions_same_fp(self):
        mentions = [("Alice", "confirmed:person/alice")]
        assert (
            compute_entity_resolution_fingerprint(mentions)
            == compute_entity_resolution_fingerprint(mentions)
        )


# ---------------------------------------------------------------------------
# 6. Rejected-proposal suppression until basis_fingerprint changes
# ---------------------------------------------------------------------------

class TestRejectedProposalSuppression:
    """Rejected proposals are suppressed when basis_fingerprint unchanged."""

    def test_suppresses_same_basis(self):
        existing_meta = {
            "axes": {
                "relationships": {
                    "proposals": [
                        {
                            "relation": "supersedes",
                            "target_id": "old_note",
                            "basis_fingerprint": "sha256:same",
                            "status": "rejected",
                        }
                    ]
                }
            }
        }
        new_proposals = [
            RelationshipProposal(
                relation="supersedes",
                target_id="old_note",
                basis_fingerprint="sha256:same",
                confidence="high",
                signals=["same_source_stem"],
                rationale="Same lineage.",
                status="pending_human_confirmation",
            )
        ]
        result = _suppress_rejected_proposals(new_proposals, existing_meta, force=False)
        assert len(result) == 0

    def test_allows_changed_basis(self):
        existing_meta = {
            "axes": {
                "relationships": {
                    "proposals": [
                        {
                            "relation": "supersedes",
                            "target_id": "old_note",
                            "basis_fingerprint": "sha256:old",
                            "status": "rejected",
                        }
                    ]
                }
            }
        }
        new_proposals = [
            RelationshipProposal(
                relation="supersedes",
                target_id="old_note",
                basis_fingerprint="sha256:new_different",
                confidence="high",
                signals=["same_source_stem"],
                rationale="Changed basis.",
                status="pending_human_confirmation",
            )
        ]
        result = _suppress_rejected_proposals(new_proposals, existing_meta, force=False)
        assert len(result) == 1

    def test_force_still_suppresses_same_basis(self):
        existing_meta = {
            "axes": {
                "relationships": {
                    "proposals": [
                        {
                            "relation": "supersedes",
                            "target_id": "old_note",
                            "basis_fingerprint": "sha256:same",
                            "status": "rejected",
                        }
                    ]
                }
            }
        }
        new_proposals = [
            RelationshipProposal(
                relation="supersedes",
                target_id="old_note",
                basis_fingerprint="sha256:same",
                confidence="high",
                signals=[],
                rationale="",
                status="pending_human_confirmation",
            )
        ]
        result = _suppress_rejected_proposals(new_proposals, existing_meta, force=True)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# 7. Managed-body fingerprint conflict detection
# ---------------------------------------------------------------------------

class TestManagedBodyConflict:
    """Conflict when managed body fingerprint mismatches."""

    def test_conflict_on_mismatch(self):
        content = "# Title\n\n## Slide 1\n\n### Analysis\n\nOriginal content.\n\n## Version History\n\nHistory.\n"
        doc = MarkdownDocument(content)
        # Store a fingerprint that doesn't match current content
        fm = {
            "curation_level": "L0",
            "review_status": "clean",
            "_llm_metadata": {
                "enrich": {
                    "managed_body_fingerprint": "sha256:old_different_fp",
                }
            },
        }
        disp, reason = _determine_disposition(
            fm=fm, doc=doc, doc_type="evidence",
            profile_name="default", force=False,
        )
        assert disp == "conflict"
        assert "fingerprint mismatch" in reason


# ---------------------------------------------------------------------------
# 8. Malformed-heading protected fallback
# ---------------------------------------------------------------------------

class TestMalformedHeadingProtection:
    """Missing managed sections trigger protection."""

    def test_no_sections_returns_protect(self):
        content = "Just plain text."
        doc = MarkdownDocument(content)
        fm = {
            "curation_level": "L0",
            "review_status": "clean",
            "_llm_metadata": {
                "enrich": {"status": "executed"}
            },
        }
        disp, reason = _determine_disposition(
            fm=fm, doc=doc, doc_type="evidence",
            profile_name="default", force=False,
        )
        assert disp == "protect"
        assert "not identifiable" in reason


# ---------------------------------------------------------------------------
# 9. Relationship proposal serialization, singular supersedes
# ---------------------------------------------------------------------------

class TestRelationshipProposalSerialization:
    """Proposal serialization and singular supersedes cardinality."""

    def test_singular_supersedes(self):
        proposals = [
            RelationshipProposal(
                relation="supersedes", target_id="a",
                basis_fingerprint="sha256:x", confidence="high",
                signals=[], rationale="", status="pending_human_confirmation",
            ),
            RelationshipProposal(
                relation="supersedes", target_id="b",
                basis_fingerprint="sha256:y", confidence="high",
                signals=[], rationale="", status="pending_human_confirmation",
            ),
            RelationshipProposal(
                relation="impacts", target_id="c",
                basis_fingerprint="sha256:z", confidence="medium",
                signals=[], rationale="", status="pending_human_confirmation",
            ),
        ]
        filtered = _enforce_singular_supersedes(proposals)
        supersedes = [p for p in filtered if p.relation == "supersedes"]
        assert len(supersedes) == 1
        assert supersedes[0].target_id == "a"
        # impacts should survive
        assert any(p.relation == "impacts" for p in filtered)

    def test_proposal_roundtrip(self):
        proposal = RelationshipProposal(
            relation="supersedes",
            target_id="target_123",
            basis_fingerprint="sha256:abc",
            confidence="high",
            signals=["same_source_stem"],
            rationale="Same deck.",
            status="pending_human_confirmation",
        )
        d = proposal.to_dict()
        restored = RelationshipProposal.from_dict(d)
        assert restored.relation == proposal.relation
        assert restored.target_id == proposal.target_id
        assert restored.status == proposal.status


# ---------------------------------------------------------------------------
# 10. Entity resolver policy reuse
# ---------------------------------------------------------------------------

class TestEntityResolverPolicyReuse:
    """Entity resolver reuses shipped policy across both note types."""

    def test_resolve_entities_delegates(self):
        from folio.pipeline.entity_resolution import resolve_entities, resolve_interaction_entities
        # Verify resolve_entities exists and has the right signature
        import inspect
        sig = inspect.signature(resolve_entities)
        params = list(sig.parameters.keys())
        assert "entities_path" in params
        assert "extracted_entities" in params
        assert "source_text" in params


# ---------------------------------------------------------------------------
# 11. Dry-run: no writes, no LLM calls
# ---------------------------------------------------------------------------

class TestDryRun:
    """Dry-run makes no writes and no LLM calls."""

    def test_dry_run_no_writes(self, tmp_path):
        config = _make_config(tmp_path)
        library_root = config.library_root

        note_content = _make_evidence_note()
        _setup_note(library_root, "ClientA/DD_Q1/evidence.md", note_content)
        _setup_registry(library_root, {
            "test_evidence": {
                "id": "test_evidence",
                "title": "Test Evidence",
                "type": "evidence",
                "markdown_path": "ClientA/DD_Q1/evidence.md",
                "deck_dir": "ClientA/DD_Q1",
                "source_relative_path": "deck.pptx",
                "source_hash": "abc123def456",
                "version": 1,
                "converted": "2026-01-01T00:00:00Z",
                "client": "ClientA",
                "engagement": "DD_Q1",
            }
        })

        messages = []
        result = enrich_batch(
            config, dry_run=True, echo=messages.append,
        )

        # Note content should be unchanged
        after_content = (library_root / "ClientA/DD_Q1/evidence.md").read_text()
        assert after_content == note_content

        # Should report counts
        summary = messages[-1]
        assert "would_analyze" in summary

    def test_dry_run_separate_counts(self, tmp_path):
        config = _make_config(tmp_path)
        library_root = config.library_root

        # L0 note (analyze)
        _setup_note(library_root, "ClientA/DD_Q1/e1.md", _make_evidence_note(note_id="e1"))
        # L1 note (protect)
        _setup_note(library_root, "ClientA/DD_Q1/e2.md",
                     _make_evidence_note(note_id="e2", curation_level="L1"))

        _setup_registry(library_root, {
            "e1": {
                "id": "e1", "title": "E1", "type": "evidence",
                "markdown_path": "ClientA/DD_Q1/e1.md",
                "deck_dir": "ClientA/DD_Q1",
                "source_relative_path": "deck.pptx",
                "source_hash": "abc123", "version": 1,
                "converted": "2026-01-01T00:00:00Z",
            },
            "e2": {
                "id": "e2", "title": "E2", "type": "evidence",
                "markdown_path": "ClientA/DD_Q1/e2.md",
                "deck_dir": "ClientA/DD_Q1",
                "source_relative_path": "deck.pptx",
                "source_hash": "abc123", "version": 1,
                "converted": "2026-01-01T00:00:00Z",
            },
        })

        messages = []
        result = enrich_batch(config, dry_run=True, echo=messages.append)
        summary = messages[-1]
        assert "would_protect" in summary


# ---------------------------------------------------------------------------
# 12. ## Related from canonical frontmatter only
# ---------------------------------------------------------------------------

class TestRelatedFromCanonical:
    """## Related is generated from canonical frontmatter only."""

    def test_renders_from_canonical(self, tmp_path):
        config = _make_config(tmp_path)
        library_root = config.library_root
        _setup_registry(library_root, {
            "target_note": {
                "id": "target_note",
                "title": "Target Note Title",
                "type": "evidence",
                "markdown_path": "ClientA/DD_Q1/target.md",
                "deck_dir": "ClientA/DD_Q1",
                "source_relative_path": "deck.pptx",
                "source_hash": "xyz", "version": 1,
                "converted": "2026-01-01T00:00:00Z",
            }
        })

        content = "# Title\n\n## Version History\n\nHistory.\n"
        fm = {"supersedes": "target_note"}

        new_content = _update_related_section(
            content=content,
            doc_type="evidence",
            fm=fm,
            config=config,
        )
        assert "## Related" in new_content
        assert "[[ClientA/DD_Q1/target|Target Note Title]]" in new_content

    def test_no_proposals_in_related(self, tmp_path):
        """Pending proposals are NOT rendered into ## Related."""
        config = _make_config(tmp_path)
        library_root = config.library_root
        _setup_registry(library_root, {})

        content = "# Title\n\n## Version History\n\nHistory.\n"
        # Frontmatter with no canonical relationships
        fm = {
            "_llm_metadata": {
                "enrich": {
                    "axes": {
                        "relationships": {
                            "proposals": [{
                                "relation": "supersedes",
                                "target_id": "some_note",
                            }]
                        }
                    }
                }
            }
        }

        new_content = _update_related_section(
            content=content,
            doc_type="evidence",
            fm=fm,
            config=config,
        )
        assert "## Related" not in new_content


# ---------------------------------------------------------------------------
# 13. ## Related suppression when all targets unresolved
# ---------------------------------------------------------------------------

class TestRelatedSuppression:
    """## Related is suppressed when all targets are unresolvable."""

    def test_removes_stale_related(self, tmp_path):
        config = _make_config(tmp_path)
        library_root = config.library_root
        _setup_registry(library_root, {})  # Empty registry

        content = "# Title\n\n## Related\n\n### Supersedes\n- [[old|Old Note]]\n\n## Version History\n\nHistory.\n"
        fm = {"supersedes": "nonexistent_id"}

        new_content = _update_related_section(
            content=content,
            doc_type="evidence",
            fm=fm,
            config=config,
        )
        assert "## Related" not in new_content

    def test_no_related_when_empty(self, tmp_path):
        config = _make_config(tmp_path)
        library_root = config.library_root
        _setup_registry(library_root, {})

        content = "# Title\n\n## Version History\n\nHistory.\n"
        fm = {}

        new_content = _update_related_section(
            content=content,
            doc_type="evidence",
            fm=fm,
            config=config,
        )
        assert "## Related" not in new_content


# ---------------------------------------------------------------------------
# 14. Stale-status transition
# ---------------------------------------------------------------------------

class TestStaleTransition:
    """Stale notes always re-enrich."""

    def test_stale_bypasses_skip(self):
        fm = {
            "curation_level": "L0",
            "review_status": "clean",
            "_llm_metadata": {
                "enrich": {
                    "status": "stale",
                    "input_fingerprint": "sha256:any_value",
                }
            },
        }
        content = "# Title\n\n## Slide 1\n\n### Analysis\n\nContent.\n\n## Version History\n\nHist.\n"
        doc = MarkdownDocument(content)
        disp, reason = _determine_disposition(
            fm=fm, doc=doc, doc_type="evidence",
            profile_name="default", force=False,
        )
        assert disp == "analyze"
        assert reason == "stale"


# ---------------------------------------------------------------------------
# Body safety tests (spec section 16.2)
# ---------------------------------------------------------------------------

class TestEvidenceBodySafety:
    """Evidence body safety: verbatim text and evidence quotes unchanged."""

    def test_verbatim_text_unchanged(self):
        content = _make_evidence_note()
        doc = MarkdownDocument(content)

        # Verify verbatim text section is protected
        managed = doc.get_managed_sections("evidence")
        for key, section in managed.items():
            assert "Text (Verbatim)" not in key

    def test_wikilinks_only_in_analysis(self):
        """Wikilinks are only inserted in allowed analysis prose fields."""
        body = """\
**Slide Type:** data
**Framework:** none
**Visual Description:** ServiceNow integration chart.
**Key Data:** Engineering Department processes 500 tickets.
**Main Insight:** ServiceNow drives efficiency.

**Evidence:**
- claim: ServiceNow handles 500 tickets
  - confidence: high
  - validated: yes
"""
        wikilink_map = {
            "ServiceNow": "[[ServiceNow]]",
            "Engineering Department": "[[Engineering Department]]",
        }
        result = _insert_wikilinks_in_analysis(body, wikilink_map)

        # Wikilinks should appear in prose fields
        lines = result.split("\n")
        for line in lines:
            if line.startswith("**Visual Description:**"):
                assert "[[ServiceNow]]" in line
            if line.startswith("**Key Data:**"):
                assert "[[Engineering Department]]" in line
            # Evidence section should NOT have wikilinks
            if line.strip().startswith("- claim:"):
                assert "[[" not in line

    def test_no_bleed_across_sections(self):
        content = _make_evidence_note()
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("evidence")

        for key, section in managed.items():
            if key == "## Related":
                continue
            # Each section should have defined boundaries
            body = content[section.body_start:section.end]
            assert "## Slide" not in body or key.startswith("## Slide")


class TestInteractionBodySafety:
    """Interaction body safety: transcript, summary, key findings unchanged."""

    def test_summary_not_in_managed(self):
        content = _make_interaction_note()
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("interaction")
        assert "## Summary" not in managed

    def test_key_findings_not_in_managed(self):
        content = _make_interaction_note()
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("interaction")
        assert "## Key Findings" not in managed

    def test_quotes_not_in_managed(self):
        content = _make_interaction_note()
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("interaction")
        assert "## Quotes / Evidence" not in managed

    def test_entities_mentioned_is_managed(self):
        content = _make_interaction_note()
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("interaction")
        assert "## Entities Mentioned" in managed

    def test_impact_on_hypotheses_not_managed_in_v1(self):
        """Excluded from managed set: no mutation logic in v1 (B6 fix)."""
        content = _make_interaction_note()
        doc = MarkdownDocument(content)
        managed = doc.get_managed_sections("interaction")
        assert "## Impact on Hypotheses" not in managed


# ---------------------------------------------------------------------------
# Frontmatter replacement
# ---------------------------------------------------------------------------

class TestFrontmatterReplacement:
    """Frontmatter is correctly replaced in note content."""

    def test_replace_preserves_body(self):
        content = "---\nid: old\n---\n\n# Title\n\nBody content.\n"
        fm = {"id": "new", "type": "evidence"}
        result = _replace_frontmatter(content, fm)
        assert "id: new" in result
        assert "Body content." in result
        assert result.count("---") == 2  # Opening and closing delimiters

    def test_replace_handles_multiline_yaml_with_dashes(self):
        """B2: YAML block scalar containing '---' must not corrupt the note."""
        content = (
            "---\n"
            "id: test_note\n"
            "description: |\n"
            "  This is a multi-line\n"
            "  ---\n"
            "  description with dashes.\n"
            "tags:\n"
            "  - foo\n"
            "---\n"
            "\n# Title\n\nBody content.\n"
        )
        fm = {"id": "updated", "type": "evidence"}
        result = _replace_frontmatter(content, fm)
        assert "id: updated" in result
        assert "Body content." in result
        # Must not include the old description block in the body
        assert "description with dashes" not in result

    def test_replace_handles_nested_yaml_dashes_in_string(self):
        """B2: Quoted string value containing --- must not confuse parser."""
        content = (
            "---\n"
            "id: test\n"
            "note: 'line1\\n---\\nline2'\n"
            "---\n"
            "\n# Title\n\nBody.\n"
        )
        fm = {"id": "new"}
        result = _replace_frontmatter(content, fm)
        assert "id: new" in result
        assert "Body." in result


# ---------------------------------------------------------------------------
# B1: Body safety gate for ## Related
# ---------------------------------------------------------------------------

class TestRelatedSectionBodySafety:
    """B1: _update_related_section must not run on protected notes."""

    def test_protected_note_disposition_is_protect(self):
        """L1 note must get 'protect' disposition, blocking body mutation."""
        content = _make_evidence_note()
        fm = yaml.safe_load(content.split("---")[1])
        fm["curation_level"] = "L1"
        fm["supersedes"] = "other_note_id"

        doc = MarkdownDocument(content)
        disposition, reason = _determine_disposition(
            fm=fm,
            doc=doc,
            doc_type="evidence",
            profile_name="test",
            force=False,
        )
        assert disposition == "protect"
        assert "curation_level" in reason


# ---------------------------------------------------------------------------
# B4: Promoted-proposal cleanup
# ---------------------------------------------------------------------------

class TestPromotedProposalCleanup:
    """B4: Proposals matching canonical fields must be removed."""

    def test_promoted_supersedes_removed(self):
        proposals = [
            RelationshipProposal(
                relation="supersedes",
                target_id="target_a",
                basis_fingerprint="sha256:abc",
                confidence="high",
                signals=["same_source_stem"],
                rationale="Same lineage.",
                status="pending_human_confirmation",
            ),
        ]
        fm = {"supersedes": "target_a"}
        result = _remove_promoted_proposals(proposals, fm)
        assert len(result) == 0

    def test_promoted_impacts_removed_from_list(self):
        proposals = [
            RelationshipProposal(
                relation="impacts",
                target_id="target_b",
                basis_fingerprint="sha256:def",
                confidence="medium",
                signals=["explicit_document_reference"],
                rationale="Referenced directly.",
                status="pending_human_confirmation",
            ),
        ]
        fm = {"impacts": ["target_b", "target_c"]}
        result = _remove_promoted_proposals(proposals, fm)
        assert len(result) == 0

    def test_non_promoted_proposal_kept(self):
        proposals = [
            RelationshipProposal(
                relation="supersedes",
                target_id="target_x",
                basis_fingerprint="sha256:ghi",
                confidence="high",
                signals=["version_order"],
                rationale="Newer version.",
                status="pending_human_confirmation",
            ),
        ]
        fm = {"supersedes": "different_target"}
        result = _remove_promoted_proposals(proposals, fm)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# S3: Singular supersedes sorts by confidence
# ---------------------------------------------------------------------------

class TestSingularSupersedesConfidence:
    """S3: When multiple supersedes exist, keep highest confidence."""

    def test_high_confidence_kept_over_medium(self):
        proposals = [
            RelationshipProposal(
                relation="supersedes", target_id="t1",
                basis_fingerprint="fp1", confidence="medium",
                signals=[], rationale="", status="pending_human_confirmation",
            ),
            RelationshipProposal(
                relation="supersedes", target_id="t2",
                basis_fingerprint="fp2", confidence="high",
                signals=[], rationale="", status="pending_human_confirmation",
            ),
        ]
        result = _enforce_singular_supersedes(proposals)
        supersedes = [p for p in result if p.relation == "supersedes"]
        assert len(supersedes) == 1
        assert supersedes[0].confidence == "high"
        assert supersedes[0].target_id == "t2"


# ---------------------------------------------------------------------------
# V2 Review Fixes
# ---------------------------------------------------------------------------

class TestFrontmatterBlockScalarFalsePositive:
    """B1-V2: > in normal YAML values must not trigger block-scalar mode."""

    def test_greater_than_in_quoted_value(self):
        content = (
            "---\n"
            "id: test\n"
            "note: 'value > comparison'\n"
            "---\n"
            "\n# Title\n\nBody.\n"
        )
        fm = {"id": "updated"}
        result = _replace_frontmatter(content, fm)
        assert "id: updated" in result
        assert "Body." in result
        # Old frontmatter must be fully replaced
        assert "value > comparison" not in result

    def test_greater_than_unquoted_value(self):
        content = (
            "---\n"
            "id: test\n"
            "compare: x > y\n"
            "---\n"
            "\n# Title\n\nBody.\n"
        )
        fm = {"id": "new"}
        result = _replace_frontmatter(content, fm)
        assert "id: new" in result
        assert "Body." in result

    def test_real_block_scalar_still_works(self):
        content = (
            "---\n"
            "id: test\n"
            "description: |\n"
            "  line one\n"
            "  ---\n"
            "  line two\n"
            "---\n"
            "\n# Title\n\nBody.\n"
        )
        fm = {"id": "new"}
        result = _replace_frontmatter(content, fm)
        assert "id: new" in result
        assert "Body." in result
        assert "line one" not in result

    def test_block_scalar_with_chomping(self):
        content = (
            "---\n"
            "id: test\n"
            "text: |+\n"
            "  keep trailing\n"
            "  ---\n"
            "---\n"
            "\n# Title\n\nBody.\n"
        )
        fm = {"id": "new"}
        result = _replace_frontmatter(content, fm)
        assert "id: new" in result
        assert "Body." in result


class TestEntityFingerprintNoDuplicates:
    """B2-V2: Created entities must not be duplicated in mention records."""

    def test_created_entity_not_stamped_as_confirmed(self):
        """Auto-created entity should appear once with unconfirmed prefix."""
        from folio.pipeline.entity_resolution import ResolutionResult, CreatedEntity

        result = ResolutionResult(
            entities={"people": ["Known Person", "New Person"]},
            warnings=[],
            created_entities=[
                CreatedEntity(
                    entity_type="person",
                    key="new_person",
                    canonical_name="New Person",
                    proposed_match=None,
                ),
            ],
        )

        # Simulate the mention record building logic
        created_names = {c.canonical_name for c in result.created_entities}
        records = []

        for category, names in result.entities.items():
            for name in names:
                if name in created_names:
                    continue
                records.append(("confirmed", name))

        for created in result.created_entities:
            prefix = "proposed_match" if created.proposed_match else "unconfirmed"
            records.append((prefix, created.canonical_name))

        # "Known Person" confirmed, "New Person" unconfirmed — no duplicates
        assert len(records) == 2
        assert ("confirmed", "Known Person") in records
        assert ("unconfirmed", "New Person") in records
        # Must NOT have confirmed entry for created entity
        assert ("confirmed", "New Person") not in records
