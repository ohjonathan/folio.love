---
id: log_20260321_performance-patch-pr30-review
type: log
status: complete
event_type: performance-patch-pr30-review-and-merge
source: cli
branch: codex/performance-patch
created: 2026-03-21
---

# Performance Patch PR #30 — Implementation + 4 Review Rounds

## Goal

Implement 5 performance optimizations (P0–P4, P3) from the performance patch
spec and iterate through 4 rounds of PR review to reach merge-ready state.

## Key Decisions

- **P1b gating before coercion**: After R4 feedback, moved P1b gating to run
  BEFORE DiagramAnalysis coercion so gated pages keep their Pass-1
  SlideAnalysis. This prevents flag leakage and preserves P4 zero-text checks.
- **Content-hash dedup (P0)**: 64KB streaming SHA-256 chunks, per-file error
  handling for hash/read failures (non-fatal fallthrough).
- **Scope discipline**: Removed unapproved `DiagramAnalysis.gated` field and
  `diagram_gated_slide_{n}` flag after R3 feedback — kept within approved
  contract boundaries.

## Alternatives Considered

- Gating after coercion with `abstained=True` (rejected: leaks
  `diagram_abstained_slide_{n}` flag, excludes slides from P4 checks).
- Distinct `diagram_gated_slide_{n}` flag (rejected: scope violation, not
  approved in this patch).

## Impacts

- 5 workstreams implemented: P0 (dedup), P1a (table reclassification),
  P1b (diagram gating), P3 (large-doc warning), P4 (zero-text confidence).
- 1183 tests pass (3 skipped), up from 1171 pre-patch.
- No breaking changes to existing contracts.

## Changes Made

### Source
- `folio/cli.py`: P0 dedup with 64KB chunks, per-file error handling
- `folio/converter.py`: P1b gating (before coercion), P3 large-doc warning,
  module-level `_SKIP_DIAGRAM_TYPES`
- `folio/pipeline/analysis.py`: P4 zero-text confidence + flags
- `folio/pipeline/inspect.py`: P1a table-heavy reclassification
- `folio/pipeline/pdfium_adapter.py`: P1a vector geometry helper
- `folio/config.py`: P3 `large_document_warn_pages` config

### Tests (42 new tests total)
- `tests/test_cli_batch.py`: 10 tests (dedup, empty, combined, robustness, same-basename)
- `tests/test_converter_integration.py`: 8 tests (P1b gating, frozen-slide, combined)
- `tests/test_pipeline_integration.py`: 3 tests (P4 zero-text pipeline)
- `tests/test_grounding.py`: 6 tests (P4 confidence + flags)
- `tests/test_inspect.py`: 8 tests (P1a reclassification + false-positive)
- `tests/test_config.py`: 4 tests (P3 config validation)

## Testing

```
1183 passed, 3 skipped, 0 failed (15.33s)
```