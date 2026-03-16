# Task: Tier 1 Validation Rerun on Current `main`

## What You're Doing

This is a validation gate for the current shipped baseline on `main`, not an implementation task.

You are re-running Folio against a real 50-deck consulting corpus to determine whether Tier 1 now holds on the current codebase:

- automated PPTX conversion on managed macOS
- zero silent failures
- valid ontology-complete frontmatter
- trustworthy slide images, text, and analysis
- working version/staleness behavior

This prompt supersedes the older `v0.1` validation prompt that assumed:

- the old AppleScript-only PowerPoint open path
- no dedicated-session restart behavior
- pre-PR #8 single-provider assumptions
- automated-PPTX reconversion cache persistence as an immediate gate check

Those assumptions are no longer accurate on `main`.

## Current Baseline You Are Validating

The current validation target includes these shipped changes:

- PR #1: Source grounding and multi-pass extraction
- PR #2: Core extraction hardening
- PR #3: Analysis caching hardening
- PR #5: Version tracking
- PR #6: Frontmatter v2 completeness
- PR #8: Multi-provider LLM support
- PR #10: PPTX renderer reliability mitigation on managed macOS

Important current boundaries:

- Tier 1 requires **fully automated PPTX conversion**.
- Manual/operator-exported PDFs are **mitigation-only** and do **not** count toward the 50-deck Tier 1 gate.
- Automated-PPTX reconversion cache persistence is still a known limitation unless a separate follow-on lands; do not treat it as silently fixed.
- Same-PDF reruns are still valid for cache verification on the PDF mitigation path.

### Gate Definition

For this rerun, a full Tier 1 `PASS` means:

- the same real 50-deck corpus is attempted through the automated PPTX path
- all 50 decks convert through the automated PPTX path
- zero silent failures occur across those automated conversions

This is intentionally strict because it matches the roadmap wording: `50 real decks converted with zero silent failures`.

Do **not** reinterpret the gate as:

- "zero silent failures across only the subset that converted", or
- "Tier 1 passes if enough decks convert and the rest can use PDF mitigation"

Those are useful observations, but they are not full Tier 1 closure.

## Phase 1: Read and Understand

Read these in order before running anything:

1. [docs/product/04_Implementation_Roadmap.md](/Users/jonathanoh/Dev/folio.love/docs/product/04_Implementation_Roadmap.md)
   Focus on:
   - Tier 1 exit criteria
   - current March 2026 shipped baseline note

2. [docs/architecture/Folio_Ontology_Architecture.md](/Users/jonathanoh/Dev/folio.love/docs/architecture/Folio_Ontology_Architecture.md)
   This is the schema you will validate output against.

3. Historical baseline:
   - [docs/validation/tier1_validation_report.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_validation_report.md)
   - [docs/validation/tier1_session_log.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_session_log.md)

4. Current rerun guidance:
   - [docs/validation/tier1_rerun_guide.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier1_rerun_guide.md)
   - [docs/proposals/renderer_and_cache_fix_proposal.md](/Users/jonathanoh/Dev/folio.love/docs/proposals/renderer_and_cache_fix_proposal.md)

5. Current runtime surface:
   - [folio/cli.py](/Users/jonathanoh/Dev/folio.love/folio/cli.py)
   - [folio/converter.py](/Users/jonathanoh/Dev/folio.love/folio/converter.py)
   - [folio/pipeline/normalize.py](/Users/jonathanoh/Dev/folio.love/folio/pipeline/normalize.py)
   - [folio/pipeline/analysis.py](/Users/jonathanoh/Dev/folio.love/folio/pipeline/analysis.py)

You need to understand:

- `folio batch <directory>` for automated PPTX runs
- `folio batch <directory> --pattern "*.pdf"` for mitigation-only PDF runs
- `--dedicated-session/--no-dedicated-session`
- `--passes 1|2`
- `folio status [scope]` and the fact that `scope` is library-relative, not a source-corpus path
- where output goes (`library_root`)
- what batch output now reports

## Phase 2: Environment and Corpus Setup

### 2.1 Environment Requirements

Run the automated PPTX validation only in an environment that matches the managed-mac production constraint:

- macOS managed laptop
- Microsoft PowerPoint installed
- Terminal.app has PowerPoint automation permission
- run from Terminal.app, not Cursor or another terminal lacking TCC permission
- use a dedicated PowerPoint session with no unrelated presentations open
- use the current project virtualenv / installed Folio environment
- use real LLM credentials if available

If any of these are false, record that as a validation limitation before proceeding.

### 2.2 Corpus Rules

For the official Tier 1 gate, use **50 real decks**.

Preferred order:

1. Reuse the original March 2026 50-deck corpus if available.
2. If that exact corpus is unavailable, use a new real 50-deck corpus with comparable diversity and document the substitution.
3. Do **not** use generated decks to satisfy the official Tier 1 gate.

Generated decks are acceptable only for:

- preflight debugging
- narrow reproduction of a known failure mode
- future regression tests

They are not acceptable as replacements for the 50-real-deck gate corpus.

### 2.3 Corpus Identity

Before running the batch, record only what matters to gate interpretation:

- corpus root path
- whether this is the exact March 2026 corpus or a substitute real corpus
- number of decks
- any substitutions or exclusions

If the corpus includes PDFs, classify them separately:

- native PDFs
- operator-exported mitigation PDFs

Do not let mitigation PDFs inflate the automated PPTX Tier 1 count.

## Phase 3: Preflight Reruns

Before the full 50-deck gate run, do two targeted reruns.

### 3.1 Targeted FM1 Rerun: Prior `-9074` Cohort

Re-run the previously failing `-9074` files from Terminal.app using the current automated PPTX path.

Capture:

- stdout/stderr
- per-file result
- renderer reported
- duration
- whether any permission dialog appears

Minimum questions to answer:

- how many of the previously failing files now succeed?
- do any still fail with `-9074`?
- are failures clustered by file type or template family?
- does the batch output identify the renderer actually used?

Hard gate:

- If any of the original consistently failing `-9074` files still fail consistently on the same corpus, a full `50/50` automated Tier 1 `PASS` is no longer achievable on that corpus.
- In that case, stop and record a `preflight no-go` unless you explicitly continue for regression/comparison data.

### 3.2 Fatigue Rerun: 30+ Deck Automated Batch

Run a 30+ deck PPTX batch in dedicated-session mode.

Verify:

- preemptive restart occurs
- batch continues after restart
- no dead-on-arrival PowerPoint phase
- no manual intervention is required during the run

This is an automation check, not a quality check.

Hard gate:

- If the fatigue rerun still requires manual intervention, still deadlocks, or still collapses after restart automation, stop and record a `preflight no-go` unless you explicitly continue for deeper debugging data.

## Phase 4: Full Validation Runs

### 4.1 Automated PPTX Single-Pass Tier 1 Run

Run the full automated PPTX corpus:

```bash
folio batch <corpus_directory> --pattern "*.pptx" --passes 1 --dedicated-session
```

Capture:

- full stdout/stderr to a log
- exit code
- wall clock time
- per-file outcome
- restart events
- warnings

For each failed deck, classify:

- AppleScript / PowerPoint error code if available
- timeout
- unknown normalization failure
- downstream extraction / analysis failure

### 4.2 Automated PPTX Two-Pass Run

Run:

```bash
folio batch <corpus_directory> --pattern "*.pptx" --passes 2 --dedicated-session
```

Capture the same data plus:

- which decks/slides triggered Pass 2
- whether Pass 2 changes evidence volume materially
- whether Pass 2 introduces regressions in grounding or frontmatter accounting

### 4.3 PDF Mitigation Run (Non-Tier-1)

If you have operator-exported PDFs for still-unconvertible decks, run them separately:

```bash
folio batch <pdf_directory> --pattern "*.pdf" --passes 1
```

This run is useful, but it is **not** Tier 1 counting.

Capture separately:

- success/failure counts
- portrait-PDF warnings
- scanned-PDF warnings
- frontmatter validity
- cache hit behavior on same-PDF rerun

Do not merge these results into the automated PPTX Tier 1 numerator.

### 4.4 Cache Validation

Split cache validation into the two paths that currently exist.

#### A. Automated PPTX reconversion

You may still run a second unchanged PPTX batch and record cache behavior, but do **not** assume current `main` should deliver cross-reconversion cache hits for unchanged PPTX decks.

Record:

- observed hit/miss behavior
- whether hits occur only within a run vs across reruns
- whether behavior matches the current known limitation

This is an observation item, not an automatic Tier 1 fail by itself.

In the final report, state this explicitly if confirmed:

- caching works for stable same-PDF reruns
- automated-PPTX cross-rerun cache persistence remains a known accepted Tier 1 limitation on the current baseline

#### B. Same-PDF rerun cache validation

For stable PDF inputs, run the same PDF batch twice:

```bash
folio batch <pdf_directory> --pattern "*.pdf" --passes 1
folio batch <pdf_directory> --pattern "*.pdf" --passes 1
```

Verify:

- second run hits cache
- no unexpected API calls
- output remains structurally identical
- rerun is materially faster

### 4.5 Staleness / Version Tracking Validation

Use converted output in the library, not the source corpus directory.

Do **not** edit the canonical 50-deck gate corpus in place.

Instead:

1. Copy 3-5 source decks to a scratch validation directory outside the canonical corpus.
2. Convert those copied decks into a separate validation scope or scratch library target.
3. Modify only the copied decks.

Then modify the copied decks deliberately:

- edit slide text
- add a slide
- remove a slide

Then run:

```bash
folio status
```

or, if applicable:

```bash
folio status <client-or-engagement-scope>
```

Verify:

- modified decks show as stale
- unmodified decks remain current

Then rerun conversion on the modified subset and verify:

- versions increment
- `id` and `created` are preserved
- `converted` and `modified` update correctly
- unchanged decks are not re-analyzed unnecessarily

## Phase 5: Validate Output Quality

For every converted deck, validate the actual output files.

Create fresh validation artifacts under `tests/validation/` for this rerun if needed. Do not overwrite the historical March 2026 report/log.

### 5.1 Frontmatter Validation

Write or refresh a validation script that checks:

1. YAML is parseable
2. all required ontology fields are present
3. field types are correct
4. allowed enum values are valid
5. `grounding_summary` is present and internally consistent
6. version/source/staleness fields are present and well-formed
7. `_llm_metadata` remains internal metadata, not schema drift

### 5.2 Markdown Structure Validation

Check for each output:

1. slide sections present
2. analysis blocks present
3. evidence blocks present
4. image references exist
5. file is not truncated
6. pass-2 evidence formatting is counted correctly if present

### 5.3 Silent Failure Detection

A silent failure is still the main gate.

For each automated PPTX deck, check:

1. slide count in output matches source
2. every slide has image, text, and non-empty analysis
3. evidence validation rate is plausible for the deck type
4. no repeated analysis indicating extraction/cache corruption
5. `grounding_summary.total_claims` matches the evidence count in body
6. no deck exits `0` with structurally incomplete output

Also record any mitigation-only PDF decks that convert successfully but are low-trust:

- scanned PDFs with no usable text layer
- likely notes-page PDFs
- handout-layout PDFs

These are not silent failures if the warning is loud and output is classified correctly, but they are still quality findings.

## Phase 6: Report the Results

Write a new rerun report. Do not overwrite the original historical baseline files.

Recommended output files:

- `docs/validation/tier1_rerun_report.md`
- `docs/validation/tier1_rerun_session_log.md`
- `tests/validation/validate_frontmatter.py`
- `tests/validation/<any corpus or helper scripts used>`

### 6.1 Summary Table

Include, at minimum:

| Metric | Value |
|--------|-------|
| Total real decks in automated PPTX corpus | |
| Automated PPTX successes | |
| Automated PPTX failures | |
| Silent failures | |
| Total slides processed | |
| Frontmatter validation pass rate | |
| Average evidence validation rate | |
| Pass 2 decks | |
| Staleness detection accuracy | |
| Same-PDF cache hit rate | |
| Automated-PPTX rerun cache behavior | |

### 6.2 Separate Automated vs Mitigation Results

Report these separately:

- automated PPTX Tier 1 results
- operator-assisted PDF mitigation results

Do not combine them.

### 6.3 Failure Catalog

For every failure:

| # | Deck | Failure Type | Description | Severity | Slide(s) | Reproducible? |
|---|------|-------------|-------------|----------|-----------|---------------|

Failure types:

- Crash
- Error
- Silent-Wrong-Output
- Silent-Missing-Content
- Silent-Malformed-Frontmatter
- Silent-Invalid-YAML
- Performance
- Mitigation-Only Warning

### 6.4 Tier 1 Gate Decision

Evaluate these separately:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 50 real decks converted via automated PPTX path | PASS / FAIL | |
| Zero silent failures on automated PPTX conversions | PASS / FAIL | |
| Every converted slide has image, text, and analysis | PASS / FAIL | |
| Frontmatter matches Ontology v2 | PASS / FAIL | |
| Version/staleness behavior works | PASS / FAIL / PARTIAL | |
| Managed-mac batch automation works without user intervention | PASS / FAIL / PARTIAL | |
| Same-PDF cache rerun works | PASS / FAIL / NOT TESTED | |
| Automated-PPTX rerun cache behavior | OBSERVED / DEFERRED / REGRESSED | |
| Cross-machine portability | PASS / FAIL / NOT TESTED | |

Overall decision:

- `PASS`
- `FAIL`
- `CONDITIONAL PASS`

If `FAIL`, list the exact blockers to rerun.

If `CONDITIONAL PASS`, distinguish:

- acceptable known limitations
- issues that still block Tier 1

Interpret the automated-PPTX cache row this way:

- `DEFERRED`: behavior matches the known current limitation from the March 2026 baseline
- `REGRESSED`: behavior is materially worse than the March 2026 baseline and must be called out as a concrete finding, even if it does not independently fail the Tier 1 gate
- `OBSERVED`: rerun captured behavior but it does not fit cleanly into the prior two cases; explain why

### 6.5 Delta vs March 2026 Baseline

Add an explicit side-by-side comparison against the original March 2026 run.

At minimum, compare:

| Metric | March 2026 Baseline | Current Rerun | Delta |
|--------|----------------------|---------------|-------|
| Automated PPTX successes | | | |
| Automated PPTX failures | | | |
| Consistent `-9074` failures fixed | | | |
| Fatigue behavior | | | |
| Silent failures | | | |
| Frontmatter validation pass rate | | | |
| Average evidence validation rate | | | |
| Pass 2 decks | | | |
| Same-PDF cache behavior | | | |
| Previously passing decks that regressed | | | |

Also answer plainly:

- How many of the original 18 failures are now fixed?
- Did any decks that passed in March now fail?
- Did evidence validation rates materially improve or worsen?
- Did batch automation materially improve?

## What Not to Do

- Do **not** fix bugs during validation
- Do **not** overwrite the original March 2026 validation report/log
- Do **not** count operator-exported PDFs toward the Tier 1 automated gate
- Do **not** use generated decks as substitutes for the 50-real-deck gate corpus
- Do **not** run the automated PPTX gate from a terminal environment that lacks PowerPoint automation permission
- Do **not** treat automated-PPTX cache misses on unchanged reruns as a surprise if the deferred follow-on has not landed
- Do **not** lower the silent-failure bar; one silent failure still fails the gate
- Do **not** use mocked API calls if real credentials are available
- Do **not** continue to the full 50-deck run blindly if the preflight reruns already prove a `50/50` automated PASS is impossible on the same corpus

## Final Deliverable

Produce a rerun report that answers one question clearly:

**On the current shipped baseline, does Folio now pass the Tier 1 automated PPTX gate on a real 50-deck corpus with zero silent failures?**

Everything else in the report should support that answer.
