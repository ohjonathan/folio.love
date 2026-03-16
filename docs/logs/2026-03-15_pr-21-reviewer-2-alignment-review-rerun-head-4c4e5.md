---
id: log_20260315_pr-21-reviewer-2-alignment-review-rerun-head-4c4e5
type: log
status: active
event_type: decision
source: codex
branch: codex/diagram-pr3-schema-cache
created: 2026-03-15
---

# pr-21-reviewer-2-alignment-review-rerun-head-4c4e50d

## Context

Alignment rerun for PR #21 on branch `codex/diagram-pr3-schema-cache`
at `4c4e50d423651aa459a2f3d559cf63a88a1c3213`, compared against `main`
with extra attention to the delta since
`1bc56bca6c20680cf512e99df8683cddfc4093b1`.

## Goal

Verify whether the latest fixes bring the PR 3 schema-cache branch into
alignment with the approved stable edge-ID contract and the approved
diagram-payload deserialization architecture without introducing
regressions.

## Decision

Request changes. The partial-payload fix is aligned and the branch is
otherwise green, but the updated edge-ID helper still does not fully satisfy
the approved stability contract for parallel edges when the disambiguation
keys tie.

## Rationale

- Ran Ontos activation and reviewed the PR 3 prompt, the proposal stable-ID
  sections, the PR21 minor-fixes prompt, and the prior rerun review logs.
- Compared the branch against `main` and inspected the latest code delta in
  `folio/pipeline/analysis.py` and `tests/test_diagram_analysis.py`.
- Ran focused validation:
  - `.venv/bin/python -m pytest tests/test_diagram_analysis.py tests/test_analysis_cache.py tests/test_converter_integration.py tests/test_grounding.py -q`
    → `230 passed`
  - `.venv/bin/python -m pytest tests -q`
    → `767 passed, 3 skipped`
- Reproduced that `_rewrite_edge_ids()` is now stable for reordered parallel
  edges when `label`/`direction` differ, but still changes ID assignment when
  two parallel edges share the same `(label, direction)` sort key.
- Confirmed the new `_validate_base_fields()` behavior keeps
  `description`/`graph`-only diagram payloads in `DiagramAnalysis` form while
  preventing them from looking like clean analyses, with no observed suite
  regressions.

## Key Decisions

- Treated the stable-ID contract in the approved proposal/prompt as the merge
  gate, not just current test pass status.
- Counted the remaining edge-ID tie-case as a blocking deviation because the
  helper and docstring still claim order independence.
- Treated the partial-payload validator as aligned because it preserves
  polymorphic routing and did not break existing runtime or test behavior.

## Alternatives Considered

- Approve because the touched modules and full test suite are green. Rejected
  because the direct helper probe still finds an order-sensitive corner case
  under equal sort keys.
- Block on the partial-payload validator for changing `review_required`
  during deserialization. Rejected because that behavior is consistent with
  the architecture’s safety goals and caused no observed regression.

## Consequences

- Merge should remain blocked until edge-ID disambiguation is made stable even
  when parallel edges share the same current sort key, or the contract is
  explicitly narrowed and re-approved.
- No additional blocker was found in the partial-payload fix path.

## Impacts

- Prevents PR 3 from shipping a helper that still overstates its stability
  guarantees for future override persistence.
- Confirms the description/graph-only deserialization behavior is now aligned
  enough to avoid silent diagram payload downgrades.
