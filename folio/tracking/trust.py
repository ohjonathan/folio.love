"""Shared trust-posture helpers for proposal-consuming surfaces.

Promoted from `folio/graph.py` (v0.7.1 ADV-SF6 carry-forward) so that
`folio graph`, `folio synthesize`, and future `folio search` share one
implementation of the §11 trust-gating derivation.
"""

from __future__ import annotations


def derive_trust_status(view) -> str:
    """Return ``"flagged"`` if the proposal's source or target input is flagged, else ``"ok"``.

    Duck-typed on ``view.flagged_inputs`` (any iterable or ``None``). Explicit
    set intersection avoids truthiness edge-cases per v0.7.1 ADV-SF5 closure.
    """
    flagged = set(view.flagged_inputs or [])
    return "flagged" if ({"source", "target"} & flagged) else "ok"
