---
id: log_20260315_pr-21-reviewer-3-adversarial-review-rerun
type: log
status: active
event_type: decision
source: codex
branch: codex/diagram-pr3-schema-cache
created: 2026-03-15
---

# pr-21-reviewer-3-adversarial-review-rerun

## Context

Merge-readiness rerun for PR #21 on branch `codex/diagram-pr3-schema-cache`
at `4c4e50d423651aa459a2f3d559cf63a88a1c3213`, compared against `main`
with special attention to the delta since
`1bc56bca6c20680cf512e99df8683cddfc4093b1`.

## Goal

Re-check the previously blocked PR after the follow-up commit, with adversarial
focus on:

- reordered parallel-edge stability
- duplicate parallel edges with the same label/direction
- partial graph-only and description-only warm-cache payloads through
  `analyze_slides()` and `FolioConverter.convert()`
- any regressions introduced by the new hardening logic

## Decision

Block merge.

## Rationale

The rerun fixes the earlier order-sensitivity case for parallel edges with
distinct `(label, direction)` sort keys, and the targeted test set still
passes (`230 passed`). Two blocking correctness gaps remain:

1. `_rewrite_edge_ids()` is still order-sensitive for duplicate parallel edges
   whose `(label, direction)` keys are identical. Reversing two otherwise
   identical `a -> b` edges with distinct `evidence_bbox` values swaps which
   edge receives `a_b` vs `a_b_1`, so the helper still does not provide stable
   cross-run edge identity for that shape.
2. The new partial-payload hardening only sets
   `DiagramAnalysis.review_required = True`. Converter/frontmatter review
   derivation does not consume that field, so graph-only and description-only
   warm-cache payloads still round-trip through `analyze_slides()` into
   `FolioConverter.convert()` as document-level `review_status: clean`, with
   blank `Slide Type` / `Framework` lines in the rendered markdown.

## Key Decisions

- Treated proposal-contract stability and end-to-end converter behavior as the
  gate, not unit-test pass rate alone.
- Ran the PR-focused test subset:
  `.venv/bin/python -m pytest tests/test_diagram_analysis.py tests/test_analysis_cache.py tests/test_converter_integration.py tests/test_grounding.py -q`
  which passed (`230 passed`).
- Used direct local repros in addition to the existing tests to probe duplicate
  parallel edges and partial warm-cache payloads, because the added tests only
  cover distinct-label edge reordering and deserializer-level `review_required`
  toggling.

## Alternatives Considered

- Approve because the follow-up commit addresses the original reordered-edge
  case and the targeted suite is green. Rejected because duplicate same-key
  parallel edges still violate the stable-ID goal.
- Treat the partial warm-cache issue as out of scope because it requires a
  malformed/legacy cache entry. Rejected because this commit explicitly claims
  partial-payload cache hardening, yet the converter still publishes those
  payloads as clean output.

## Consequences

PR #21 should remain blocked until duplicate same-key parallel edges receive a
stable disambiguation strategy and partial warm-cache diagram payloads are
escalated into converter/frontmatter review state instead of only toggling an
unused `review_required` field.

## Impacts

- Prevents PR 3 from shipping an edge-ID scheme that still changes across
  input-order variation for duplicated logical edges.
- Prevents malformed warm-cache diagram payloads from silently surfacing as
  clean conversions with blank analysis fields.
