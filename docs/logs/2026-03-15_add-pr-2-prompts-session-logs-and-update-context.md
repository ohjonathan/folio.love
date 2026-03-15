---
id: log_20260315_add-pr-2-prompts-session-logs-and-update-context
type: log
status: active
event_type: pr20-cache-hit-provenance-and-merge-prep
source: cli
branch: codex/diagram-pr2-provider-dpi-tiles
created: 2026-03-15
---

# PR 20: Cache-Hit Provenance Fix and Merge Prep

## Summary

Closed the final mixed-provider provenance gap in PR 20. Cache-hit paths
in pass-1 and pass-2 now populate `per_slide_providers` from cached
`_provider`/`_model` entries. Hardened `_cached_provider_model` helper
to require both fields present and non-empty before trusting cached
provenance.

## Key Decisions

- **Stricter provenance validation:** `_cached_provider_model` now
  requires both `_provider` (non-empty str) and `_model` (non-empty str)
  to use cached values; partial entries fall back to primary pair.
- **Pass-2 miss path:** Added fallback summary metadata tracking on the
  miss path (was only on cache-hit path).
- **Derive `mixed_providers` from `per_slide_providers`:** Converter
  inspects the per-slide map rather than relying on summary booleans alone.

## Changes Made

- `folio/pipeline/analysis.py`: `_cached_provider_model` helper, pass-1
  and pass-2 cache-hit bookkeeping, pass-2 miss fallback summary.
- `folio/llm/types.py`: `per_slide_providers` field (added in prior round).
- `folio/converter.py`: `mixed_providers` and `providers_used` derivation.
- `tests/test_analysis_cache.py`: 6 new tests (TestCacheHitProvenance).
- `tests/test_converter_integration.py`: 1 new integration test
  (TestLLMMetadataConverterIntegration).

## Testing

690 passed, 3 skipped. 3 skips are optional SDK import checks.

## Alternatives Considered

- Deriving all fallback flags from `per_slide_providers` only:
  rejected because existing code already tracks `fallback_activated`
  on the miss path; duplicating derivation adds complexity.

## Impacts

- Cache-hit provenance is now accurate for mixed-provider warm-cache runs.
- Frontmatter `mixed_providers`, `providers_used`, and `fallback_used`
  are consistent across cold and warm cache scenarios.