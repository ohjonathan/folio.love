---
id: tier2_closeout_prompt
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
---

# Task: Tier 2 Closeout Validation and Tier 3 Go/No-Go Gate

## What You're Doing

This is **not** an implementation task. This is the formal closeout gate
between **Tier 2: Daily Driver** and **Tier 3: Engagement Intelligence**.

Tier 2 code is now on `main`. What is not yet proven is whether Folio is
actually usable as an everyday consulting workflow over time.

Your job is to validate that reality and produce a decision package for the
Chief Architect:

- `GO TO TIER 3`, or
- `STAY IN TIER 2`

You are validating the real daily-driver loop:

- `folio convert`
- `folio batch`
- `folio status`
- `folio scan`
- `folio refresh`
- `folio promote`

You are also validating:

- Obsidian vault usability
- Dataview query behavior
- source-root-aware routing
- registry integrity in real usage
- LLM routing / profile behavior in normal operation

## The Gate Is Already Defined

The checklist in
[tier2_closeout_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_checklist.md)
is the authoritative gate.

This prompt exists to run that checklist, not to redefine it.

Do **not** weaken the criteria during the run.

## Current Baseline

Work from the current `main` branch baseline reflected in these docs:

- [04_Implementation_Roadmap_v2.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap_v2.md)
- [02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md)
- [tier2_closeout_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_checklist.md)
- [tier1_closeout_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_closeout_report.md)
- [obsidian_queries.md](/Users/jonathanoh/Dev/folio.love/docs/obsidian_queries.md)

Important current truths:

- Tier 1 is closed sufficiently to support daily-driver use.
- Tier 2 implementation is shipped on `main`, including registry-backed status,
  scan, refresh, promote, and source-root-aware routing.
- Tier 3 should not begin until Tier 2 is validated in actual daily use.

## Read Before Doing Anything

Read these in order:

1. [tier2_closeout_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_checklist.md)
   Focus on:
   - all 8 Tier 2 exit criteria
   - supporting quality checks
   - required artifacts
   - go / no-go rules

2. [04_Implementation_Roadmap_v2.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap_v2.md)
   Focus on:
   - Tier 2 scope
   - Tier 2 exit criteria
   - Tier 3 start condition

3. [02_Product_Requirements_Document.md](/Users/jonathanoh/Dev/folio.love/docs/product/02_Product_Requirements_Document.md)
   Focus on:
   - FR-400 Library Organization
   - FR-500 CLI Commands
   - FR-600 LLM Provider Configuration
   - NFR-100 through NFR-400

4. [obsidian_queries.md](/Users/jonathanoh/Dev/folio.love/docs/obsidian_queries.md)
   Focus on:
   - actual query set to validate

5. Current runtime/code surface:
   - [folio/cli.py](/Users/jonathanoh/Dev/folio.love/folio/cli.py)
   - [folio/config.py](/Users/jonathanoh/Dev/folio.love/folio/config.py)
   - [folio/converter.py](/Users/jonathanoh/Dev/folio.love/folio/converter.py)
   - [folio/tracking/registry.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/registry.py)
   - [folio/tracking/sources.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/sources.py)
   - [folio/tracking/versions.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/versions.py)
   - [folio/output/frontmatter.py](/Users/jonathanoh/Dev/folio.love/folio/output/frontmatter.py)

## Validation Mode

This is a **real-use** validation, not a synthetic-only test.

The strongest Tier 2 criterion is:

- Johnny uses Folio daily on a real engagement for **2+ weeks**

If a real 2-week usage window is not available yet, do not fake completion.
Record `NOT COMPLETE` and explain why.

## Phase 1: Daily-Driver Loop Validation

### Goal

Determine whether Folio is usable as the normal operating workflow on a real
engagement.

### Minimum Required Usage During the Window

Over at least 2 weeks, capture all of the following:

- at least 3 real `folio convert` runs on new assets
- at least 1 meaningful `folio batch`
- repeated `folio status` usage as the normal library index view
- at least 1 real `folio scan` after source changes
- at least 1 real `folio refresh` from stale detection
- at least 2 real `folio promote` actions on useful documents

### What to Record

For each meaningful usage event:

- date
- command used
- what the user was trying to do
- whether it worked on first try
- whether any manual workaround was needed
- any confusion, friction, or slowness

### Hard Failure Conditions

Treat any of these as a Tier 2 blocker candidate:

- repeated registry drift or corruption
- repeated source misrouting
- `scan` / `refresh` behavior too unreliable for real use
- `promote` causing data loss or inconsistent metadata
- manual repair becoming part of the normal workflow

## Phase 2: Obsidian Validation

### Goal

Determine whether the library is genuinely usable as an Obsidian vault.

### What to Verify

- vault opens with no YAML/frontmatter errors
- converted markdown files render cleanly
- image links render in preview mode
- Dataview queries from [obsidian_queries.md](/Users/jonathanoh/Dev/folio.love/docs/obsidian_queries.md)
  work as documented or are updated to match reality
- no recurring broken-link or malformed-frontmatter pattern appears

### Required Query Coverage

Confirm queryability for at least:

- `type`
- `subtype`
- `client`
- `engagement`
- `authority`
- `curation_level`
- `tags`
- `frameworks`
- `slide_types`
- `source_type`
- `version`

## Phase 3: Library Organization and Source Mapping Validation

### Goal

Prove that the library is organized correctly at realistic scale.

### What to Verify

- library contains at least 100 decks across at least 5 clients, or clearly
  record that the scale criterion is not yet met
- source root with empty `target_prefix`
- source root with non-empty `target_prefix`
- explicit `--target` override still works correctly
- explicit `--client` / `--engagement` override inference where intended
- output paths are understandable and predictable

### Required Evidence

Capture:

- library tree sample
- total deck count
- client count
- engagement count
- at least 5 concrete source-path to output-path examples

## Phase 4: Registry, Status, Scan, and Refresh Validation

### Goal

Validate that the registry-backed daily-driver loop is trustworthy in real use.

### What to Verify

- missing `registry.json` bootstraps cleanly
- `folio status` is fast and usable on the real library
- `folio scan` finds new and stale sources correctly
- `folio refresh` reconverts the intended decks only
- scoped `status` / `refresh` work correctly
- no manual frontmatter changes or conversions create lasting registry drift

### Required Evidence

Capture:

- actual command lines
- observed runtime for `folio status`
- stale detection examples
- refresh examples
- any registry rebuild or recovery events

## Phase 5: Promote Validation

### Goal

Verify that `folio promote` is safe and useful in the real workflow.

### What to Verify

- promotion gates behave as expected
- promotion updates frontmatter
- promotion updates registry consistently
- promotion appends events without corrupting version history
- promoted documents remain stable on later conversions or refreshes

## Phase 6: LLM Profile / Routing Validation

### Goal

Validate the Tier 2 LLM configuration experience in real usage.

### What to Verify

- route-based selection works in ordinary `convert` / `batch` use
- explicit `--llm-profile` override works
- provider/model provenance remains visible
- if fallbacks are configured, transient fallback activation works as expected
- if fallbacks are not configured, record `N/A` explicitly

### Also Record

- whether the current profile model/routing setup is understandable
- whether provider credentials are manageable in day-to-day use

## Phase 7: Supporting Quality Checks

These do not replace the checklist, but they strengthen the decision:

- status performance on the real library
- error message quality
- progress feedback quality
- path/sync portability observations if the library is used from a synced path
- packaging/install friction that affects daily use

## Required Artifacts

This closeout run must produce all four required validation artifacts plus the
updated checklist:

- [docs/validation/tier2_closeout_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_report.md)
- [docs/validation/tier2_closeout_session_log.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_session_log.md)
- [docs/validation/tier2_closeout_chat_log.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_chat_log.md)
- [docs/validation/tier2_closeout_prompt.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_prompt.md)
- updated statuses in [tier2_closeout_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_checklist.md)

If you create helper scripts, save them under:

- [tests/validation](/Users/jonathanoh/Dev/folio.love/tests/validation)

## Required Report Structure

### 1. Executive Summary

| Item | Status | Notes |
|------|--------|-------|
| Daily-driver loop | | |
| Obsidian validation | | |
| Library organization / routing | | |
| Registry / refresh integrity | | |
| Promote safety | | |
| LLM profiles / fallback | | |
| Tier 2 overall | | |

### 2. Tier 2 Exit Criteria Table

Reproduce all 8 Tier 2 exit criteria from the checklist and mark each:

- `PASS`
- `PARTIAL`
- `FAIL`
- `NOT COMPLETE`

### 3. Daily-Driver Usage Summary

Include:

- date range
- engagement context
- commands used
- friction patterns
- whether Folio replaced the prior manual loop

### 4. Obsidian Validation Summary

Include:

- vault open result
- image rendering result
- Dataview query results
- any compatibility issues

### 5. Routing / Registry Integrity Summary

Include:

- source mapping observations
- registry bootstrap / refresh observations
- stale detection and refresh quality
- any drift/corruption incidents

### 6. LLM Configuration Summary

Include:

- route-based selection result
- override result
- fallback result or `N/A`
- provenance visibility

### 7. Friction Log

Capture the most important usability problems even if the overall result is
still `GO`.

### 8. Tier 3 Recommendation

Choose exactly one:

- `GO TO TIER 3`
- `STAY IN TIER 2`

If `GO`, list accepted limitations that are being carried forward.

If `STAY`, list the exact blockers and the next actions required.

## What NOT to Do

- Do **not** implement fixes during the closeout run.
- Do **not** reinterpret the checklist to make it easier to pass.
- Do **not** replace the 2-week real-use criterion with a short synthetic test.
- Do **not** skip failed commands or hide friction.
- Do **not** overwrite prior Tier 1 validation artifacts.
- Do **not** silently waive missing evidence.

## Final Decision Rule

Use this standard:

- If the real daily-driver workflow proves usable and the checklist passes,
  recommend `GO TO TIER 3`.
- If daily use is incomplete, or the workflow is still unreliable in practice,
  recommend `STAY IN TIER 2`.

This gate is about product readiness, not just whether the commands exist.
