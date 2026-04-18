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
    """All three consumers — v0.7.1 graph, v0.8.0 synthesize, v0.9.0 search
    — call the same trust helper object. The shared-consumer uniformity
    proof at N=3 (load-bearing for parent §12)."""

    def test_graph_module_uses_shared_helper(self):
        from folio import graph as graph_mod
        from folio.tracking import trust as trust_mod

        assert graph_mod.derive_trust_status is trust_mod.derive_trust_status

    def test_synthesize_module_uses_shared_helper(self):
        from folio import synthesize as synth_mod
        from folio.tracking import trust as trust_mod

        assert synth_mod.derive_trust_status is trust_mod.derive_trust_status

    def test_search_module_uses_shared_helper(self):
        # NEW in v0.9.0: sub-slice 3 extends the invariant to N=3 surfaces.
        from folio import search as search_mod
        from folio.tracking import trust as trust_mod

        assert search_mod.derive_trust_status is trust_mod.derive_trust_status

    def test_graph_and_synthesize_share_identical_helper_object(self):
        from folio import graph as graph_mod
        from folio import synthesize as synth_mod

        assert graph_mod.derive_trust_status is synth_mod.derive_trust_status

    def test_all_three_consumers_share_identical_helper_object(self):
        # NEW in v0.9.0: the 3-way identity check. If any consumer re-
        # exports via alias, lazy-import shim, or monkeypatched override,
        # this will fail. Load-bearing for parent §12 uniformity.
        from folio import graph as graph_mod
        from folio import synthesize as synth_mod
        from folio import search as search_mod

        assert (
            graph_mod.derive_trust_status
            is synth_mod.derive_trust_status
            is search_mod.derive_trust_status
        )
