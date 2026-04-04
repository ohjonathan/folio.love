---
id: tier4_entities_bootstrap_report
type: validation
status: complete
created: 2026-04-04
---

# Tier 4 Production Entities Bootstrap — Validation Report

## 1. Executive Summary

**Decision:** PASS. The production `entities.json` bootstrap follow-up from
the Tier 3 closeout package is complete.

The McKinsey-laptop production run imported the US Bank / Technology
Resilience 2026 org chart into the supported entity registry path, verified
that the resulting `entities.json` is readable and non-empty, regenerated
entity stubs, and closed the last operational prerequisite that was still
called out in the original Tier 3 closeout report. The evidence in this file
is operator-attested from a separate McKinsey-laptop checkout, not directly
repo-verifiable from this repository snapshot.

## 2. Run Summary

| Metric | Value |
|--------|-------|
| Source CSV | `ada-output/export-data/org_chart.csv` |
| Prepared import CSV | `org_chart_folio_import.csv` |
| Source row count | 1,531 |
| People imported | 1,492 |
| Departments created | 9 |
| Total imported entities | 1,501 |
| Alias-collision warnings | 55 |
| Slug-collision skips | 39 |
| Unconfirmed entities after import | 0 (CSV imports auto-confirm by design) |
| Entity stubs after refresh | 2,635 total |
| Prior stubs | 1,134 |
| Stub total after refresh | 2,635 (operator-reported) |
| `entities.json` size | ~733 KB |
| Matching recent interaction participants | None of `Mark Piersak`, `Andrew Lee`, `Bradley Pearce` were present in the org chart |

## 3. Supported Workflow Verification

The run followed the supported Tier 3 / Tier 4 entity workflow:

1. org-chart CSV selected from the engagement workspace
2. import CSV prepared for `folio entities import <csv>`
3. production entity registry imported via `folio entities import`
4. stubs refreshed with `folio entities generate-stubs --force`
5. verification performed with `folio status`, `folio entities`,
   `folio entities --unconfirmed`, and `folio entities show`

No custom bootstrap script or hand-authored `entities.json` registry was
introduced as the system of record. The only prep step outside the Folio CLI
was the column-rename script used to prepare the source CSV for the supported
import command.

## 4. Validation Results

### Registry State

- The production library now has a readable, non-empty `entities.json`.
- Entity totals after import were reported as:
  - 1,492 `person`
  - 9 `department`
- Remaining unconfirmed entities: 0. This reflects the supported CSV import
  path auto-confirming imported rows by design; it should not be read as
  manual per-entity verification.

### Stub State

- Pre-existing entity stubs: 1,134
- Total stubs after refresh: 2,635
- The reported totals imply a net increase of 1,501 stubs, but this
  reconstructed artifact does not independently prove a one-stub-per-import
  relationship because 39 slug-collision skips were also reported.

### Known Non-Matches

The recent interaction participants used in the production ingest proof:

- `Mark Piersak`
- `Andrew Lee`
- `Bradley Pearce`

did not appear in the imported org-chart CSV. The bootstrap correctly left
them out of the production registry rather than force-creating or falsely
confirming them.

## 5. Documentation / Provenance Notes

- The McKinsey-laptop operator reported the work as committed locally under
  `8e8c78b`, but that commit exists only on the separate McKinsey-laptop
  checkout and is not verifiable from this repo.
- The four expected validation artifacts for this run are now present under
  `docs/validation/`.
- The Tier 3 closeout report and Tier 3 tracker were updated so the production
  `entities.json` bootstrap is no longer described as an open Tier 4
  prerequisite.

## 6. Residual Risks

1. The import summary reported 55 alias-collision warnings and 39
   slug-collision skips. These did not block the bootstrap, but they indicate
   that the org chart is not a perfect one-to-one identity source, and this
   repo does not independently prove whether the skipped slugs were benign
   duplicates or missed coverage.
2. Title data in the source CSV was empty for all rows, so title-level
   enrichment did not improve during the bootstrap, which weakens one easy
   disambiguation aid for same-name people.
3. Some real engagement participants still exist only as wikilinks in
   interaction notes and were not covered by the org-chart CSV.

## 7. Recommendation

Treat the production `entities.json` bootstrap as complete and closed. Tier 4
feature work can now begin from the retained production library without any
remaining Tier 3 operational follow-ups.

## 8. Artifacts Produced

| Artifact | Path |
|----------|------|
| Prompt | `docs/validation/tier4_entities_bootstrap_prompt.md` |
| Report | `docs/validation/tier4_entities_bootstrap_report.md` |
| Session log | `docs/validation/tier4_entities_bootstrap_session_log.md` |
| Chat log | `docs/validation/tier4_entities_bootstrap_chat_log.md` |
