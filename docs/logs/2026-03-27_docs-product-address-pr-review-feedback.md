---
id: log_20260327_docs-product-address-pr-review-feedback
type: log
status: active
event_type: pr36-product-baseline-docs-sync-merge
source: cli
branch: codex/docs-tier3-prc-baseline-sync
created: 2026-03-27
---

# docs(product): address PR review feedback

## Goal

Close the remaining review items on PR #36 so the product-doc sync is
merge-ready before PR C planning begins.

## Summary

Addressed the blocking and should-fix feedback on the late-March product-doc
sync PR. The branch now includes the missing tracked vault-validation package,
the roadmap’s softened v1/v2 boundary for entity resolution, an updated
prioritization matrix, and a renamed Tier 3 baseline decision memo.

## Changes Made

- Published a repo-safe vault-validation artifact set under `docs/validation/`
  so product docs no longer reference missing files.
- Updated `02_Product_Requirements_Document.md` to point at the renamed
  decision memo and to clarify the current entity-registry versus
  ingest-extraction boundary.
- Updated `04_Implementation_Roadmap.md` so entity resolution beyond v1
  remains an explicit open question, while v1 shipped status stays clear.
- Updated `06_Prioritization_Matrix.md` so entity work is recorded as shipped
  baseline rather than future-only scope.
- Renamed `2026-03_late_march_status_update.md` to
  `tier3_baseline_decision_memo.md` and tightened it into a baseline-decision
  record.
- Sanitized vault-validation and rerun-summary artifacts to remove machine
  paths, client-sensitive titles, and local workspace identifiers before
  publishing.

## Key Decisions

- Keep the PR focused on product-doc and validation-doc sync rather than
  widening into application code or PR C planning.
- Treat entity resolution as “shipped for v1 common cases, still open beyond
  v1” instead of fully closed.
- Preserve the validation package as tracked artifacts because the product docs
  now depend on those reports for baseline justification.
- Rename the memo to a decision-record shape instead of leaving it as a
  month-stamped status memo.

## Alternatives Considered

- Leave the vault-validation artifacts uncommitted and remove the references
  from product docs.
  Rejected because the docs should point to the actual validation evidence.
- Keep entity resolution fully in the roadmap’s resolved list.
  Rejected because production-scale exercise and enrichment-time backfill are
  still untested.
- Keep the original long status memo filename and structure.
  Rejected because the document is a baseline decision record, not a recurring
  monthly report.

## Impacts

- PR #36 is now aligned with the actual shipped Tier 3 baseline and its
  supporting validation evidence.
- Product docs now more clearly separate shipped v1 entity behavior from later
  entity-resolution work.
- PR C can start from a cleaner documented baseline without reopening the late
  March operational decision.

## Testing

- Docs-only change; no application tests were run.
- Performed targeted sensitivity scans on the published validation artifacts to
  verify removal of local machine paths and identifiable note names.
- Verified the roadmap, PRD, prioritization matrix, and decision memo no
  longer contradicted the shipped entity-system baseline.
