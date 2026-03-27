---
id: tier2_real_library_rerun_chat_log
type: atom
status: complete
ontos_schema: 2.2
curation_level: 0
label: tier2_real_library_rerun
created: 2026-03-27
---

# Chat Log — Tier 2 Real Library Rerun

## Platform

Cursor IDE (Agent mode). Raw transcript is preserved in the local Cursor agent
transcript store on the managed validation laptop and is not committed to this repo.
This tracked document is the sanitized decision-and-rationale substitute.

## Session Summary

**Date:** 2026-03-27
**Operator:** Jonathan Oh
**Agent:** Ada (Cursor Agent, claude-4.6-opus-high-thinking)

### Key Decisions Made

1. **Library target:** scratch validation library at `<SCRATCH_LIBRARY>` while
   leaving the production library at `<PRODUCTION_LIBRARY>` untouched.
2. **Scope:** full corpus rerun — all 161 files (149 PDFs + 12 PPTXs) across 93
   source directories.
3. **Model:** `anthropic_haiku45` per the Tier 2 model-comparison decision.
4. **Config approach:** used `<RERUN_CONFIG>` to point `library_root` at the
   scratch library and passed `--llm-profile anthropic_haiku45` explicitly.
5. **Execution approach:** local batch-runner helper walked the source tree,
   split PDF/PPTX invocations, and logged each command with exit code and
   elapsed time. Resume logic skipped already-completed directories.
6. **Timeout handling:** one 1800s timeout occurred on `DIR_001`; the two
   remaining files were retried individually and succeeded.
7. **PPTX handling:** `--no-dedicated-session` from Cursor was sufficient.
   All 12 PPTX files processed successfully without a dedicated PowerPoint
   session.

### Outcome

- **Gate decision:** PARTIAL / FIX KNOWN ISSUES FIRST
- **Production library retained** as the vault-validation baseline
  (`sonnet4` outperforms `haiku45` on 53.5% of matched decks; average score
  46.0 vs 43.1)
- **Rerun library preserved locally** for possible per-deck best-of curation
  (22 comparisons where `haiku45` scored higher)
- **Runtime confirmed operational** — the full 161-file corpus processed with
  no systemic failures
