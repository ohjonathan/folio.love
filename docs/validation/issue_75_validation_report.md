# Issue #75 Validation Report — VTT Timestamp Normalization

**Date:** 2026-06-04
**Validator:** Automated implementation + regression run (Claude Code)
**Scope:** GitHub issue #75 — normalize timestamps in extracted findings/action items
**Pipeline version:** folio 1.4.0 (Unreleased; branch `fix/issue-75-vtt-timestamp-normalization`)
**LLM calls:** None (all tests use mocked providers / pure unit paths)

---

## Summary

A real Zoom VTT ingest produced malformed timestamps inside extracted analysis
fields (`claims`, `data_points`, `decisions`, `open_questions`, `action_items`,
`notable_quotes`) even though the raw cue timestamps were valid. A single shared
canonicalizer (`folio.pipeline.timestamps.canonicalize_timestamp`) now normalizes
both VTT/SRT cue timestamps (before prompt construction) and LLM-extracted
timestamp fields (post-processing). Unambiguous malformations are repaired;
unrepairable values are dropped and the finding is flagged for review.

| Metric | Value |
|--------|-------|
| New helper module | `folio/pipeline/timestamps.py` |
| Integration points | `transcript_formats.py`, `interaction_analysis.py`, `interaction_markdown.py` |
| New unit tests (`test_timestamps.py`) | 27 passed |
| Slice A targeted tests | 59 passed |
| Full suite | 2136 passed, 6 skipped |
| Live provider calls | 0 |

---

## Acceptance criteria → evidence

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | VTT-derived findings, quotes, action items, decisions, open questions use one canonical format | ✅ | `_coerce_findings` (claims/data_points/decisions/open_questions/action_items) and `_coerce_quotes` route timestamps through `canonicalize_timestamp`. Tests: `TestTimestampNormalization::test_coerce_findings_*`, `test_coerce_quotes_repairs_and_flags`, `test_end_to_end_repairs_colon_timestamp`. |
| 2 | Milliseconds represented consistently if retained | ✅ | Canonical output is `HH:MM:SS.mmm`; range ends share ms presence. Test: `TestRanges::test_milliseconds_are_consistent_across_range_ends`. |
| 3 | Ranges preserve both start and end | ✅ | Range parsing/formatting in `canonicalize_timestamp`. Tests: `TestRanges::*`, `test_coerce_findings_preserves_valid_and_absent_timestamps`. |
| 4 | Invalid formats like `04:21:900` and `01:20:49:519` do not appear | ✅ | Repaired to `00:04:21.900` / `01:20:49.519`; unrepairable inverted range dropped + `needs-review` marker. Tests: `TestRepairableColonMilliseconds::*`, `test_markdown_renders_needs_review_and_hides_malformed_value` (asserts `03:18:819` absent from output). |
| 5 | Existing `.txt`/`.md` ingest behavior unchanged | ✅ | `normalize_source_text` and ingest routing untouched; valid timestamps pass through unchanged. Tests: `TestNormalizeHelpers::test_plain_text_timestamps_in_body_are_not_reformatted`, existing `test_single_pass_parses_structured_json_and_validates_quote` (uses `00:04:15`, stays `review_status == "clean"`). |
| 6 | Add regression coverage using representative VTT cue ranges | ✅ | `test_transcript_formats.py::test_vtt_cue_range_renders_canonical_timestamps` (issue cue `00:03:03.650 --> 00:03:18.819`) plus the full `test_timestamps.py` matrix. |

---

## Repair vs. flag policy

- **Repaired (unambiguous):** colon-before-milliseconds forms — `01:20:49:519` →
  `01:20:49.519`, `01:22:44:700` → `01:22:44.700`, `04:21:900` → `00:04:21.900`;
  SRT comma decimals; zero-padding; fractional-second width.
- **Flagged (unsafe to repair):** non-numeric tokens, out-of-range fields
  (`MM`/`SS` ≥ 60), >3 components, and inverted ranges where the end precedes the
  start — e.g. the issue's `03:03:03.650 - 03:18:819` (end resolves to
  `00:03:18.819`, before the start). Flagged findings drop the timestamp, set
  `timestamp_review=True`, add a `timestamp_review_*` review flag, and render
  `- timestamp: needs-review` instead of an invalid value.

---

## Residual risk

- The canonicalizer also applies to `.txt`/`.md`-sourced extracted timestamps.
  This only changes output when a value is malformed (a strict improvement); valid
  values are byte-identical, and the `.txt`/`.md` *parsing* path is unchanged.
- Repair of the 3-component `MM:SS:mmm` form assumes a transcript-minutes reading
  (`04:21:900` → `00:04:21.900`); this matches the observed Zoom output and is the
  only reading consistent with VTT's 3-digit-millisecond / 2-digit-second rule.
