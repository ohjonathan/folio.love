---
id: tier2_closeout_checklist
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
---

# Tier 2 Closeout Checklist Before Tier 3

## Purpose

This checklist is the operational gate between **Tier 2: Daily Driver** and
**Tier 3: Engagement Intelligence**.

It translates the current Tier 2 exit criteria in
[04_Implementation_Roadmap_v2.md](../product/04_Implementation_Roadmap_v2.md)
and the supporting PRD requirements in
[02_Product_Requirements_Document.md](../product/02_Product_Requirements_Document.md)
into a concrete pass/fail tracker.

Tier 3 should not start until this checklist is complete and the result is
explicitly recorded.

## Decision Rule

**GO TO TIER 3** requires:

- every Tier 2 exit criterion marked `PASS`, or
- an explicit written waiver for any non-pass item, with rationale and owner.

Without that, the correct status is:

- `STAY IN TIER 2`

## Current Baseline

Tier 2 implementation work is now on `main`, including:

- registry-backed library indexing
- source-root-aware output routing
- `folio status` on registry
- `folio scan`
- `folio refresh`
- `folio promote`
- Obsidian query documentation

This checklist is about proving those features work in a real daily-driver
workflow, not about building more Tier 2 code by default.

## Tier 2 Exit Criteria Tracker

| # | Criterion | Source | PASS Means | Required Evidence | Current Status |
|---|-----------|--------|------------|-------------------|----------------|
| 1 | CLI handles full daily workflow (`convert`, `batch`, `status`, `scan`, `refresh`, `promote`) | Roadmap Tier 2 exit criteria | All six commands are used successfully in a real workflow without manual registry repair or ad hoc file surgery | Dated usage log covering at least one real `scan -> refresh -> status` loop, one `promote`, one direct `convert`, and one `batch` run | Not started |
| 2 | Route-based LLM selection plus `--llm-profile` override work in normal use | Roadmap Tier 2 exit criteria, PRD FR-501/502/604 | Route-based selection works by default and explicit `--llm-profile` override changes the execution path as expected | At least one routed run and one override run with output or metadata evidence (`_llm_metadata` or CLI output) | Not started |
| 3 | Multi-client library is organized and navigable | Roadmap Tier 2 weeks 9-10 and Tier 2 Gate | Library includes at least 100 decks and is understandable and usable across real clients/engagements with no silent misrouting | Snapshot of actual library tree, count of decks, count of clients/engagements, and spot-check of mapped output routing | Not started |
| 4 | Obsidian opens the library with no errors | Roadmap Tier 2 exit criteria, PRD FR-402, NFR-300 | Real vault opens cleanly, frontmatter parses, images render, no systematic broken links | Obsidian validation note with screenshots or direct observations from a real vault open | Not started |
| 5 | Dataview queries work for all important frontmatter fields | Roadmap Tier 2 exit criteria | Query cookbook works against the real vault for the operational fields that drive discovery and triage | Query results for at least: `type`, `subtype`, `client`, `engagement`, `authority`, `curation_level`, `tags`, `frameworks`, `slide_types`, `source_type`, `version` | Not started |
| 6 | Configuration supports multiple source roots | Roadmap Tier 2 exit criteria, PRD FR-202 | At least two source roots work correctly, including one empty `target_prefix` and one non-empty `target_prefix` | `folio.yaml`, commands, and output paths demonstrating both routing modes | Not started |
| 7 | Configuration supports named LLM profiles and provider credential references | Roadmap Tier 2 exit criteria, PRD FR-601 to FR-606 | Multiple named profiles are usable from config without raw secrets in config | Sanitized config example plus one successful run per tested provider/profile path | Not started |
| 8 | Johnny uses it daily on a real engagement for 2+ weeks | Roadmap Tier 2 exit criteria | Folio is used as the normal workflow, not as a one-off validation exercise | Two-week usage log with dates, commands run, friction points, and whether Folio replaced the prior manual loop | Not started |

## Supporting Quality Checks

These are not separate roadmap bullets, but they are required to justify a
serious Tier 2 closeout decision.

| # | Check | Source | PASS Means | Required Evidence | Current Status |
|---|-------|--------|------------|-------------------|----------------|
| 9 | `status` remains fast at realistic library scale | PRD NFR-100 | `folio status` feels effectively instantaneous on the real library and remains within the documented target envelope | Timed runs on the real library; record deck count and runtime | Not started |
| 10 | Crash recovery / registry integrity is acceptable in real use | PRD NFR-200 | No observed registry corruption or manual registry repair during the 2-week loop | Usage log explicitly records whether any registry rebuilds, corruptions, or manual repairs occurred | Not started |
| 11 | Error messages and progress feedback are good enough for daily use | PRD NFR-400 | Failures are actionable and long-running operations provide adequate feedback | Short operator assessment with concrete examples from `batch`, `scan`, and `refresh` | Not started |
| 12 | Sync/path portability is not regressing the daily-driver loop | PRD NFR-300, Tier 1 closeout baseline | Existing Tier 1 portability assumptions still hold under normal Tier 2 usage | Note whether the daily-driver run involved a synced library path and whether any path-related issues appeared | Not started |

## Required Validation Activities

### 1. Daily-Driver Loop Validation

Run Folio as a normal tool for at least 2 weeks on a real engagement.

Minimum activities during that window:

- convert at least 3 new assets with `folio convert`
- run at least 1 meaningful `folio batch`
- run `folio scan` after source changes
- run `folio refresh` on detected stale items
- run `folio status` regularly as the index view
- run `folio promote` on at least 2 useful documents

This is the most important Tier 2 gate. If this does not happen, Tier 2 is not
actually closed.

### 2. Obsidian Validation

Use the real library as an Obsidian vault and verify:

- frontmatter parses cleanly
- image links render
- Dataview queries from `docs/obsidian_queries.md` work or are updated to work
- no recurring YAML/frontmatter compatibility errors

### 3. Source Mapping / Routing Validation

Verify at least these routing cases:

- source root with empty `target_prefix`
- source root with non-empty `target_prefix`
- explicit `--target` still overrides routing
- explicit `--client` / `--engagement` override inference where intended

Record at least 5 concrete source-path to output-path examples.

### 4. Registry / Refresh Validation

Verify at least these behaviors in real usage:

- missing `registry.json` bootstraps cleanly
- `scan` finds new and stale sources correctly
- `refresh` only reconverts intended decks by default
- scoped `status` / `refresh` behave correctly
- `promote` updates frontmatter and version history without drift

### 5. LLM Profile Validation

Verify:

- default route-based selection in normal convert/batch use
- explicit `--llm-profile` override
- provider/model metadata remains visible in output provenance

## Required Artifacts

Before calling Tier 2 complete, produce all of these:

- `docs/validation/tier2_closeout_report.md`
- `docs/validation/tier2_closeout_session_log.md`
- `docs/validation/tier2_closeout_chat_log.md`
- `docs/validation/tier2_closeout_prompt.md`
- updated checklist statuses in this file
- any supporting screenshots or sample query outputs referenced by the report

## Required Sections in the Tier 2 Closeout Report

The closeout report must include:

1. Executive summary
2. Tier 2 exit criteria table with `PASS / PARTIAL / FAIL`
3. Daily-driver usage log summary
4. Obsidian validation summary
5. Source mapping / registry integrity summary
6. Real-world friction log
7. Go / no-go recommendation for Tier 3
8. If `GO`, list accepted limitations carried into Tier 3
9. If `NO-GO`, list the exact blockers and next actions

## Go / No-Go Rules

### GO TO TIER 3

Use this only if:

- the 2-week real-engagement usage criterion passes
- the full daily-driver loop works in practice
- Obsidian validation passes
- no serious registry drift or silent source misrouting is observed

### STAY IN TIER 2

Use this if any of the following happen:

- daily use was not actually completed
- `scan` / `refresh` / `promote` prove too unreliable for real workflow use
- registry corruption or drift appears in real usage
- source mapping causes wrong or confusing library placement
- Obsidian/Dataview usage is still materially broken

## Known Questions to Resolve During Closeout

These are not automatic blockers, but they should be answered explicitly in the
closeout report:

- Is the current package/install story good enough for daily use, or does Tier 2 still need packaging hardening?
- Is `folio status` fast enough on the real library, not just in tests?
- Are the current Obsidian query docs sufficient, or do they need to be rewritten after actual vault use?
- Are any Tier 1 accepted limitations still painful enough in day-to-day use that they should be promoted before Tier 3?

## Suggested Owner Workflow

1. Keep this checklist as the live tracker.
2. Run the daily-driver validation period.
3. Fill out the closeout report and session log.
4. Update this checklist from `Not started` to `PASS / PARTIAL / FAIL`.
5. Make the Tier 3 decision explicitly in writing.
