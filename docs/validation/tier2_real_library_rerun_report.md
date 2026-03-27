---
id: tier2_real_library_rerun_report
type: atom
status: complete
ontos_schema: 2.2
curation_level: 0
label: tier2_real_library_rerun
created: 2026-03-27
---

# Tier 2 Real Library Rerun — Final Report

## Executive Summary

Reran the **full real engagement corpus** (161 source files, 93 directories)
using `anthropic_haiku45` per the Tier 2 model comparison decision. The rerun
targeted a **scratch validation library** to enable per-deck comparison against
the existing production library (built with `anthropic_sonnet4`).

**Result: PARTIAL / FIX KNOWN ISSUES FIRST**

The rerun completed successfully: 94/94 batch invocations eventually succeeded
(1 initial timeout recovered via manual retry). The scratch library produced
**116 decks** from the full corpus. However, the per-deck comparison shows that
the **production library (sonnet4) outperforms the rerun library (haiku45)** on
aggregate quality metrics.

## Run Context

| Field | Value |
|-------|-------|
| Run date | 2026-03-27 |
| Operator | Jonathan Oh |
| Machine | Managed macOS laptop (Apple Silicon) |
| Branch | `main` |
| Python | `3.12.13` |
| folio-love | `0.2.0` |
| Model decision | `anthropic_haiku45` (`claude-haiku-4-5-20251001`) |
| Flags | `--passes 2 --no-cache` |
| Library target | Scratch: `<SCRATCH_LIBRARY>` |
| Production library | `<PRODUCTION_LIBRARY>` (115 decks, untouched) |
| Config | `<RERUN_CONFIG>` |

## Source Directory Inventory

- **Total source files:** 161 (149 PDFs + 12 PPTXs)
- **Total source directories:** 93
- **Batch invocations:** 94 (83 PDF + 11 PPTX)
- **Source root:** `<SOURCE_ROOT>`

See `tier2_real_library_rerun_manifest.md` for the anonymized directory
inventory.

## Command Inventory

### Phase A: PDF Batch Conversions (83 directories)

| Metric | Value |
|--------|-------|
| Directories processed | 83 |
| Success | 82 |
| Timeout (recovered) | 1 |
| Errors | 0 |
| Total runtime | 8.3 hours |

The single timeout occurred on `DIR_001` (5 PDFs, 1800s limit). The 2
remaining files were retried individually and succeeded (412s + 54s).

### Phase B: PPTX Batch Conversions (11 directories)

| Metric | Value |
|--------|-------|
| Directories processed | 11 |
| Success | 11 |
| Timeout | 0 |
| Errors | 0 |
| Total runtime | 0.2 hours (884s) |

PPTX files processed with `--no-dedicated-session` from Cursor. All succeeded.

### Post-Run Validation

| Command | Result |
|---------|--------|
| `folio status --refresh` | 116 decks, all current, 112 flagged |
| `folio scan` | 161 sources scanned, 45 new (dedup), 0 stale, 0 missing |

The 45 `new` entries from `folio scan` are duplicate copies of the same
documents placed across multiple journey directories. Folio correctly
deduplicated them; this is expected behavior, not a failure.

## Comparison Results: Production vs Scratch

### Summary

| Metric | Value |
|--------|-------|
| Matched decks (by source_hash) | 114 |
| Production-only | 1 (`PROD_ONLY_001`) |
| Scratch-only | 2 (`RERUN_ONLY_001`, `RERUN_ONLY_002`) |
| **PRODUCTION_BETTER** | **61 (53.5%)** |
| TIE | 31 (27.2%) |
| RERUN_BETTER | 22 (19.3%) |
| **Avg production score** | **46.0** |
| **Avg scratch score** | **43.1** |

### Score Breakdown

| Category | Scratch better | Production better | Tie |
|----------|---------------:|------------------:|----:|
| Registry metadata | 39 | 75 | — |
| Markdown quality | 24 | 90 | — |
| Diagram extraction | 19 | 95 | — |

### Top 5 RERUN_BETTER (haiku45 wins)

| Comparison ID | Source Hash | Delta | Prod Score | Scratch Score |
|---|---|---:|---:|---:|
| `CMP_083` | `a775d60ea171` | +9.3 | 43.0 | 52.3 |
| `CMP_066` | `7d07eb9332cc` | +8.6 | 35.1 | 43.7 |
| `CMP_113` | `f39607f0b70c` | +8.5 | 31.9 | 40.4 |
| `CMP_044` | `4b66883aa328` | +5.3 | 46.0 | 51.3 |
| `CMP_051` | `625747ea9db0` | +5.3 | 37.4 | 42.7 |

### Top 5 PRODUCTION_BETTER (sonnet4 wins)

| Comparison ID | Source Hash | Delta | Prod Score | Scratch Score |
|---|---|---:|---:|---:|
| `CMP_062` | `7a02ef38c9a3` | -16.8 | 40.4 | 23.6 |
| `CMP_024` | `24c3595eefcf` | -16.0 | 50.1 | 34.1 |
| `CMP_111` | `e984a79aba7a` | -13.1 | 53.3 | 40.2 |
| `CMP_001` | `017b6975f140` | -12.6 | 56.0 | 43.4 |
| `CMP_067` | `7d1c36f4372c` | -12.5 | 52.1 | 39.5 |

### Analysis

The production library (sonnet4) outperforms the rerun library (haiku45) on
**53.5% of matched decks**. The average score gap is **2.9 points** (46.0 vs
43.1).

Key observations:

1. **Markdown quality favors production strongly** (90 vs 24). Sonnet4 produces
   longer, more structured descriptions with more sections and evidence
   markers.
2. **Diagram extraction favors production** (95 vs 19). Sonnet4 extracts more
   diagram nodes/edges and provides higher confidence scores.
3. **Registry metadata is closer** (75 vs 39), with haiku45 sometimes
   producing fewer review flags.
4. **Haiku45 wins on a minority of architecture-heavy documents** where its
   extraction is cleaner and more focused.
5. **Sonnet4 wins on many dense, multi-page documents** where its higher
   capacity produces richer analysis.

## Notable Runtime Observations

1. **No systemic failures.** All 161 files were processed successfully. The
   only operational issue was one recoverable timeout on `DIR_001`.
2. **PPTX without dedicated session worked.** The `--no-dedicated-session`
   flag allowed all 12 PPTX files to process from Cursor without needing
   Terminal.app.
3. **Deduplication is correct.** Folio recognized duplicate source files across
   journey directories and did not create redundant library entries.
4. **Pass 2 triggered selectively.** Dense slides above the density threshold
   (2.0) received Pass 2 analysis. Most simple diagrams skipped Pass 2 as
   expected.
5. **API stability was excellent.** No rate limit errors and no auth failures
   were recorded across 8.5 hours of continuous Anthropic calls.

## Gate Decision

### PARTIAL / FIX KNOWN ISSUES FIRST

The rerun demonstrates that the Folio runtime is **operationally sound**: it
can process the full real corpus without systemic failure using the chosen
model. However, the quality comparison shows that `anthropic_haiku45` produces
**lower quality output** than the existing `anthropic_sonnet4` production
library on the majority of decks.

This means:

1. The current production library (sonnet4) should be **retained as the
   baseline** for vault validation, not replaced by the haiku45 rerun.
2. The Tier 2 model comparison's aggregate recommendation of haiku45 as the
   single-route default is **incorrect for production use**. The smaller 40-slide
   subset did not capture sonnet4's advantage on dense and complex documents at
   full-corpus scale.
3. For specific comparisons where haiku45 scored higher (22 of 114), a
   best-of-both merge could improve the library, but that requires per-deck
   curation rather than a blanket model switch.

## Next Steps

1. **Keep production library (sonnet4) as the vault-validation baseline.** Do
   not overwrite it with haiku45 output.
2. **Consider per-deck best-of merge.** For the 22 comparisons where haiku45
   scored higher, evaluate whether the rerun version should replace the
   production version.
3. **Revisit the model-comparison methodology.** The smaller comparison subset
   underweighted dense multi-page documents where sonnet4 excels.
4. **Proceed to vault validation with the production library.** The production
   library (115 decks, sonnet4) is ready for vault validation on the managed
   laptop.
5. **PR C (`folio enrich`) can proceed after vault validation** using the
   production library as its input.

## Tracked Artifacts Produced

| File | Description |
|------|-------------|
| `tier2_real_library_rerun_prompt.md` | Task specification |
| `tier2_real_library_rerun_report.md` | This report |
| `tier2_real_library_rerun_session_log.md` | Sanitized command-by-command execution log |
| `tier2_real_library_rerun_chat_log.md` | Sanitized decision and rationale log |
| `tier2_real_library_rerun_manifest.md` | Anonymized source-directory inventory |
| `tier2_real_library_rerun_comparison.json` | Sanitized per-deck comparison data |

## Local-Only Run Artifacts

The managed-laptop run also used local helper scripts and produced a local
scratch rerun library. Those artifacts are intentionally not committed because
they are run-specific and/or contain sensitive local context.
