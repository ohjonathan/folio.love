"""Tests for enrich data model and fingerprint functions."""

import pytest

from folio.pipeline.enrich_data import (
    ENRICH_SPEC_VERSION,
    RELATIONSHIP_FIELDS,
    EnrichOutcome,
    RelationshipProposal,
    EnrichAxisResult,
    EnrichResult,
    compute_input_fingerprint,
    compute_entity_resolution_fingerprint,
    compute_relationship_context_fingerprint,
    compute_managed_body_fingerprint,
)


# ---------------------------------------------------------------------------
# Fingerprint determinism
# ---------------------------------------------------------------------------

class TestFingerprintDeterminism:
    """All fingerprint functions produce deterministic output."""

    def test_input_fingerprint_deterministic(self):
        fp1 = compute_input_fingerprint("content", "efp", "rfp", "profile", 2)
        fp2 = compute_input_fingerprint("content", "efp", "rfp", "profile", 2)
        assert fp1 == fp2
        assert fp1.startswith("sha256:")

    def test_entity_resolution_fingerprint_deterministic(self):
        mentions = [("Alice", "confirmed:person/alice"), ("Bob", "unresolved")]
        fp1 = compute_entity_resolution_fingerprint(mentions)
        fp2 = compute_entity_resolution_fingerprint(mentions)
        assert fp1 == fp2
        assert fp1.startswith("sha256:")

    def test_relationship_context_fingerprint_deterministic(self):
        fp1 = compute_relationship_context_fingerprint(["target_a"], ["target_b"])
        fp2 = compute_relationship_context_fingerprint(["target_a"], ["target_b"])
        assert fp1 == fp2
        assert fp1.startswith("sha256:")

    def test_managed_body_fingerprint_deterministic(self):
        contents = {"## Entities Mentioned": "body1", "## Impact": "body2"}
        fp1 = compute_managed_body_fingerprint(contents)
        fp2 = compute_managed_body_fingerprint(contents)
        assert fp1 == fp2
        assert fp1.startswith("sha256:")


# ---------------------------------------------------------------------------
# Input fingerprint sensitivity
# ---------------------------------------------------------------------------

class TestInputFingerprint:
    """Input fingerprint changes when any component changes."""

    def test_changes_when_entity_fp_changes(self):
        fp1 = compute_input_fingerprint("content", "efp_v1", "rfp", "profile", 2)
        fp2 = compute_input_fingerprint("content", "efp_v2", "rfp", "profile", 2)
        assert fp1 != fp2

    def test_changes_when_profile_name_changes(self):
        fp1 = compute_input_fingerprint("content", "efp", "rfp", "profile_a", 2)
        fp2 = compute_input_fingerprint("content", "efp", "rfp", "profile_b", 2)
        assert fp1 != fp2

    def test_changes_when_spec_version_changes(self):
        fp1 = compute_input_fingerprint("content", "efp", "rfp", "profile", 1)
        fp2 = compute_input_fingerprint("content", "efp", "rfp", "profile", 2)
        assert fp1 != fp2

    def test_changes_when_content_changes(self):
        fp1 = compute_input_fingerprint("content_v1", "efp", "rfp", "profile", 2)
        fp2 = compute_input_fingerprint("content_v2", "efp", "rfp", "profile", 2)
        assert fp1 != fp2

    def test_changes_when_relationship_fp_changes(self):
        fp1 = compute_input_fingerprint("content", "efp", "rfp_v1", "profile", 2)
        fp2 = compute_input_fingerprint("content", "efp", "rfp_v2", "profile", 2)
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# Managed body fingerprint
# ---------------------------------------------------------------------------

class TestManagedBodyFingerprint:
    """Managed body fingerprint detects content changes."""

    def test_detects_content_change(self):
        fp1 = compute_managed_body_fingerprint({"## Section": "original"})
        fp2 = compute_managed_body_fingerprint({"## Section": "modified"})
        assert fp1 != fp2

    def test_detects_new_section(self):
        fp1 = compute_managed_body_fingerprint({"## A": "content"})
        fp2 = compute_managed_body_fingerprint({"## A": "content", "## B": "new"})
        assert fp1 != fp2

    def test_order_independent(self):
        fp1 = compute_managed_body_fingerprint({"## B": "b", "## A": "a"})
        fp2 = compute_managed_body_fingerprint({"## A": "a", "## B": "b"})
        assert fp1 == fp2


# ---------------------------------------------------------------------------
# Entity resolution fingerprint
# ---------------------------------------------------------------------------

class TestEntityResolutionFingerprint:
    """Entity resolution fingerprint behavior."""

    def test_changes_when_resolution_changes(self):
        fp1 = compute_entity_resolution_fingerprint(
            [("Alice", "unresolved")]
        )
        fp2 = compute_entity_resolution_fingerprint(
            [("Alice", "confirmed:person/alice")]
        )
        assert fp1 != fp2

    def test_note_scoped_same_mentions_same_fp(self):
        mentions = [("Alice", "confirmed:person/alice"), ("Bob", "unresolved")]
        fp1 = compute_entity_resolution_fingerprint(mentions)
        fp2 = compute_entity_resolution_fingerprint(mentions)
        assert fp1 == fp2

    def test_order_independent(self):
        fp1 = compute_entity_resolution_fingerprint(
            [("Bob", "unresolved"), ("Alice", "confirmed:person/alice")]
        )
        fp2 = compute_entity_resolution_fingerprint(
            [("Alice", "confirmed:person/alice"), ("Bob", "unresolved")]
        )
        assert fp1 == fp2


# ---------------------------------------------------------------------------
# Relationship context fingerprint
# ---------------------------------------------------------------------------

class TestRelationshipContextFingerprint:
    """Relationship context fingerprint is note-scoped."""

    def test_note_scoped_based_on_targets(self):
        fp1 = compute_relationship_context_fingerprint(
            canonical_targets=["target_a"],
            proposal_targets=["target_b"],
        )
        fp2 = compute_relationship_context_fingerprint(
            canonical_targets=["target_a"],
            proposal_targets=["target_b"],
        )
        assert fp1 == fp2

    def test_changes_when_canonical_targets_change(self):
        fp1 = compute_relationship_context_fingerprint(["a"], ["b"])
        fp2 = compute_relationship_context_fingerprint(["a", "c"], ["b"])
        assert fp1 != fp2

    def test_changes_when_proposal_targets_change(self):
        fp1 = compute_relationship_context_fingerprint(["a"], ["b"])
        fp2 = compute_relationship_context_fingerprint(["a"], ["b", "c"])
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# RelationshipProposal serialization
# ---------------------------------------------------------------------------

class TestRelationshipProposal:
    """RelationshipProposal serialization matches spec section 9.3."""

    def test_to_dict_has_all_fields(self):
        proposal = RelationshipProposal(
            relation="supersedes",
            target_id="client_evidence_20260301_market-sizing",
            basis_fingerprint="sha256:abc123",
            confidence="high",
            signals=["same_source_stem", "version_order"],
            rationale="Same deck lineage and newer converted note.",
            status="pending_human_confirmation",
        )
        d = proposal.to_dict()
        assert d["relation"] == "supersedes"
        assert d["target_id"] == "client_evidence_20260301_market-sizing"
        assert d["basis_fingerprint"] == "sha256:abc123"
        assert d["confidence"] == "high"
        assert d["signals"] == ["same_source_stem", "version_order"]
        assert d["rationale"] == "Same deck lineage and newer converted note."
        assert d["status"] == "pending_human_confirmation"

    def test_from_dict_roundtrip(self):
        original = RelationshipProposal(
            relation="impacts",
            target_id="target_id_123",
            basis_fingerprint="sha256:def456",
            confidence="medium",
            signals=["explicit_document_reference"],
            rationale="Direct reference to target.",
            status="rejected",
        )
        restored = RelationshipProposal.from_dict(original.to_dict())
        assert restored.relation == original.relation
        assert restored.target_id == original.target_id
        assert restored.confidence == original.confidence
        assert restored.status == original.status

    def test_to_dict_no_extra_fields(self):
        proposal = RelationshipProposal(
            relation="supersedes",
            target_id="t",
            basis_fingerprint="sha256:x",
            confidence="high",
            signals=[],
            rationale="",
            status="pending_human_confirmation",
        )
        d = proposal.to_dict()
        expected_keys = {
            "relation", "target_id", "basis_fingerprint",
            "confidence", "signals", "rationale", "status",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# EnrichAxisResult serialization
# ---------------------------------------------------------------------------

class TestEnrichAxisResult:
    """EnrichAxisResult serialization omits None fields."""

    def test_tag_axis(self):
        result = EnrichAxisResult(status="updated", added=["new-tag"])
        d = result.to_dict()
        assert d == {"status": "updated", "added": ["new-tag"]}

    def test_entity_axis(self):
        result = EnrichAxisResult(
            status="updated",
            mentions=[{"text": "Alice", "type": "person"}],
            resolved=["Alice"],
            unresolved_created=["Bob"],
        )
        d = result.to_dict()
        assert "mentions" in d
        assert "resolved" in d
        assert "unresolved_created" in d

    def test_skipped_axis_minimal(self):
        result = EnrichAxisResult(status="skipped")
        d = result.to_dict()
        assert d == {"status": "skipped"}


# ---------------------------------------------------------------------------
# EnrichOutcome enum
# ---------------------------------------------------------------------------

class TestEnrichOutcome:
    """EnrichOutcome values."""

    def test_all_values(self):
        assert EnrichOutcome.updated == "updated"
        assert EnrichOutcome.unchanged == "unchanged"
        assert EnrichOutcome.protected == "protected"
        assert EnrichOutcome.conflicted == "conflicted"
        assert EnrichOutcome.failed == "failed"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Module constants are correct."""

    def test_spec_version(self):
        assert ENRICH_SPEC_VERSION == 2

    def test_relationship_fields(self):
        assert "depends_on" in RELATIONSHIP_FIELDS
        assert "draws_from" in RELATIONSHIP_FIELDS
        assert "impacts" in RELATIONSHIP_FIELDS
        assert "relates_to" in RELATIONSHIP_FIELDS
        assert "supersedes" in RELATIONSHIP_FIELDS
        assert "instantiates" in RELATIONSHIP_FIELDS
        assert len(RELATIONSHIP_FIELDS) == 6
