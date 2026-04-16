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
    compute_relationship_proposal_id,
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
            lifecycle_state="queued",
        )
        d = proposal.to_dict()
        assert d["proposal_id"] == ""
        assert d["relation"] == "supersedes"
        assert d["target_id"] == "client_evidence_20260301_market-sizing"
        assert d["producer"] == "enrich"
        assert d["basis_fingerprint"] == "sha256:abc123"
        assert d["confidence"] == "high"
        assert d["signals"] == ["same_source_stem", "version_order"]
        assert d["rationale"] == "Same deck lineage and newer converted note."
        assert d["lifecycle_state"] == "queued"

    def test_from_dict_roundtrip(self):
        original = RelationshipProposal(
            relation="impacts",
            target_id="target_id_123",
            basis_fingerprint="sha256:def456",
            confidence="medium",
            signals=["explicit_document_reference"],
            rationale="Direct reference to target.",
            lifecycle_state="rejected",
        )
        restored = RelationshipProposal.from_dict(original.to_dict())
        assert restored.relation == original.relation
        assert restored.target_id == original.target_id
        assert restored.confidence == original.confidence
        assert restored.lifecycle_state == original.lifecycle_state

    def test_to_dict_no_extra_fields(self):
        proposal = RelationshipProposal(
            relation="supersedes",
            target_id="t",
            basis_fingerprint="sha256:x",
            confidence="high",
            signals=[],
            rationale="",
            lifecycle_state="queued",
        )
        d = proposal.to_dict()
        expected_keys = {
            "proposal_id", "relation", "target_id", "producer",
            "basis_fingerprint", "confidence", "signals",
            "rationale", "lifecycle_state",
        }
        assert set(d.keys()) == expected_keys

    def test_from_dict_backfills_deterministic_proposal_id(self):
        restored = RelationshipProposal.from_dict(
            {
                "source_id": "client_note_01",
                "relation": "supersedes",
                "target_id": "client_note_00",
                "basis_fingerprint": "sha256:abc123",
                "confidence": "high",
                "signals": [],
                "rationale": "",
                "lifecycle_state": "queued",
            }
        )
        assert restored.proposal_id == compute_relationship_proposal_id(
            source_id="client_note_01",
            relation="supersedes",
            target_id="client_note_00",
            basis_fingerprint="sha256:abc123",
        )

    def test_from_dict_reads_legacy_status_pending(self):
        p = RelationshipProposal.from_dict(
            {"relation": "impacts", "target_id": "x", "status": "pending_human_confirmation"}
        )
        assert p.lifecycle_state == "queued"

    def test_from_dict_reads_legacy_status_rejected(self):
        p = RelationshipProposal.from_dict(
            {"relation": "impacts", "target_id": "x", "status": "rejected"}
        )
        assert p.lifecycle_state == "rejected"

    def test_from_dict_prefers_lifecycle_state_over_status(self):
        p = RelationshipProposal.from_dict(
            {"relation": "impacts", "target_id": "x", "lifecycle_state": "suppressed", "status": "rejected"}
        )
        assert p.lifecycle_state == "suppressed"

    def test_from_dict_lifecycle_state_null_falls_to_status(self):
        p = RelationshipProposal.from_dict(
            {"relation": "impacts", "target_id": "x", "lifecycle_state": None, "status": "rejected"}
        )
        assert p.lifecycle_state == "rejected"

    def test_to_dict_emits_lifecycle_state_not_status(self):
        p = RelationshipProposal(
            relation="impacts", target_id="x", basis_fingerprint="",
            confidence="medium", signals=[], rationale="",
        )
        d = p.to_dict()
        assert "lifecycle_state" in d
        assert "status" not in d

    def test_proposal_lifecycle_states_constant(self):
        from folio.pipeline.enrich_data import PROPOSAL_LIFECYCLE_STATES
        assert len(PROPOSAL_LIFECYCLE_STATES) == 6
        assert PROPOSAL_LIFECYCLE_STATES == frozenset({
            "queued", "accepted", "rejected", "suppressed", "stale", "superseded",
        })

    def test_from_dict_neither_key_defaults_to_queued(self):
        p = RelationshipProposal.from_dict({"relation": "impacts", "target_id": "x"})
        assert p.lifecycle_state == "queued"

    def test_enrich_emission_time_rejection_filter_reads_legacy_status(self):
        """T-6: rejection filter at enrich.py emission time handles legacy status."""
        from folio.enrich import _suppress_rejected_proposals
        legacy_rejected = {
            "relation": "impacts",
            "target_id": "t1",
            "basis_fingerprint": "sha256:abc",
            "status": "rejected",
        }
        existing_meta = {"axes": {"relationships": {"proposals": [legacy_rejected]}}}
        new = RelationshipProposal(
            relation="impacts", target_id="t1", basis_fingerprint="sha256:abc",
            confidence="medium", signals=[], rationale="",
        )
        result, count = _suppress_rejected_proposals([new], existing_meta, force=False)
        assert len(result) == 1
        assert result[0].lifecycle_state == "suppressed"
        assert count == 1

    def test_graph_acceptance_rate_reads_legacy_rejected_status(self):
        """T-8: graph acceptance-rate aggregation counts legacy status: rejected."""
        raw = {"status": "rejected"}
        state = raw.get("lifecycle_state")
        if state is None:
            state = raw.get("status")
        assert state == "rejected"


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
