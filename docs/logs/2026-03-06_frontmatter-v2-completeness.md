---
id: log_20260306_frontmatter-v2-completeness
type: log
status: active
event_type: implementation
source: Antigravity
branch: feat/frontmatter-v2
created: 2026-03-06
concepts:
  - frontmatter
  - ontology-compliance
  - reconversion-safety
---

# Frontmatter V2 Completeness

## Summary

Closed 5 gaps (G1-G5) between the Folio Ontology v2 Schema (Section 12) and
frontmatter output. Passed two rounds of 3-agent code review and addressed all
blocking issues before merge.

## Changes Made

- **G1:** `source_type` auto-detected from file extension (`deck` or `pdf`)
- **G2:** `subtype` configurable via `--subtype` CLI arg (default: `research`)
- **G3:** `industry` optional via `--industry` CLI arg (comma-separated)
- **G4:** Tag override via `--tags`, merged with auto-generated tags
- **G5:** Semantic group field ordering in frontmatter dict

### Review Fixes (Round 1)
- S1: String-to-list coercion guards for `industry`/`extra_tags`
- S2: CLI integration tests via CliRunner
- S3: `source_type` made keyword-only in `generate()`

### Review Fixes (Round 2)
- B1: `_read_existing_frontmatter()` rewritten with line-delimited fence detection
  (fixes reconversion corruption when YAML scalars contain `---`)
- B1: `generate()` validates preserved `id`/`created` (null/non-dict → safe fallback)
- B2: `source_type: report` documented as explicit deferral with acceptance tests
- SF1: Batch CLI forwarding test added

## Testing

- `tests/test_frontmatter.py`: 43 tests across 14 classes
- Full suite: 303 passed, 1 pre-existing error (pptx module)

## Key Decisions

- `source_type: report` deferred — requires semantic classification, not file-extension
  detection. Accepted per spec Section 7 and Ontology Section 12.4.
- Mixed-vault `source_type` inconsistency accepted — older PDFs retain `deck` until
  reconversion. No backfill tool in v0.1 scope.