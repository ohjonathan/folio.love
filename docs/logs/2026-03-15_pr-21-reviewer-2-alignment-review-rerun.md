---
id: log_20260315_pr-21-reviewer-2-alignment-review-rerun
type: log
status: active
event_type: decision
source: codex
branch: codex/diagram-pr3-schema-cache
created: 2026-03-15
---

# pr-21-reviewer-2-alignment-review-rerun

## Context

Alignment review rerun for PR #21 on branch `codex/diagram-pr3-schema-cache`
at `1bc56bca6c20680cf512e99df8683cddfc4093b1`, compared against `main`
with special attention to the delta since
`acacfe40c0d1310656d2a0509c3f408b87ede9e0`.

## Goal

Verify that the current PR 3 foundation matches the approved proposal, the
merged PR 1 / PR 2 runtime invariants, and the PR21 follow-up prompt without
introducing backward-compatibility regressions.

## Decision

Request changes. The latest delta fixes the prior description-marker
misalignment and adds the missing warm-cache coverage, but the edge-ID
contract remains materially misaligned with the approved proposal for
parallel edges.

## Rationale

- Ran Ontos activation and reviewed the PR 3 prompt, PR21 follow-up prompt,
  proposal sections covering `DiagramAnalysis`, routing, and stable IDs.
- Compared the branch against `main` and against
  `acacfe40c0d1310656d2a0509c3f408b87ede9e0`.
- Ran targeted validation:
  - `.venv/bin/python -m pytest tests/test_diagram_analysis.py tests/test_analysis_cache.py tests/test_converter_integration.py tests/test_grounding.py -q`
    → `225 passed`
  - `.venv/bin/python -m pytest tests -q`
    → `762 passed, 3 skipped`
- Confirmed the description-only factory dispatch issue is fixed.
- Reproduced that `_rewrite_edge_ids()` still assigns different IDs to the
  same logical parallel edges when their list order changes, because the
  per-pair counter is order-sensitive.

## Key Decisions

- Treated proposal alignment as the primary gate, not test pass rate alone.
- Counted the edge-ID instability as a blocking architecture issue because PR 3
  is explicitly establishing the stable-ID foundation for later override
  persistence work.
- Did not raise additional routing/cache/body concerns once the latest code and
  tests showed those areas aligned with the prompt and current runtime.

## Alternatives Considered

- Approve because the full suite is green and the latest delta resolves the
  prior description-marker blocker. Rejected because the parallel-edge ID
  contract still does not satisfy the proposal's stability claim.
- Downgrade the edge-ID issue to a future-PR concern. Rejected because the PR
  body and helper docstring both present the current helper as aligned with the
  approved contract.

## Consequences

- Merge should stay blocked until the edge-ID helper is made stable for
  logically identical parallel edges across run-order variation, or the
  contract is narrowed and re-approved explicitly.
- The rest of the rerun scope is in good shape: factory markers, routing,
  cache-marker behavior, PR 2 invariants, and PR body/test-count accuracy all
  check out.

## Impacts

- Prevents PR 3 from locking in an order-sensitive edge identity contract that
  would later undermine override persistence and graph reconciliation.
- Provides a clear rerun record showing that only one material proposal
  deviation remains after the latest fixes.
