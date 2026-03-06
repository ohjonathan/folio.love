---
id: log_20260306_merge-pull-request-2-from-ohjonathan-feat-core-ex
type: log
status: active
event_type: core-extraction-hardening-review-merge
source: cli
branch: main
created: 2026-03-06
---

# Merge pull request #2 from ohjonathan/feat/core-ex

## Summary

Core Extraction Hardening (v0.3.2) implemented, reviewed (3 independent AI reviewers × 2 review rounds), and merged to main. Addresses all blocking, should-fix, and minor items from the consolidated spec review.

## Changes Made

- **PR #2** (`feat/core-extraction-hardening` → `main`): Full spec implementation
  - Input validation, timeout scaling, atomic swap in `normalize.py` and `images.py`
  - `ImageResult` dataclass, `extract_with_metadata()`, blank/tiny detection
  - HR boundary pattern, tightened Pattern 3, table detection in `text.py`
  - `reconcile_slide_count()` with gap-filling, alignment confidence
  - Three-layer failure policy (L1/L2/L3) for PDF and PPTX
  - Blank-slide override, reconciliation metadata in frontmatter
  - `.texts_cache.json` version migration (B3)
- **PR #3** (`fix/review-followup` → `feat/core-extraction-hardening`): Review fixes
  - Removed dead `_validation_cache`, replaced `getdata()` with `histogram()`
  - YAML-validated frontmatter stripping, `skip_slides` in `analyze_slides_deep()`
  - `gap_filled` action, `_compute_timeout` floor, Pattern 3 content guard
  - Atomic swap error wrapping, parser L2 fallback coverage

## Key Decisions

- Keep `_validate_image()` in `extract()` (B1) — removing causes NameError
- Copy input dict at top of `reconcile_slide_count()` (B2) — prevents mutation
- Cache version marker for `.texts_cache.json` (B3) — clean upgrade path
- Histogram over `getdata()` — eliminates Pillow deprecation, ~1000x faster
- Removed `_validation_cache` — path mismatch made it dead code; histogram makes it unnecessary
- Pattern 3 content guard (>20 chars) — prevents numbered-list false positives

## Testing

- 176 tests passing (71 new across 4 new test files + 1 modified)
- 0 Pillow deprecation warnings
- All 15 files changed, +2,958 lines