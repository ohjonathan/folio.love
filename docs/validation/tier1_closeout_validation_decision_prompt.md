# Task: Tier 1 Closeout Validation and Decision Gate

## What You're Doing

This is **not** an implementation task. This is a focused closeout gate before
Tier 2 begins.

Tier 1 has already made major progress:

- PR #8 shipped multi-provider LLM support
- PR #10 improved managed-mac PowerPoint reliability
- PR #12 fixed the PowerPoint sandbox staging-dir problem
- the March 2026 rerun achieved `50/50` automated PPTX conversion on the real
  corpus, with `49/50` clean output and one documented template-only edge case

However, four Tier-1-adjacent items still require explicit validation or a
decision before proceeding to Tier 2:

1. **OneDrive / cross-machine portability**
2. **Same-PDF cache rerun validation**
3. **`building_blocks` policy decision**
4. **`Approach J` decision** for automated-PPTX cache persistence

Your job is to validate the first two and make a recommendation on the second
two. The output of this prompt is a decision package for the Chief Architect.

## Current Baseline

Work from the current `main` branch baseline reflected in these docs:

- [docs/product/04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md)
- [docs/validation/tier1_rerun_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_rerun_report.md)
- [docs/validation/tier1_rerun_session_log.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_rerun_session_log.md)
- [docs/proposals/renderer_and_cache_fix_proposal.md](/Users/jonathanoh/Dev/folio.love/docs/proposals/renderer_and_cache_fix_proposal.md)

Important current truths:

- Managed-mac automated PPTX conversion is now working on the real 50-deck
  corpus.
- Cross-machine portability is **not yet tested**.
- Same-PDF cache reruns are expected to work, but were **not tested** during
  the main rerun.
- Automated-PPTX rerun cache persistence remains a **known deferred
  limitation** unless a follow-on (for example, `Approach J`) is promoted.
- `building_blocks` remains a documented edge case: it converted, but one
  placeholder slide produced pending analysis despite executed LLM metadata.

## Read Before Doing Anything

Read these in order:

1. [docs/product/04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md)
   Focus on:
   - March 2026 status update
   - Tier 1 exit criteria
   - current status table

2. [docs/validation/tier1_rerun_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_rerun_report.md)
   Focus on:
   - `building_blocks`
   - same-PDF cache not tested
   - cross-machine portability not tested

3. [docs/validation/tier1_rerun_session_log.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_rerun_session_log.md)
   Focus on:
   - exact environment used
   - staleness/version validation method

4. [docs/proposals/renderer_and_cache_fix_proposal.md](/Users/jonathanoh/Dev/folio.love/docs/proposals/renderer_and_cache_fix_proposal.md)
   Focus on:
   - accepted automated-PPTX cache limitation
   - `Approach J`

5. Current runtime/code surface:
   - [folio/cli.py](/Users/jonathanoh/Dev/folio.love/folio/cli.py)
   - [folio/converter.py](/Users/jonathanoh/Dev/folio.love/folio/converter.py)
   - [folio/pipeline/normalize.py](/Users/jonathanoh/Dev/folio.love/folio/pipeline/normalize.py)
   - [folio/pipeline/analysis.py](/Users/jonathanoh/Dev/folio.love/folio/pipeline/analysis.py)
   - [folio/pipeline/images.py](/Users/jonathanoh/Dev/folio.love/folio/pipeline/images.py)
   - [folio/tracking/sources.py](/Users/jonathanoh/Dev/folio.love/folio/tracking/sources.py)

## Phase 1: OneDrive / Cross-Machine Portability Validation

### Goal

Determine whether Folio conversions remain usable and correctly tracked when
the library is opened from a OneDrive-synced location on another machine or an
equivalent second synced path.

### Required Test Setup

Use one of these setups:

1. **Best:** actual second machine with the same library synced via OneDrive
2. **Acceptable fallback:** second synced root on the same machine that mimics
   the real relative-path and sync behavior closely enough to test path
   resolution

If neither is possible, stop and record `NOT TESTED` with the blocking reason.

### Minimum Test Corpus

Use at least:

- 3 previously converted PPTX decks from the March rerun corpus
- 1 deck that has version history
- 1 deck with many slides
- 1 deck with spaces/special characters in file or directory names

### What to Verify

For each selected deck:

- markdown opens successfully from the synced library location
- image links still resolve/render
- `source` frontmatter path still resolves correctly
- `folio status` reports the expected current/stale state from the synced
  environment
- changing a source file and rerunning `folio status` still marks the correct
  deck stale
- re-converting from the synced environment still works

### Required Evidence

Capture:

- exact library path(s) used
- exact source path(s) used
- command lines
- failures, if any
- whether failures are path-related, permission-related, or sync-latency-related

### Decision Rule

- If source links, stale detection, or re-conversion break under synced-path
  conditions, this is a **Tier-1 closeout blocker**.
- If the synced-path test passes, mark portability as closed for Tier 1.

## Phase 2: Same-PDF Cache Validation

### Goal

Validate the cache behavior that should work today: rerunning the **same PDF**
with no content change.

This is distinct from automated-PPTX rerun caching, which remains a known
deferred limitation.

### Test Corpus

Use 3-5 stable PDFs:

- Prefer PDFs already produced and retained from real decks
- If needed, manually export a small representative subset of decks to
  slides-only PDF

Do **not** count this as Tier 1 automated PPTX validation. This is a closeout
verification for the supported same-PDF path.

### Required Runs

1. Initial conversion:

```bash
folio batch <pdf_dir> --pattern "*.pdf" --passes 1
```

2. Unchanged rerun:

```bash
folio batch <pdf_dir> --pattern "*.pdf" --passes 1
```

Optional:

3. Provider/model change rerun, if you want to confirm invalidation still works

### What to Verify

- second run produces cache hits on unchanged PDFs
- runtime is materially faster on the second run
- outputs are unchanged except for expected timestamps/version metadata
- no silent reanalysis of unchanged slides
- cache behavior still invalidates correctly if provider/model changes

### Decision Rule

- If unchanged same-PDF reruns do **not** hit cache, treat this as a
  **Tier-1 closeout blocker** until explicitly waived.
- If unchanged same-PDF reruns behave correctly, close this validation item and
  keep automated-PPTX cache persistence deferred separately.

## Phase 3: `building_blocks` Decision

### Goal

Decide whether the `building_blocks` result is:

1. an acceptable template-only edge case,
2. a validation-exclusion candidate for future strict gate runs, or
3. a real product bug that should be fixed before Tier 2.

### Required Review

Inspect:

- the source deck
- the converted markdown
- frontmatter / `_llm_metadata`
- whether the deck is meaningful business content or just placeholders/template
  scaffolding

### Required Recommendation

Choose exactly one:

- `ACCEPT + DOCUMENT`
- `EXCLUDE FROM STRICT FUTURE CORPUS COUNTING`
- `FIX BEFORE TIER 2`

You must justify the choice in terms of product behavior, not aesthetics.

## Phase 4: `Approach J` Decision

### Goal

Decide whether `Approach J` should remain deferred or be promoted ahead of Tier
2.

`Approach J` is the image-artifact reuse follow-on that stabilizes
automated-PPTX cache persistence without redesigning cache keys.

### Required Inputs

Review:

- [docs/proposals/renderer_and_cache_fix_proposal.md](/Users/jonathanoh/Dev/folio.love/docs/proposals/renderer_and_cache_fix_proposal.md)
  (`Approach J` sections)
- current `images.py`
- current `analysis.py`
- current roadmap status

### Required Recommendation

Choose exactly one:

- `DEFER TO POST-TIER-2`
- `PROMOTE BEFORE TIER 2`
- `PROMOTE ONLY IF SAME-PDF CACHE VALIDATION FAILS`

Your reasoning must cover:

- user pain / operator cost
- expected implementation effort
- impact on LLM spend
- whether the limitation materially blocks Tier 2 daily-driver usage

## Output

Save the final decision package to:

- [docs/validation/tier1_closeout_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_closeout_report.md)

If you create helper scripts, save them under:

- [tests/validation](/Users/jonathanoh/Dev/folio.love/tests/validation)

## Required Report Structure

### 1. Executive Summary

| Item | Status | Recommendation |
|------|--------|----------------|
| OneDrive portability | | |
| Same-PDF cache validation | | |
| `building_blocks` | | |
| `Approach J` | | |

### 2. OneDrive / Cross-Machine Validation

- setup
- commands run
- results
- failures
- final pass/fail

### 3. Same-PDF Cache Validation

- corpus used
- commands run
- first-run vs second-run behavior
- cache evidence
- final pass/fail

### 4. `building_blocks` Decision

- what was inspected
- what the actual issue is
- final recommendation

### 5. `Approach J` Decision

- current limitation restated
- cost/benefit assessment
- final recommendation

### 6. Tier 2 Go/No-Go

Choose exactly one:

- `GO TO TIER 2`
- `GO TO TIER 2 WITH EXPLICIT KNOWN LIMITATIONS`
- `NO-GO — CLOSEOUT WORK REMAINS`

If `NO-GO`, list the exact blocking items.

## What Not To Do

- Do **not** change Folio code while running this prompt
- Do **not** re-run the full 50-deck automated PPTX gate unless a closeout item
  fails in a way that makes a full rerun necessary
- Do **not** count PDF validation results as automated PPTX Tier 1 results
- Do **not** overwrite the March rerun report or session log
- Do **not** soften the decision language; every item must end in a clear
  close/defer/fix recommendation
