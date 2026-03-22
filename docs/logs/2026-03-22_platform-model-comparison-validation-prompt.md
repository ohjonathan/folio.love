---
id: log_20260322_platform-model-comparison-validation-prompt
type: log
status: active
event_type: chore
source: codex
branch: main
created: 2026-03-22
concepts: [validation, llm-evaluation, prompts, ontos]
---

# platform model comparison validation prompt

## Summary

Drafted a new Tier 2 validation prompt for platform-level LLM model
comparison, grounded it against the current shipped `folio convert` runtime,
and synced the Ontos-generated context artifacts so the prompt is discoverable
from the project docs graph.

## Goal

- Capture a decision-complete prompt for comparing current Folio LLM profiles
  against the live runtime rather than the older diagram-only plan
- Preserve the original diagram-comparison rigor while expanding scope to Pass
  1, diagram extraction, and Pass 2
- Leave a reusable validation artifact that another engineer or agent can run
  without inventing missing protocol details

## Key Decisions

- Kept this as a validation prompt in `docs/validation/` instead of a Claude-
  specific implementation prompt because the task is evaluation, not feature
  delivery
- Scoped the comparison to the current shipped `folio convert` path only,
  explicitly excluding unimplemented surfaces such as `folio ingest` and future
  per-stage routing
- Preserved gold-standard annotation and weighted rubric requirements, with
  stage-specific scoring for Pass 1, diagrams, and Pass 2
- Required five explicit report conclusions: Pass 1 winner, diagram-stage
  winner, Pass 2 winner, interim single current-`main` default, and routing
  implications if stage winners differ
- Required anonymized corpus IDs and blocked synthetic substitutes so the run
  cannot claim completion without real engagement material and annotators

## Alternatives Considered

- Reusing the older diagram-only comparison framing. Rejected because the live
  codebase now exposes a broader LLM surface and the prompt needed to reflect
  that current state.
- Writing a run-ready prompt that assumes corpus, annotators, and candidate
  profiles are already prepared. Rejected because the environment prerequisites
  are material and need an explicit preflight gate.
- Drafting an implementation spec for stage-specific routing in the same
  document. Rejected because the current task was to define the evaluation
  protocol and report the implications, not to design or ship follow-on code.

## Impacts

- The repo now has a current-state validation prompt for platform-level LLM
  comparison rather than relying on stale diagram-only comparison notes
- Future comparison work can be executed with explicit artifact requirements,
  rubric weights, tie-break rules, and stop conditions already defined
- The Ontos context map now indexes the new validation prompt, making it part
  of the project’s searchable documentation graph

## Changes Made

- Added `docs/validation/tier2_platform_model_comparison_prompt.md`
- Synced `Ontos_Context_Map.md` and `AGENTS.md` with `ontos map --sync-agents`

## Testing

- `ontos map --sync-agents`
