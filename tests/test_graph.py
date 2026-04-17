"""Unit tests for folio.graph helpers and graph_doctor contract shape (v0.7.1).

Covers §5 shared-proposal-contract retrofit per
docs/specs/v0.7.1_folio_graph_generalized_proposals_spec.md.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from folio.graph import (
    _SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS,
    _SUPPORTED_RELATIONS,
    _compute_relationship_schema_gate,
    _derive_recommended_action,
    _derive_trust_status,
)
from folio.pipeline.enrich_data import PROPOSAL_LIFECYCLE_STATES, RelationshipProposal


def _make_proposal(
    *,
    relation: str = "draws_from",
    target_id: str = "target_doc",
    basis_fingerprint: str = "sha256:abc",
    rationale: str = "Both docs reference the shared framework.",
    signals: list[str] | None = None,
    lifecycle_state: str = "queued",
    producer: str = "enrich",
    proposal_id: str = "rprop-deadbeef",
) -> RelationshipProposal:
    return RelationshipProposal(
        relation=relation,
        target_id=target_id,
        basis_fingerprint=basis_fingerprint,
        confidence="medium",
        signals=list(signals or ["shared-term: framework"]),
        rationale=rationale,
        lifecycle_state=lifecycle_state,
        proposal_id=proposal_id,
        producer=producer,
    )


def _make_view(
    *,
    source_id: str = "source_doc",
    flagged_inputs: list[str] | None = None,
    proposal: RelationshipProposal | None = None,
    producer: str | None = None,
):
    prop = proposal or _make_proposal()
    return SimpleNamespace(
        source_id=source_id,
        source_path=Path("/tmp/source.md"),
        source_markdown_path="source.md",
        producer=producer or prop.producer,
        proposal=prop,
        revived=False,
        flagged_inputs=list(flagged_inputs or []),
    )


class TestSharedProposalContractEmittedKeys:
    def test_has_eleven_keys(self):
        assert len(_SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS) == 11

    def test_keys_match_spec(self):
        expected = {
            "proposal_type",
            "source_id",
            "target_id",
            "subject_id",
            "evidence_bundle",
            "reason_summary",
            "trust_status",
            "schema_gate_result",
            "producer",
            "input_fingerprint",
            "lifecycle_state",
        }
        assert set(_SHARED_PROPOSAL_CONTRACT_EMITTED_KEYS) == expected


class TestDeriveTrustStatus:
    def test_empty_list_is_ok(self):
        view = _make_view(flagged_inputs=[])
        assert _derive_trust_status(view) == "ok"

    def test_none_input_is_ok(self):
        view = SimpleNamespace(flagged_inputs=None)
        assert _derive_trust_status(view) == "ok"

    def test_source_flagged_is_flagged(self):
        view = _make_view(flagged_inputs=["source"])
        assert _derive_trust_status(view) == "flagged"

    def test_target_flagged_is_flagged(self):
        view = _make_view(flagged_inputs=["target"])
        assert _derive_trust_status(view) == "flagged"

    def test_both_flagged_is_flagged(self):
        view = _make_view(flagged_inputs=["source", "target"])
        assert _derive_trust_status(view) == "flagged"

    def test_unexpected_value_is_ok(self):
        # ADV-SF5 edge case: unexpected list contents don't match
        # {"source","target"}; result is "ok", not "flagged".
        view = _make_view(flagged_inputs=["both"])
        assert _derive_trust_status(view) == "ok"


class TestComputeRelationshipSchemaGate:
    def test_valid_target_and_relation_returns_none(self):
        view = _make_view(
            proposal=_make_proposal(relation="draws_from", target_id="doc_a"),
        )
        assert _compute_relationship_schema_gate(view, {"source_doc", "doc_a"}) is None

    def test_missing_target_fails_target_registered(self):
        view = _make_view(
            proposal=_make_proposal(relation="draws_from", target_id="doc_missing"),
        )
        gate = _compute_relationship_schema_gate(view, {"source_doc"})
        # Key-subset assertion per B2 additive-extension contract.
        assert gate is not None
        assert gate["status"] == "fail"
        assert gate["rule"] == "target_registered"

    def test_unsupported_relation_fails_supported_relation(self):
        view = _make_view(
            proposal=_make_proposal(relation="weird_relation", target_id="doc_a"),
        )
        gate = _compute_relationship_schema_gate(view, {"source_doc", "doc_a"})
        assert gate is not None
        assert gate["status"] == "fail"
        assert gate["rule"] == "supported_relation"

    def test_target_missing_short_circuits_before_relation_check(self):
        # Even with an unsupported relation, missing target fires first.
        view = _make_view(
            proposal=_make_proposal(relation="weird_relation", target_id="doc_missing"),
        )
        gate = _compute_relationship_schema_gate(view, {"source_doc"})
        assert gate["rule"] == "target_registered"

    def test_supported_relations_covers_all_core_relations(self):
        # Scope-guard: the set should mirror folio/links.py SUPPORTED_RELATIONS.
        assert _SUPPORTED_RELATIONS == {"supersedes", "impacts", "draws_from", "depends_on"}


class TestDeriveRecommendedAction:
    def test_baseline_when_ok_and_no_gate(self):
        action = _derive_recommended_action("ok", None)
        assert action == "Review with `folio links review` and confirm or reject it."

    def test_notes_flagged_input(self):
        action = _derive_recommended_action("flagged", None)
        assert "flagged" in action

    def test_points_to_refresh_on_target_missing(self):
        action = _derive_recommended_action("ok", {"status": "fail", "rule": "target_registered"})
        assert "folio refresh" in action or "folio ingest" in action

    def test_rejects_on_unsupported_relation(self):
        action = _derive_recommended_action("ok", {"status": "fail", "rule": "supported_relation"})
        assert "folio links review" in action

    def test_unknown_rule_gives_generic_schema_gate_message(self):
        action = _derive_recommended_action("ok", {"status": "fail", "rule": "future_rule"})
        assert "Schema gate failed" in action
        assert "future_rule" in action


class TestLifecycleStatesUnchanged:
    def test_view_lifecycle_state_flows_through(self):
        # §6 inherited — no change. Each queued proposal carries a
        # valid lifecycle_state enum value.
        view = _make_view(proposal=_make_proposal(lifecycle_state="queued"))
        assert view.proposal.lifecycle_state in PROPOSAL_LIFECYCLE_STATES
