---
id: folio_model_evaluation_methodology
type: reference
subtype: methodology
status: active
created: 2026-03-22
source: codex
concepts: [llm-evaluation, model-comparison, validation, methodology]
---

# Folio Model Evaluation Methodology

This document records the current Folio methodology for recurring model
comparison. It is the stable framework behind comparison prompts, not a
replacement for run-specific validation prompts.

Two things are true at once:

1. The methodology should stay stable enough to reuse across runs.
2. The prompt for any individual run must be regenerated from current runtime
   truth, not copied forward unchanged.

The current worked example for this methodology is
`docs/validation/tier2_platform_model_comparison_prompt.md`.

## Why This Exists

Folio needs recurring model comparison because both sides of the system move:

- frontier models and provider offerings change frequently
- Folio's shipped LLM surface changes as new capabilities land

The project direction already assumes that model evaluation is ongoing and
should be formalized. This document is that formalization for the current
state of the platform.

The purpose is not to freeze one prompt forever. The purpose is to preserve the
method that future prompts should inherit.

## Stable Methodology

### Current Methodology Scope

The current model-comparison methodology evaluates the live LLM execution
surface that exists today inside `folio convert`:

- Pass 1 slide analysis
- diagram extraction
- Pass 2 deep analysis
- aggregate interim recommendation for the current single-route runtime

This means the comparison is broader than the original diagram-only idea, but
it is still grounded in the shipped runtime rather than future architecture.

Current scope boundaries:

- Text and content quality are evaluated through Pass 1 and Pass 2.
- Numbers are evaluated only insofar as they appear in key facts, `key_data`,
  main insight, and grounding evidence.
- Tables are only partially covered today through generic text/content scoring
  and existing table-like heuristics in the runtime.
- Folio does not yet have a separate first-class table-analysis lane.
- Folio does not yet have a separate first-class numeric-fidelity lane.

These are current-state facts. They are not being re-scoped in this document.

Current exclusions:

- `folio ingest`
- unshipped stage-specific routing
- synthetic-only benchmark replacements for real corpus work
- manual one-off prompting outside the real pipeline
- speculative future evaluation categories that the runtime does not yet expose
  as first-class surfaces

### Core Principles

All future model-comparison prompts should inherit these principles unless the
repo explicitly changes them:

- Quality first. Choose the best model by measured output quality before cost
  or convenience.
- Evaluate the shipped runtime. Compare against what `main` actually does, not
  against an aspirational architecture.
- Use real corpus only. Do not substitute synthetic stand-ins and claim the run
  is complete.
- Require gold-standard annotation. The run is only as credible as the locked
  annotation rules and adjudicated labels behind it.
- Score by stage when the runtime has materially different stages.
- Measure stability and failure behavior, not just best-case quality.
- Measure confidence calibration where runtime signals exist.
- Preserve explicit blocker handling. A blocked run should still produce
  artifacts that explain why it stopped.
- Keep the methodology stable and the prompt fresh. The framework is reused;
  the prompt text is regenerated from current context.

### Standard Evaluation Lifecycle

Every recurring comparison should follow the same lifecycle.

#### 1. Preflight

- confirm current runtime truths on `main`
- inventory usable local candidate profiles from config
- record exact provider/model IDs at run time
- confirm real corpus availability
- confirm annotator availability
- stop early and document blockers if prerequisites are missing

#### 2. Corpus Design

- build a real-corpus manifest with anonymized corpus IDs
- include control cases, not only happy-path examples
- balance the corpus against the stages being evaluated
- ensure the corpus reflects the current runtime's actual decision points

#### 3. Annotation And Calibration

- define annotation rules before scored execution starts
- dual-annotate a calibration subset
- adjudicate disagreements before the full run
- lock the annotation schema for the scored run

#### 4. Isolated Execution

- run the real end-to-end pipeline, not manual provider prompts
- isolate runs with fresh targets and no stale-cache reuse for scoring
- collect stability data from repeated runs on a defined subset
- use diagnosis harnesses only for explanation, not for primary scoring

#### 5. Scoring

- score each evaluated stage with an explicit weighted rubric
- measure both quality and operational behavior
- treat abstention, skip behavior, and review-required behavior as scorable
  outcomes where the runtime supports them
- document unavailable metrics instead of inventing them

#### 6. Synthesis

- name the winner for each evaluated stage
- if the shipped runtime is still single-route, derive an interim single-route
  recommendation in addition to the stage winners
- document the code/config implications when the best stage winners differ

#### 7. Archival

- preserve the prompt
- preserve the report
- preserve the session log
- preserve the chat log or accepted substitute
- preserve annotation rules
- preserve the corpus manifest
- preserve machine-readable row-level metrics
- archive the work in Ontos

### Artifact Contract

Every model-comparison run should produce a tracked artifact set in
`docs/validation/`.

Baseline artifacts:

- prompt
- report
- session log
- chat log or accepted substitute

Comparison-specific artifacts:

- annotation rules
- corpus manifest
- machine-readable row-level metrics

Artifact rules:

- the report is the decision document
- the session log is chronological and includes exact commands, exit codes,
  durations when known, and error text
- the chat log preserves the human-AI transcript when the platform allows it;
  otherwise it must explain what substitute was used and where the raw
  transcript actually lives
- the annotation rules file is the locked schema and adjudication reference
- committed artifacts must use anonymized corpus IDs
- committed artifacts must not include raw client slide content, screenshots,
  or API keys
- API keys belong in `tests/validation/.env` during a run and must not be
  committed

### When To Re-Run

Model comparison should follow a trigger-based policy, not a calendar-only
policy.

Re-run when any of these happen:

- a new candidate frontier profile becomes available locally
- the provider/model ID for a configured profile changes
- the prompt contract changes materially
- the runtime changes its stage behavior, gating, schema, or output contract
- Folio adds a new LLM-powered feature that becomes part of the shipped
  surface
- annotation rules change materially
- production review data reveals systematic quality drift
- the real corpus expands enough to cover a new class of pages or diagrams

### How To Derive The Next Prompt

Future comparison prompts should inherit this methodology and then customize
only what is run-specific.

Stable methodology to inherit:

- quality-first comparison
- real-corpus requirement
- annotation and adjudication requirement
- stage-based scoring
- stability and failure measurement
- artifact contract
- blocker handling

Run-specific details that must be rewritten each time:

- the exact current runtime truths
- what surfaces are in scope and out of scope
- the candidate profiles inventory rules for that run
- the corpus composition required for that run
- the exact scoring weights for that run
- the exact final conclusions the report must produce

Prompts should say explicitly which assumptions are current-runtime facts and
which are stable methodology. This is how the framework stays reusable without
becoming stale.

## Current Worked Example

### 2026-03-22 Platform Comparison Prompt

The current worked example is
`docs/validation/tier2_platform_model_comparison_prompt.md`.

It preserved the original diagram-comparison idea from the repo:

- real engagement corpus
- gold-standard annotation
- weighted rubric
- stability checks
- quality-first selection
- confidence-calibration intent where runtime signals exist

It then updated the scope to match the current shipped codebase:

- the live `folio convert` runtime now exposes Pass 1, diagram extraction, and
  Pass 2 as the real LLM surface worth comparing
- one selected `convert` profile currently drives all stages, so the run needs
  both stage winners and an interim single-route recommendation
- unsupported diagrams, skip behavior, and review visibility are part of the
  current quality story and must be scored accordingly

The prompt therefore evaluates four outcomes:

- Pass 1 winner
- diagram-stage winner
- Pass 2 winner
- aggregate interim recommendation for the current single-route runtime

In the current worked example, that interim single-route recommendation is
derived from explicit aggregate weighting across the three evaluated stages,
while the stage-by-stage winners remain the primary conclusion.

For this worked example, text and content quality are evaluated through Pass 1
and Pass 2. Numbers are only evaluated through atomic facts, `key_data`,
insight, and grounding. Tables are only partially covered through generic
content scoring and table-like runtime heuristics. That is the correct current
scope for the prompt because Folio does not yet expose general table analysis
or numeric-fidelity scoring as separate first-class runtime lanes.

The prompt also records why broader methodology expansion was deferred:

- the current task was to compare models against the shipped platform, not to
  design evaluation lanes for features that do not yet exist
- the methodology should expand when Folio actually ships additional
  first-class evaluation surfaces, not before

### What We Did

The method used to produce the current prompt was:

1. Start from the original diagram-comparison intent in the repo rather than
   inventing a fresh evaluation philosophy.
2. Re-ground the task in the current codebase and current `main` runtime.
3. Preserve the rigorous parts of the older comparison idea.
4. Broaden scope only where the shipped runtime had already broadened.
5. Encode the result as a decision-complete validation prompt with explicit
   artifacts, blockers, scoring, and conclusions.

This is the pattern future prompt rewrites should follow.

## What This Document Does Not Do

This document does not:

- replace run-specific prompts
- rewrite the current Tier 2 platform prompt
- define future table-analysis or numeric-fidelity lanes before Folio ships
  them as first-class surfaces
- commit the project to one fixed rubric forever

It records the current methodology so it can be reused, revised, and extended
deliberately as Folio evolves.
