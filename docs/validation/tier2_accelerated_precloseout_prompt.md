---
id: tier2_accelerated_precloseout_prompt
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
---

# Task: Tier 2 Accelerated Pre-Closeout Validation (2-Day)

## What You're Doing

This is **not** an implementation task. This is an **accelerated pre-closeout
validation** for Tier 2.

It is designed for a **2-day** execution window when there is not enough time
to complete the full official Tier 2 closeout gate.

This run is meant to answer:

- Is Tier 2 operationally solid enough to continue forward?
- Are there still real workflow blockers in `convert`, `batch`, `status`,
  `scan`, `refresh`, `promote`, registry, routing, or Obsidian usage?
- Is Tier 3 **planning** reasonable to begin now, even if the official
  2-week daily-use gate is still open?

This run is **not** allowed to claim full Tier 2 closeout by itself.

## What This Run Can and Cannot Decide

### This run CAN decide:

- whether the Tier 2 daily-driver workflow appears operationally sound
- whether major blockers remain
- whether it is reasonable to begin Tier 3 planning/spec work in parallel with
  the remaining Tier 2 time-based validation

### This run CANNOT decide:

- that Tier 2 is formally complete
- that the roadmap’s `2+ weeks of real daily use` criterion has passed
- that the official gate is `GO TO TIER 3` with no caveats

## The Official Gate Still Exists

The authoritative Tier 2 gate is in:

- [tier2_closeout_checklist.md](./tier2_closeout_checklist.md)

The full formal closeout prompt remains:

- [tier2_closeout_prompt.md](./tier2_closeout_prompt.md)

This accelerated prompt is a shorter operational readiness check, not a
replacement for the official gate.

## Required Framing for the Final Recommendation

Your final recommendation must choose exactly one of these:

1. `OPERATIONALLY READY; CONTINUE TIER 3 PLANNING, FULL TIER 2 CLOSEOUT STILL PENDING`
2. `STAY IN TIER 2; BLOCKERS REMAIN`

Do **not** output `GO TO TIER 3` from this accelerated run unless the operator
explicitly waives the official 2-week criterion in writing.

## Current Baseline

Work from the current `main` branch baseline reflected in these docs:

- [04_Implementation_Roadmap.md](../product/04_Implementation_Roadmap.md)
- [02_Product_Requirements_Document.md](../product/02_Product_Requirements_Document.md)
- [tier2_closeout_checklist.md](./tier2_closeout_checklist.md)
- [obsidian_queries.md](../obsidian_queries.md)

Important current truths:

- Tier 2 code is now on `main`
- Tier 1 is sufficiently stable to support normal usage
- the missing part is real workflow proof, not basic implementation
- the single strongest unresolved official criterion is still:
  `Johnny uses it daily on real engagement for 2+ weeks`

## Read Before Doing Anything

Read these in order:

1. [tier2_closeout_checklist.md](./tier2_closeout_checklist.md)
2. [04_Implementation_Roadmap.md](../product/04_Implementation_Roadmap.md)
3. [02_Product_Requirements_Document.md](../product/02_Product_Requirements_Document.md)
4. [obsidian_queries.md](../obsidian_queries.md)
5. Current runtime/code surface:
   - [folio/cli.py](/Users/jonathanoh/Dev/folio.love/folio/cli.py)
   - [folio/config.py](/Users/jonathanoh/Dev/folio.love/folio/config.py)
   - [folio/converter.py](/Users/jonathanoh/Dev/folio.love/folio/converter.py)
   - [folio/tracking/registry.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/registry.py)
   - [folio/tracking/sources.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/sources.py)
   - [folio/tracking/versions.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/versions.py)

## Environment Guidance

Run this on the machine/environment that would actually be used as the
daily-driver workflow.

Use:

- the **real library** for real workflow checks
- a **sandbox library** only for destructive or failure-recovery tests

Do not mutate canonical source decks directly for validation.

## Time Budget

Target: 2 working days.

Prioritize evidence that can reveal real blockers quickly.

If a check is impossible in the time budget, mark it clearly as:

- `NOT COMPLETE`

Do not silently omit it.

## Phase 1: Accelerated Daily-Driver Loop Check

### Goal

Stress the full Tier 2 command loop in realistic usage over 2 days.

### Minimum Required Activity

During the accelerated window, do all of these:

- at least 3 real `folio convert` runs
- at least 1 meaningful `folio batch`
- at least 2 `folio status` checks in normal usage
- at least 1 real `folio scan`
- at least 1 real `folio refresh`
- at least 1 real `folio promote`

### What to Record

- command
- date/time
- what was being attempted
- whether it worked first try
- any manual workaround
- operator friction

### Failure Signals

Treat these as strong blocker evidence:

- registry drift/corruption
- misrouted output
- `refresh` acting on the wrong decks
- `promote` damaging metadata or history
- repeated need for manual repair

## Phase 2: Obsidian and Dataview Check

### Goal

Determine whether the library is practically usable as an Obsidian vault now.

### What to Verify

- vault opens cleanly
- converted markdown renders
- image links render
- Dataview queries in [obsidian_queries.md](../obsidian_queries.md) work or can
  be corrected with minor doc changes
- no recurring YAML/frontmatter issues appear

### Minimum Query Coverage

Check at least:

- `type`
- `subtype`
- `client`
- `engagement`
- `authority`
- `curation_level`
- `tags`
- `frameworks`
- `slide_types`

## Phase 3: Routing and Registry Integrity Check

### Goal

Find the highest-risk Tier 2 failures quickly.

### What to Verify

- missing `registry.json` bootstraps cleanly
- `status` remains usable and fast
- `scan` finds new/stale sources correctly
- `refresh` affects the intended decks only
- source mapping with empty and non-empty `target_prefix` works
- explicit `--target` still overrides mapping
- explicit `--client` / `--engagement` override inference where intended

### Minimum Required Evidence

Capture:

- 3 to 5 source-path -> output-path examples
- at least 1 registry bootstrap/recovery example
- at least 1 stale detection example
- at least 1 refresh example

## Phase 4: LLM Profile and Fallback Check

### Goal

Determine whether the Tier 2 LLM configuration is operationally usable.

### What to Verify

- route-based selection works in ordinary use
- explicit `--llm-profile` override works
- provider/model metadata remains visible in output provenance
- if transient fallbacks are configured, fallback activation works
- if fallbacks are not configured, mark fallback validation `N/A`

### Important Note

This is a Tier 2 operational check, not a re-run of full Tier 1 analysis
quality validation.

## Phase 5: Accelerated Decision

### Goal

Decide whether Tier 2 looks operationally solid enough to proceed with Tier 3
planning while the formal closeout remains open.

### Required Output Labels

For each official Tier 2 checklist item, mark:

- `PASS`
- `PARTIAL`
- `FAIL`
- `NOT COMPLETE`

Then give the final accelerated decision:

- `OPERATIONALLY READY; CONTINUE TIER 3 PLANNING, FULL TIER 2 CLOSEOUT STILL PENDING`
- `STAY IN TIER 2; BLOCKERS REMAIN`

## Required Artifacts

This accelerated run still follows the project validation artifact standard.

Produce:

- [docs/validation/tier2_accelerated_precloseout_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_accelerated_precloseout_report.md)
- [docs/validation/tier2_accelerated_precloseout_session_log.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_accelerated_precloseout_session_log.md)
- [docs/validation/tier2_accelerated_precloseout_chat_log.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_accelerated_precloseout_chat_log.md)
- [docs/validation/tier2_accelerated_precloseout_prompt.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_accelerated_precloseout_prompt.md)

If you create helper scripts, save them under:

- [tests/validation](/Users/jonathanoh/Dev/folio.love/tests/validation)

## Required Report Structure

### 1. Executive Summary

| Item | Status | Notes |
|------|--------|-------|
| Command loop | | |
| Obsidian / Dataview | | |
| Routing / registry | | |
| Promote | | |
| LLM profiles / fallback | | |
| Official 2-week criterion | `NOT COMPLETE` / other | |
| Accelerated decision | | |

### 2. Tier 2 Checklist Snapshot

Reproduce the 8 official Tier 2 exit criteria and mark each:

- `PASS`
- `PARTIAL`
- `FAIL`
- `NOT COMPLETE`

### 3. Operational Findings

Summarize:

- what worked
- what was awkward
- what would block real daily use

### 4. Blockers

If any blocker exists, list:

- exact issue
- impact
- whether it is a product blocker or just a docs/process gap

### 5. Recommendation

Choose exactly one:

- `OPERATIONALLY READY; CONTINUE TIER 3 PLANNING, FULL TIER 2 CLOSEOUT STILL PENDING`
- `STAY IN TIER 2; BLOCKERS REMAIN`

## What NOT to Do

- Do **not** claim full Tier 2 closeout from a 2-day run.
- Do **not** weaken or reinterpret the official 2-week criterion.
- Do **not** hide incomplete checks.
- Do **not** implement fixes during validation.
- Do **not** skip evidence collection because the run is accelerated.

## Final Rule

If the accelerated run is clean, you may recommend Tier 3 **planning** can
start while full Tier 2 closeout remains pending.

If real blockers appear, the correct answer is still:

- `STAY IN TIER 2`
