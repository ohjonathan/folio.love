---
id: log_20260327_tier2-platform-model-comparison-finalization
type: log
status: complete
event_type: decision
source: codex
branch: main
created: 2026-03-27
---

# Tier 2 Platform Model Comparison Finalization

## Goal

Finalize the staged Tier 2 platform model-comparison outputs into a repo-safe,
canonical validation package under `docs/validation/`, record the resulting
per-stage routing decision, and update the Tier 3 tracker without making any
application-code changes.

## Key Decisions

- Promoted the canonical non-prompt artifact set directly into
  `docs/validation/` and left
  `docs/validation/tier2_platform_model_comparison_prompt.md` untouched.
- Removed the redundant staging folder `docs/validation/model_comparison/`
  after promotion because it duplicated the prompt ID and was no longer needed
  once canonical artifacts existed.
- Sanitized the session log, chat log, and corpus manifest to remove raw source
  titles, client/program labels, and machine-specific paths while preserving
  command chronology, exits, elapsed times, and failure classes.
- Recorded the practical routing recommendation as:
  - Pass 1: `openai_gpt53`
  - diagram stage: `anthropic_haiku45`
  - interim Pass 2: `anthropic_haiku45`
  - interim single current-`main` default: `anthropic_haiku45`
- Explicitly documented that the committed JSONL lacks separate `pass2` rows,
  so the Pass 2 conclusion is an interim best-defensible recommendation rather
  than a directly instrumented Pass 2 rubric winner.
- Marked the Tier 3 “Per-stage routing decision” track complete and kept the
  next-step order as real library rerun, real vault validation, then PR C
  (`folio enrich`).

## Alternatives Considered

- Keeping the staged folder as an archive. Rejected because it was redundant
  after promotion and preserved the duplicate prompt ID that was already
  breaking `ontos map`.
- Leaving Conclusion 3 vague due missing explicit Pass 2 rows. Rejected because
  the prompt requires a concrete Pass 2 conclusion; instead the report names an
  interim winner with an explicit instrumentation caveat.
- Preserving raw command arguments and source-derived filenames in the session
  log. Rejected because the prompt forbids raw client-sensitive identifiers in
  committed artifacts.

## Impacts

- The repo now contains a canonical, decision-ready Tier 2 model-comparison
  package under `docs/validation/`.
- The practical routing recommendation for current Folio operation is now
  recorded in both the report and the Tier 3 tracker.
- Future Ontos regeneration is unblocked from this package’s duplicate prompt
  copy because the staging folder was removed.
- The next operational blocker before PR C remains the real engagement/library
  rerun followed by real vault validation on the McKinsey laptop.
