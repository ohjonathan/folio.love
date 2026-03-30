---
id: log_20260330_tier-3-lifecycle-integration-context-docs-regis
type: log
status: active
event_type: pr-e-tier3-lifecycle-integration-closeout
source: cli
branch: main
created: 2026-03-30
---

# Tier 3 Lifecycle Integration — PR E Closeout

## Summary

Merged PR #40 (squash → `6d904f8`). PR E delivers context documents, registry
schema v2, full engagement lifecycle test, and the Tier 3 closeout validation
package. Resolved 10 blocking review issues across 3 review rounds.

## Goal

Ship the final Tier 3 PR: context documents, source-less registry support,
end-to-end lifecycle integration test, and closeout validation templates.

## Key Decisions

1. **Schema v2 force-upgrade on save** — every `save_registry()` call writes
   `_schema_version: 2`, preventing stale v1 registries from persisting.
2. **Local date for context IDs** — `build_context_id()` uses local time (not
   UTC) so the stamped date matches the operator's calendar day.
3. **Validator subtype scope** — `engagement` field required only for
   `subtype=engagement`; `client_profile` and `workstream` are ontology-legal
   manual-only subtypes.
4. **Anti-rubber-stamp rules** — closeout report §9.7 requires current evidence
   per exit criterion, not historical references.
5. **Spoof detection** — validator flags context notes with 3+ source-backed
   fields as evidence-shaped mislabelling.

## Alternatives Considered

- UTC for context IDs (rejected: contract mismatch for users west of UTC near
  midnight).
- Warning-level review defaults (rejected: reviewers required hard-fail to
  prevent malformed context docs from passing validation).
- Separate `validate_library.py` script (deferred: inline `validate_deck()`
  spot-check is sufficient for closeout; full library validator is Tier 4 work).

## Changes Made

- `folio/context.py` — context document creation + registration (NEW)
- `folio/tracking/registry.py` — schema v2, source-less rows, `_str_or_none`
- `folio/cli.py` — `folio context init` command
- `tests/test_context.py` — 21 tests (NEW)
- `tests/test_tier3_lifecycle.py` — 4 tests, 12+ assertions (NEW)
- `tests/validation/validate_frontmatter.py` — context validation, spoof detection
- `docs/specs/folio_context_docs_tier3_closeout_spec.md` — spec (NEW)
- `docs/validation/tier3_closeout_*.md` — 4-file closeout package
- `docs/product/02_Product_Requirements_Document.md` — FR-405
- `docs/product/04_Implementation_Roadmap.md` — shipped status
- `docs/architecture/Folio_Ontology_Architecture.md` — date-bearing context ID
- `docs/validation/tier3_kickoff_checklist.md` — governance sync

## Testing

61 tests passing: `python3 -m pytest tests/test_context.py tests/test_registry.py tests/test_tier3_lifecycle.py -v`

## Impacts

- Tier 3 is now feature-complete pending production closeout validation.
- Registry schema v2 is the only persisted schema going forward.
- Context documents are first-class registry citizens excluded from
  scan/refresh/enrich/provenance pipelines.