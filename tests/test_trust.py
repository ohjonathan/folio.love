"""Unit tests for folio.tracking.trust (shared trust-posture helper).

Covers the §11 trust-gating derivation, promoted from folio.graph in
sub-slice 2 (v0.8.0 Phase 0) per v0.7.1 ADV-SF6 carry-forward.
"""

from __future__ import annotations

from types import SimpleNamespace

from folio.tracking.trust import derive_trust_status


class TestDeriveTrustStatus:
    def test_empty_list_is_ok(self):
        view = SimpleNamespace(flagged_inputs=[])
        assert derive_trust_status(view) == "ok"

    def test_none_input_is_ok(self):
        view = SimpleNamespace(flagged_inputs=None)
        assert derive_trust_status(view) == "ok"

    def test_source_flagged_is_flagged(self):
        view = SimpleNamespace(flagged_inputs=["source"])
        assert derive_trust_status(view) == "flagged"

    def test_target_flagged_is_flagged(self):
        view = SimpleNamespace(flagged_inputs=["target"])
        assert derive_trust_status(view) == "flagged"

    def test_both_flagged_is_flagged(self):
        view = SimpleNamespace(flagged_inputs=["source", "target"])
        assert derive_trust_status(view) == "flagged"

    def test_unexpected_value_is_ok(self):
        # ADV-SF5 edge case: unexpected list contents don't match
        # {"source","target"}; result is "ok", not "flagged".
        view = SimpleNamespace(flagged_inputs=["both"])
        assert derive_trust_status(view) == "ok"

    def test_tuple_input_accepted(self):
        view = SimpleNamespace(flagged_inputs=("source",))
        assert derive_trust_status(view) == "flagged"

    def test_set_input_accepted(self):
        view = SimpleNamespace(flagged_inputs={"target"})
        assert derive_trust_status(view) == "flagged"


class TestSharedConsumerInvariant:
    """Both v0.7.1 graph and v0.8.0 synthesize call the same trust helper
    object — the shared-consumer uniformity proof."""

    def test_graph_module_uses_shared_helper(self):
        from folio import graph as graph_mod
        from folio.tracking import trust as trust_mod

        assert graph_mod.derive_trust_status is trust_mod.derive_trust_status

    def test_synthesize_module_uses_shared_helper(self):
        from folio import synthesize as synth_mod
        from folio.tracking import trust as trust_mod

        assert synth_mod.derive_trust_status is trust_mod.derive_trust_status

    def test_graph_and_synthesize_share_identical_helper_object(self):
        from folio import graph as graph_mod
        from folio import synthesize as synth_mod

        assert graph_mod.derive_trust_status is synth_mod.derive_trust_status
