---
id: log_20260315_pr22-diagram-extraction-tier2-fixes
type: log
status: closed
event_type: pr22-diagram-extraction-tier2-fixes
source: cli
branch: codex/diagram-pr4-extraction
created: 2026-03-15
---

# PR 22: Diagram Extraction Tier 2 Review Fixes

## Goal

Resolve all blocking, should-fix, and minor issues from the Tier 2 adversarial review of PR #22 (diagram extraction pipeline).

## Key Decisions

- **Type gate**: Narrowed from 18-type allowlist to `{architecture, data-flow}` only, per approved proposal L62.
- **Sanity check**: Replaced graph-size delta with accounting-based mutation ratios (>40% overall, >50% action dominance).
- **Pass C highlights**: Per-batch claim-relevant bboxes instead of all-node overlay.
- **Cache IoU**: `load_stale_entry()` bypasses marker validation for ID inheritance across model/prompt changes.
- **Abstention**: Denylist → allowlist for diagram types; `pass_c_verdicts_parsed` differentiated from `pass_c_attempted`.

## Alternatives Considered

- Broad type allowlist (18 types) — rejected as exceeding approved v1 scope.
- All-node highlight overlay for Pass C — rejected as weakening dense-diagram verification per proposal contract.
- In-memory-only stale cache lookup — broken when `load_stage_cache` rejects on marker mismatch.

## Impacts

- `diagram_extraction.py`: ~400 lines changed across 8 commits
- `diagram_cache.py`: +40 lines (`load_stale_entry`)
- Tests: 894 passed, 3 skipped (+25 new regression tests)
- No breaking changes to existing APIs

## Changes Made

1. B1: Evidence-driven image strategy (global-only for simple Pass A, global-only Pass C)
2. B2: Cache dep hashes expanded (text_inventory + profile), stale-cache IoU via `load_stale_entry()`
3. B3: Mutation-ratio sanity check returning `(triggered, reason)` with review_questions
4. B4: Complete abstention (unsupported types, empty graphs, low confidence)
5. B5: `pass_c_verdicts_parsed` vs `pass_c_attempted` safety
6. S-F1: Ghost edge validation, `change_direction`, `regroup` actions
7. S-F2: Sweep edge confidence cap (≤0.5)
8. Type gate narrowed to architecture + data-flow only
9. Per-batch claim-relevant highlights for Pass C
10. 25 regression tests added

## Testing

```
894 passed, 3 skipped in 14.47s
```