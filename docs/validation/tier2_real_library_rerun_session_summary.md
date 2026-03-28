---
id: tier2_real_library_rerun_session_summary
label: tier2_real_library_rerun
created: 2026-03-27
purpose: orchestration-agent handoff
---

# Tier 2 Real Library Rerun — Session Summary

**Date:** 2026-03-27
**Operator:** Internal operator
**Agent:** Cursor agent session

## What we did

**Stage 1: Full-corpus rerun.** We ran the entire real engagement corpus (161 source files — 149 PDFs + 12 PPTXs across 93 directories) through `folio convert` using `anthropic_haiku45` with `--passes 2 --no-cache`. This was the model chosen by the Tier 2 platform model comparison as the best aggregate single-route default. The run targeted a **scratch validation library** (`SCRATCH_VALIDATION_ROOT/`) so the production library was not touched. Total runtime: ~8.5 hours. Result: **116 decks produced, 94/94 batch invocations succeeded** (one initial timeout recovered via manual retry). Zero systemic failures.

**Stage 2: Heuristic comparison.** We built `compare_libraries.py` to score every deck in both libraries (production built with `anthropic_sonnet4` vs scratch built with `anthropic_haiku45`) on registry metadata, markdown quality, and diagram extraction. Result: **production (sonnet4) outperformed the rerun (haiku45) on 53.5% of matched decks** (average score 46.0 vs 43.1). 22 decks favored the rerun, 31 ties. Initial gate decision: PARTIAL.

**Stage 3: LLM-as-judge validation.** The heuristic comparison uses proxy metrics (char counts, section counts, confidence numbers) that can't judge actual content quality. The operator confirmed that the differences were hard to see by eye. So we built `validate_merge_candidates.py` — a blinded LLM-as-judge that sends each pair to **OpenAI gpt-4.1** (a neutral model that produced neither version) as randomized "Version A" / "Version B" with a 5-criteria rubric (accuracy, completeness, structure, diagram quality, usefulness). We validated the top 15 candidates (Tier A: delta >= 5.0, Tier B: delta 3.0-4.9).

**LLM validation results:**

| Outcome | Count |
|---------|-------|
| Scratch confirmed better (merged) | 12 |
| Production retained (LLM overrides heuristic) | 2 |
| Tie | 1 |

The LLM correctly overrode the heuristic on 2 candidate decks where higher
confidence numbers didn't reflect better actual content, confirming the value
of the validation step.

**Stage 4: Selective merge.** We copied the 12 LLM-confirmed-better scratch deck directories into the production library, ran `folio status --refresh`, and committed. The production library is now **best-of-both**: 103 original sonnet4 decks + 12 targeted haiku45 improvements, all confirmed by an independent judge.

## Gate decision

**PASS TO VAULT VALIDATION.**

The production library at `PRODUCTION_LIBRARY_ROOT/` (115 decks) is the strongest available baseline. The Folio runtime is operationally confirmed for full-corpus processing. PR C (`folio enrich`) can proceed to the next validation step.

## Next steps

1. Real vault validation on the McKinsey laptop using the production library
2. Then PR C

## Artifacts produced

All in `VALIDATION_OUTPUT_ROOT/`:

| File | Purpose |
|------|---------|
| `tier2_real_library_rerun_report.md` | Full report with addendum |
| `tier2_real_library_rerun_session_log.md` | Command-by-command execution log |
| `tier2_real_library_rerun_chat_log.md` | Decision log |
| `tier2_real_library_rerun_manifest.md` | Source directory inventory |
| `tier2_real_library_rerun_comparison.json` | Heuristic per-deck comparison |
| `tier2_real_library_rerun_llm_validation.json` | LLM-as-judge results |
| `run_rerun.py` | Batch runner script |
| `compare_libraries.py` | Library comparison scorer |
| `validate_merge_candidates.py` | Blinded LLM validation script |
| `rerun-library/` | Scratch library (116 decks, local only) |

## Commits

1. `6e07469` — add tier2 real library rerun validation artifacts
2. `ab7dd62` — merge 12 LLM-validated deck improvements into production library
