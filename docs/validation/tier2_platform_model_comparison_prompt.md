---
id: tier2_platform_model_comparison_prompt
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-22
---

# Task: Tier 2 Platform LLM Model Comparison Validation

## What You're Doing

This is **not** an implementation task. This is a **platform-level LLM model
comparison validation run** for the current shipped Folio runtime on `main`.

You are validating the live LLM execution surface that exists today inside
`folio convert`:

- Pass 1 slide analysis
- diagram extraction
- Pass 2 deep analysis

You are **not** evaluating:

- `folio ingest`
- future per-stage routing that is not yet implemented
- synthetic-only benchmark data
- manual one-off prompting outside the real pipeline

This run must preserve the original diagram-comparison quality bar from the
repo:

- real corpus
- gold-standard labels
- quality-first selection
- weighted rubrics
- stability checks
- confidence calibration where runtime signals exist

The key change is scope: this is no longer just a diagram-only comparison. It
must evaluate the **full live convert-time LLM surface** while still preserving
diagram rigor.

## Required Outputs

Produce these tracked artifacts in `docs/validation/` using the shared label
`tier2_platform_model_comparison`:

1. `tier2_platform_model_comparison_prompt.md`
2. `tier2_platform_model_comparison_report.md`
3. `tier2_platform_model_comparison_session_log.md`
4. `tier2_platform_model_comparison_chat_log.md`
5. `tier2_platform_model_comparison_annotation_rules.md`
6. `tier2_platform_model_comparison_corpus_manifest.md`
7. `tier2_platform_model_comparison_metrics.jsonl`

Artifact rules:

- The report is the decision document and must contain the final
  recommendations.
- The session log must be chronological and must include exact commands, exit
  codes, durations when known, and error text.
- The chat log must preserve the human-AI transcript when the platform allows
  export. If the platform does not allow export, include a decision-and-
  rationale substitute and state where the raw transcript actually lives.
- The annotation rules file is the locked schema and adjudication reference.
- The corpus manifest must use anonymized corpus IDs and must not paste raw
  client slide text into the repo.
- The metrics file must be machine-readable JSONL with one record per
  `(candidate_profile, corpus_item_id, stage, repetition)` tuple.

Required JSONL fields:

- `candidate_profile`
- `provider`
- `model`
- `corpus_item_id`
- `stage`
- `run_type`
- `repetition`
- `status`
- `metrics`
- `notes`

Use anonymized corpus identifiers in all committed artifacts. Do **not** commit
raw client images, transcript text, screenshots, or API keys.

## Final Deliverables And Required Conclusions

The final report must always produce exactly these five conclusions:

1. best Pass 1 profile/model
2. best diagram-stage profile/model
3. best Pass 2 profile/model
4. best interim single current-`main` `convert` default
5. exact code/config implications if the stage winners differ

Do not collapse the run into one generic “best model” statement. The
stage-by-stage recommendation is the primary output. The single current-`main`
recommendation is a compatibility layer for the runtime that exists today.

## Current Runtime Truths You Must Respect

Do not reopen or weaken these facts. Ground all evaluation design in the live
repo.

1. One selected `convert` profile currently drives all live LLM surfaces.
   Pass 1, diagram extraction, and Pass 2 do not yet have separate route
   selection in shipped code.

2. Diagram extraction currently supports only `architecture` and `data-flow`
   diagrams as positive extraction targets. Unsupported diagram types should
   abstain and remain review-visible, not be scored as normal extraction wins.

3. Diagram gating happens before `DiagramAnalysis` coercion. Pages whose Pass 1
   result is `data`, `appendix`, or `title` with no framework must stay plain
   `SlideAnalysis` and must not be treated as diagram extractions.

4. `diagram_max_tokens` is capped by the current hardened runtime. Do not use
   any older proposal assumption that exceeds the current ceiling or bypasses
   current truncation handling.

5. Mermaid generation is deterministic downstream rendering from the extracted
   graph, not a model-generated text artifact. Mermaid validity still matters
   for the diagram stage because model quality determines graph quality.

6. `_llm_metadata` persists provider/model/fallback provenance, but the normal
   CLI/frontmatter path does not persist a full token-usage report for every
   run. If token usage is needed, collect it via an untracked helper under
   `tmp/` or mark cost/token metrics unavailable.

7. `tools/diagram_iterate.py` exists for targeted diagnosis. It is not the
   primary scoring path.

## Read Before Doing Anything

Read these in order before building the corpus or inventorying candidates:

1. [diagram-extraction-checklist.md](/Users/jonathanoh/Dev/folio.love/docs/proposals/diagram-extraction-checklist.md)
2. [diagram-extraction-proposal-v2.md](/Users/jonathanoh/Dev/folio.love/docs/proposals/diagram-extraction-proposal-v2.md)
3. [strategic_direction_memo.md](/Users/jonathanoh/Dev/folio.love/docs/product/strategic_direction_memo.md)
4. [tier2_closeout_checklist.md](/Users/jonathanoh/Dev/folio.love/docs/validation/tier2_closeout_checklist.md)
5. [AGENTS.md](/Users/jonathanoh/Dev/folio.love/AGENTS.md)
6. Current runtime/code surface:
   - [config.py](/Users/jonathanoh/Dev/folio.love/folio/config.py)
   - [converter.py](/Users/jonathanoh/Dev/folio.love/folio/converter.py)
   - [analysis.py](/Users/jonathanoh/Dev/folio.love/folio/pipeline/analysis.py)
   - [diagram_extraction.py](/Users/jonathanoh/Dev/folio.love/folio/pipeline/diagram_extraction.py)
   - [frontmatter.py](/Users/jonathanoh/Dev/folio.love/folio/output/frontmatter.py)
   - [diagram_iterate.py](/Users/jonathanoh/Dev/folio.love/tools/diagram_iterate.py)
   - [test_diagram_rendering.py](/Users/jonathanoh/Dev/folio.love/tests/test_diagram_rendering.py)

Do not start from the original diagram plan alone. Start from the merged
runtime.

## Environment And Secret Handling

Use the machine that has:

- the real engagement corpus
- working provider credentials
- the current Folio checkout

For API keys:

- use `tests/validation/.env`
- do not commit it
- delete it immediately after the run

If real engagement material cannot be used on the current machine, stop after
preflight and record a blocker. Do **not** substitute public or synthetic data
and pretend the run is complete.

## Stage 1: Preflight And Gated Setup

### Goal

Build the candidate set, corpus manifest, and annotation protocol. Do not begin
scored execution until this stage is complete and reviewed.

### Candidate Profile Inventory

Load the local `folio.yaml` and inventory named LLM profiles.

Selection rules:

1. Always include the profile resolved by `routing.convert.primary`.
2. Add distinct profiles from other providers when available.
3. Prefer frontier/high-capability profiles over smaller or cheaper variants if
   multiple options exist from the same provider.
4. Keep the scored set to 3-5 usable profiles.
5. Record skipped configured profiles and why they were skipped.
6. If fewer than 3 usable profiles remain, stop after preflight and record a
   blocker.

For each chosen candidate, record:

- profile name
- provider
- model
- credential env var
- whether preflight suggests it is usable
- whether it is the current default for `convert`

Do not hardcode “latest” model names into the report without checking the local
config and actual runtime identity.

### Corpus Manifest Requirements

Build a real-corpus manifest of 36-45 unique slides using anonymized IDs.

Required composition:

- 18-24 diagram or mixed pages
- 18-21 non-diagram pages
- at least 12 non-diagram pages that actually trigger Pass 2 in the current
  runtime

Required control cases:

- supported `architecture` diagram
- supported `data-flow` diagram
- unsupported diagram types that should abstain
- mixed pages
- Pass-1-gated diagram-like pages that should stay plain `SlideAnalysis`

Also include a spread of:

- simple, medium, and dense diagrams
- text-heavy and framework-heavy consulting slides
- pages likely to stress Pass 2
- pages with clear grounding quotes
- pages where the correct outcome is abstention or skip behavior

If Pass 2 eligibility is not directly obvious from existing outputs, you may
create an untracked helper under `tmp/` that runs the current density and skip
logic to identify candidate slides. Do not patch repo-tracked runtime code for
this.

### Preflight Checkpoint

At the end of Stage 1, present a preflight package to the operator containing:

- candidate inventory
- corpus manifest
- blocker list
- planned annotation workload
- any environment gaps

Do not start Stage 2 until the operator confirms the preflight package is
acceptable.

## Stage 2: Gold Standard And Annotation Rules

### Goal

Lock the annotation schema before scored runs start.

### Calibration

Create a 10-slide calibration subset spanning all three behaviors:

- Pass 1-only analysis
- diagram extraction
- Pass 2 augmentation

Dual-annotate the full calibration subset. Adjudicate disagreements and update
the annotation rules file until the schema is stable.

Only after that may the remaining corpus be annotated.

### Required Annotation Schema

Every scored slide must end with an adjudicated final label set.

For diagram pages, annotate:

- expected stage classification
- supported vs unsupported outcome
- abstain vs non-abstain outcome
- expected review-required state
- node set
- edge set
- edge direction
- containment/grouping structure
- any acceptable alternate labels if normalization is needed

For Pass 1 slides, annotate:

- gold `slide_type`
- gold `framework`
- atomic key facts
- one-sentence main insight
- acceptable grounding quotes

For Pass 2 slides, annotate:

- additional evidence that should appear beyond Pass 1
- correct `slide_type` reassessment or `unchanged`
- correct `framework` reassessment or `unchanged`

Atomic-fact rules:

- break key facts into comparable units
- do not score whole paragraphs as one fact
- normalize number formatting before comparison

Grounding-quote rules:

- list 1-5 acceptable quote snippets per slide when possible
- treat minor whitespace and punctuation variation as equivalent
- do not count paraphrases as exact-quote matches

Record the locked rules in
`tier2_platform_model_comparison_annotation_rules.md`. Do not silently change
the schema mid-run.

### Calibration Checkpoint

Before Stage 3 begins, present:

- the locked annotation rules
- the adjudicated calibration subset
- any rule ambiguities that remain

If ambiguities still materially affect scoring, stop and resolve them before
continuing.

## Stage 3: Scored Execution Protocol

### Core Rule

Score the real end-to-end pipeline, not manual prompting.

Primary scored command pattern:

```bash
folio convert <source> --passes 2 --llm-profile <profile> --no-cache --target <isolated_target>
```

Run isolation requirements:

- each candidate gets a fresh target root
- each repetition gets a fresh target root
- no cache reuse between candidates
- no frozen-note reuse
- no reuse of prior validation outputs as score inputs

### Stability Runs

Create a 10-slide stability subset drawn from the main corpus with coverage
across:

- Pass 1
- diagram extraction
- Pass 2
- at least one control case

Run that subset three times per candidate and score output consistency.

### Targeted Diagnosis

Use [diagram_iterate.py](/Users/jonathanoh/Dev/folio.love/tools/diagram_iterate.py)
only after the scored runs identify a stage failure or material discrepancy.
Use it to explain failures, not to replace the main scoring path.

### Mermaid Validity

Validate Mermaid with the real repo harness when Mermaid is present:

```bash
npm --prefix tests/mermaid ci
printf '%s' "$MERMAID_TEXT" | node tests/mermaid/validate.mjs
```

If the Mermaid harness is unavailable on the machine, mark Mermaid parse
validation unavailable and record it explicitly. Do not claim Mermaid validity
without testing it.

### Token Usage And Cost

If current frontmatter/CLI output does not expose exact token usage, you may:

- create an untracked helper under `tmp/`
- capture provider-returned usage during the run
- roll those numbers into the JSONL metrics file

If you cannot recover exact usage cleanly, mark token and cost metrics
`unavailable` and continue with the quality-first comparison. Do not invent
estimates.

## Stage 4: Scoring Rubrics

### Pass 1 Rubric

Weights:

- classification: 25
- key facts and insight: 30
- grounding and evidence quality: 30
- stability and failure rate: 10
- latency and cost: 5

Required metrics:

- slide-type accuracy
- framework accuracy
- key-fact precision
- key-fact recall
- main-insight faithfulness
- evidence-quote precision
- evidence-quote recall
- grounding-validation rate
- pending/parse-failure rate

Scoring rules:

- compare `slide_type` and `framework` as exact normalized labels
- score key facts at the atomic-fact level
- score main insight against the gold one-sentence summary on factual
  faithfulness first, coverage second
- score evidence quotes only against the acceptable-quote set from the
  annotation rules

### Diagram Rubric

Weights:

- graph accuracy: 60
- abstention/review correctness: 15
- Mermaid validity: 10
- stability: 10
- latency and cost: 5

Required metrics:

- node precision
- node recall
- edge precision
- edge recall
- edge direction accuracy
- abstention correctness
- review-flag correctness
- Mermaid validity
- confidence calibration where `diagram_confidence` is available

Scoring rules:

- compare nodes and edges after label normalization, not by transient internal
  IDs alone
- unsupported diagrams are scored on correct abstention/review behavior, not as
  failed positive extractions
- Pass-1-gated control pages are scored on correct skip behavior
- Mermaid validity is binary per page when Mermaid is emitted
- confidence calibration must compare confidence buckets against actual diagram
  accuracy; if sample size is too small, record calibration as low-confidence
  evidence rather than forcing a claim

### Pass 2 Rubric

Weights:

- incremental evidence lift: 40
- reassessment accuracy: 25
- grounding quality: 20
- stability and failure rate: 10
- latency and cost: 5

Required metrics:

- incremental evidence precision over Pass 1
- incremental evidence recall over Pass 1
- slide-type reassessment accuracy
- framework reassessment accuracy
- net lift versus Pass 1 baseline
- pending/parse-failure rate

Scoring rules:

- score only the new evidence contributed by Pass 2, not evidence already
  present from Pass 1
- treat `unchanged` as a real target label
- net lift must capture whether Pass 2 improves the final evaluated output over
  the Pass 1 baseline, not just whether it emits more text

## Stage 5: Selection Rules

Choose the stage winner by the weighted rubric score for that stage.

If the top two candidates are within 3 points on the stage score, break ties in
this order:

1. lower failure/pending rate
2. better stability
3. lower latency
4. lower cost

Derive the interim single current-`main` `convert` recommendation from this
aggregate weighting:

- Pass 1: 50
- diagram stage: 30
- Pass 2: 20

The stage-by-stage recommendation remains the primary conclusion even if the
single current-`main` recommendation differs.

If the stage winners differ, the final report must document:

- exactly which stages want different profiles
- why
- what current runtime limitation forces a compromise
- what config/code changes would be required to realize the stage-specific
  recommendation

Do **not** write the follow-up implementation spec in this run. Only document
the implications clearly.

## Blockers And Stop Conditions

Stop after preflight and mark the run blocked if any of these are true:

- fewer than 3 usable candidate profiles
- no real engagement corpus available
- no human annotators available
- unresolved annotation ambiguity makes the rubric unstable
- the machine cannot run the real pipeline needed for scoring

If blocked:

- still write the prompt artifact
- still write the session log
- still write the chat log or substitute
- still write a report that explains what blocked the run

Do not fake completion.

## Hard Prohibitions

- Do not weaken the rubric after seeing results.
- Do not replace real corpus with synthetic slides.
- Do not manual-prompt providers outside the real pipeline and count that as a
  scored result.
- Do not reuse stale caches or frozen outputs for scoring.
- Do not commit API keys.
- Do not commit raw client content into repo-tracked artifacts.
- Do not claim unsupported diagrams should have extracted as supported pages.
- Do not claim Pass-1-gated pages are diagram misses; they are control cases.
- Do not invent token or cost figures when the runtime does not expose them.

## Definition Of A Good Final Report

A correct final report is decision-ready for another engineer or the Chief
Architect. It should let a reader answer all of these without reading the raw
chat:

- What was compared?
- On what corpus?
- Under what exact runtime conditions?
- Which profile won Pass 1?
- Which profile won diagrams?
- Which profile won Pass 2?
- What is the best interim single default on current `main`?
- What breaks if we try to route by stage today?
- What evidence supports those claims?

If the report cannot answer those questions cleanly, the run is incomplete.
