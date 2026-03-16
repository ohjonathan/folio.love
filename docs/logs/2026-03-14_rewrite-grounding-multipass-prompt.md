---
id: log_20260314_rewrite-grounding-multipass-prompt
type: log
status: active
event_type: chore
source: codex
branch: main
created: 2026-03-14
---

# rewrite grounding multipass prompt

## Summary

Recreated the deleted grounding and multi-pass Claude Code prompt as a
repo-accurate implementation spec under `docs/prompts/`. The new prompt is
aligned to current `main`, explicitly distinguishes shipped functionality from
missing FR-700 reviewability work, and uses the current agent-team
implementation prompt structure instead of the stale Tier 1-era prompt shape.

## Goal

- Restore the missing grounding prompt at the historical `docs/prompts/` path
- Rewrite it so Claude Code sees the actual current code surface
- Make the prompt decision-complete for the remaining reviewability work

## Key Decisions

- Used `docs/specs/v0.4.0_multi_provider_implementation_prompt.md` as the
  structural template instead of a validation prompt
- Treated the old prompt from commit
  `69abd9f3e9aa6c45020aea857d3f385565a6970b` as intent input only, not as a
  source of truth for repo assumptions
- Framed the new prompt as an additive FR-700 reviewability integration over
  current shipped grounding and Pass 2 behavior
- Kept the prompt at `docs/prompts/CLAUDE_CODE_PROMPT_grounding_multipass.md`
  per the clarified canonical path

## Changes Made

- Added `docs/prompts/CLAUDE_CODE_PROMPT_grounding_multipass.md`
- Documented current shipped features: multi-provider routing, `SlideText`,
  grounded JSON evidence flow, evidence validation, density scoring, Pass 2,
  current CLI `--passes`, registry workflow, and `_llm_metadata`
- Specified remaining required work: `review_status`, `review_flags`,
  `extraction_confidence`, registry integration, flagged status counts,
  promotion gating, and `review_confidence_threshold`
- Added decision-complete code sketches for evidence handling, extraction
  confidence scoring, and review auto-flagging
- Included file-by-file instructions, implementation order, test requirements,
  verification checklist, and guardrails

## Alternatives Considered

- Recreating the old prompt mostly verbatim and only fixing path names
- Using the Tier 2 validation prompt style instead of the implementation-spec
  style
- Writing the prompt at `docs/CLAUDE_CODE_PROMPT_grounding_multipass.md`
  instead of the restored historical `docs/prompts/` location

## Impacts

- The repo now again contains a canonical grounding and multi-pass implementation
  prompt
- Future agent-team work on FR-700 can start from an accurate current-main
  baseline instead of the deleted Anthropic-only prompt
- Ontos now indexes the restored prompt document in the live docs graph

## Testing

- `git diff --check -- docs/prompts/CLAUDE_CODE_PROMPT_grounding_multipass.md`
- `ontos map --sync-agents`
