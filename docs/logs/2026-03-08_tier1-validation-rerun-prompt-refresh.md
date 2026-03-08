---
id: log_20260308_tier1-validation-rerun-prompt-refresh
type: log
status: active
event_type: decision
source: codex
branch: main
created: 2026-03-08
---

# tier1 validation rerun prompt refresh

## Goal

Refresh the obsolete Tier 1 validation prompt so it matches the current `main`
baseline after the renderer reliability work, multi-provider support, and the
current Tier 1 gate interpretation.

## Key Decisions

- Replaced the old `v0.1` validation assumptions with a new rerun prompt at
  `docs/validation/tier1_validation_rerun_prompt.md`.
- Defined the full Tier 1 gate strictly as `50/50` automated PPTX conversions
  on the real corpus with zero silent failures.
- Split automated PPTX validation from PDF mitigation validation; manual PDFs
  remain mitigation-only and do not count toward Tier 1.
- Added hard preflight stop conditions for the historical `-9074` cohort and
  the fatigue batch so the rerun can abort early when a full pass is no longer
  achievable.
- Kept automated-PPTX cross-rerun cache behavior as an observed/deferred
  limitation while requiring same-PDF rerun cache validation.
- Required a side-by-side delta section against the March 2026 baseline report.

## Alternatives Considered

- Reusing the original prompt with small path fixes only.
  Rejected because the gate logic, cache expectations, and managed-mac runtime
  assumptions were all stale.
- Treating zero silent failures on a converted subset as sufficient.
  Rejected because it weakens the roadmap wording and masks renderer failures.
- Counting operator-exported PDFs toward Tier 1.
  Rejected because Tier 1 requires fully automated PPTX conversion.

## Impacts

- Future reruns now have a repo-accurate execution prompt and do not need to
  infer current behavior from the historical March report.
- The rerun outcome will be easier to interpret because automated PPTX results,
  mitigation-only PDF results, and the March 2026 delta are separated.
- The prompt makes it cheaper to fail fast when the remaining renderer
  limitations still prevent a full Tier 1 pass on the same corpus.
