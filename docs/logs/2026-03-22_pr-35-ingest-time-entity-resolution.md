---
id: log_20260322_pr-35-ingest-time-entity-resolution
type: log
status: complete
event_type: feature
source: codex
branch: feature/v0.5.1-entity-resolution
created: 2026-03-22
---

# PR #35 ingest-time entity resolution

## Goal

Implement PR #35 for v0.5.1 by connecting the shipped entity registry to
`folio ingest`, resolving confirmed entities to canonical wikilinks during
ingest, auto-creating unresolved entities for review, and surfacing proposed
matches in the existing entity review CLI.

## Key Decisions

- Added a dedicated ingest-time resolver module and hooked it into
  `ingest_source()` immediately after interaction analysis, before note write.
- Kept entity resolution body-only: no frontmatter schema changes and no
  markdown renderer changes.
- Preserved the confirmed-only, type-strict resolution boundary from the
  approved spec, with auto-created unresolved entities stored as
  `needs_confirmation: true`.
- Treated soft match as best-effort: malformed or failed LLM matching falls
  back to `match: null` rather than aborting ingest.
- Allowed output-only changes to existing `folio entities` commands so
  proposed matches are visible without expanding the CLI surface.

## Alternatives Considered

- Keeping proposed matches file-only in `entities.json` was rejected because it
  would not satisfy the human review flow or smoke-test expectations.
- Rewriting the interaction markdown renderer was rejected because canonical
  entity names can be supplied by the resolver without changing rendering.
- Adding frontmatter entity fields was rejected to preserve the v0.5.0
  interaction contract and the approved PR B scope boundary.
- Making soft match mandatory was rejected in favor of a non-fatal fallback so
  ingest remains robust when providers or credentials are unavailable.

## Impacts

- `folio ingest` now consults `entities.json` when present, resolves exact and
  alias matches to canonical names, and auto-creates unresolved entities for
  later confirmation.
- `folio entities` output now shows proposal state for unconfirmed entities.
- Added a new transcript fixture plus direct resolver and ingest integration
  coverage for exact match, alias match, auto-create, re-ingest behavior, and
  CLI review output.

## Testing

- `python3 -m pytest tests/test_entity_resolution.py tests/test_cli_entities.py tests/test_ingest_integration.py -q`
- `python3 -m pytest tests/test_entities.py tests/test_entity_import.py tests/test_cli_entities.py tests/test_cli_ingest.py tests/test_interaction_analysis.py tests/test_ingest_integration.py tests/test_entity_resolution.py -q`
- `python3 -m pytest tests/ -q`
  Result in this workspace: 1322 passed, 3 skipped, 18 failed, 2 errors, all
  due to missing optional `python-pptx` and `reportlab` dependencies already
  known from baseline.
- Final review cleanup: `python3 -m pytest tests/test_entity_resolution.py -q`
  (`22 passed`) and `python3 -m pytest tests/test_entity_resolution.py
  tests/test_cli_entities.py tests/test_ingest_integration.py -q`
  (`71 passed`).

## Documentation

- Archived the PR session via this log after the Round 4 cleanup pass and merge
  readiness verification.
