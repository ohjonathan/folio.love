---
id: log_20260604_github-issues-75-76-implementation
type: log
status: active
event_type: feature
source: claude-code
branch: feat/issue-76-diagram-retry-extraction
created: 2026-06-04
---

# github-issues-75-76-implementation

## Goal

Address GitHub issues #75 and #76 end-to-end as two independent slices, with
scoped implementation, mocked-provider regression tests, and formal Tier
validation artifacts per issue.

- **#75 (fix):** VTT/SRT ingest emitted malformed timestamps inside extracted
  findings/quotes/action items/decisions/open questions (e.g. `04:21:900`,
  `01:20:49:519`, inverted range `03:03:03.650 - 03:18:819`).
- **#76 (feature):** No public slide-scoped diagram retry; `concept-map`/`process`
  abstained (so consulting decks cached almost nothing); transient provider
  failures forced full reconversion.

## Summary

- **#75 → PR #77** (`fix/issue-75-vtt-timestamp-normalization`): new shared
  `folio.pipeline.timestamps.canonicalize_timestamp` applied to VTT/SRT cue
  normalization and to LLM-extracted timestamp fields. Unambiguous malformations
  repaired to `HH:MM:SS.mmm`; unrepairable values dropped + `timestamp_review`
  flag + `needs-review` marker. `.txt`/`.md` ingest unchanged.
- **#76 → PR #78** (`feat/issue-76-diagram-retry-extraction`): CLI
  `--diagrams-only`/`--slides`/`--retry-failed-diagrams`/`--retry-review-required-diagrams`
  → surgical `FolioConverter.convert_diagrams()`; `concept-map`/`process`
  first-class + Structured Inventory; reduced-image-payload Pass A retry;
  end-of-run retry-candidate summary; cache persists on `--no-cache`.

## Key Decisions

1. **Two independent branches + two PRs** (no source-file overlap) per the user's
   delivery choice; each PR self-contained with its own four Tier artifacts.
2. **#75 repair-vs-flag policy:** repair only unambiguous colon-before-ms forms;
   flag (drop value, mark for review) for inverted ranges / out-of-range / >3
   components — never emit invalid data. Single shared helper with focused tests.
3. **#76 surgical path is a dedicated method, not a branch inside `convert()`:**
   a diagrams-only run has no Pass 1/2, so it must not regenerate the deck body;
   it refreshes sidecars + deck diagram review flags + registry in place.
4. **#76 deck-flag refresh recomputes only `diagram_*_slide_{n}` flags** (which
   depend solely on diagram analyses), preserving all other flags, via a
   body-preserving frontmatter rewrite.
5. **#76 minimum-robust diagram breadth:** allowlist + generic `DiagramGraph`
   inventory; the six bespoke consulting-visual schemas and the
   semantic-inventory-only LLM fallback are deferred with documented rationale.

## Alternatives Considered

- **#75:** infer the dropped hour to "repair" the inverted range — rejected as
  ambiguous (unrecoverable), so it is flagged instead.
- **#75:** silently drop unrepairable timestamps — rejected; the acceptance
  criteria require flagging for review.
- **#76:** thread retry conditionals through `convert()` — rejected (would risk
  regenerating the deck body without Pass 1/2 results).
- **#76:** regenerate full deck frontmatter via `assess_review_state` — not
  possible without Pass 1/2; recompute the diagram-flag subset instead.
- **#76:** implement all six bespoke schemas now — deferred per the issue's
  "minimum robust" guidance to keep the slice shippable.

## Impacts

- New public CLI surface on `folio convert` (retry flags); full-conversion
  behavior unchanged unless a flag is used (additive end-of-run summary only).
- New module `folio/pipeline/timestamps.py`; new
  `FolioConverter.convert_diagrams()` + diagram-notes retry helpers; `concept-map`
  and `process` now produce cacheable, rendered notes.
- Two follow-ups deferred (documented in `docs/validation/issue_76_validation_report.md`):
  bespoke consulting-visual schemas; semantic-inventory-only extraction fallback.

## Testing

- `.venv/bin/python -m pytest tests/` — **2136 passed, 6 skipped** on the #75
  branch; **2125 passed, 6 skipped** on the #76 branch. No live provider calls.
- New: `tests/test_timestamps.py` (27), `tests/test_diagram_retry.py` (23); plus
  extended interaction/transcript/diagram-type-gate regressions.

## Documentation

- `CHANGELOG.md` Unreleased entries (one per issue, on each branch).
- Per-issue Tier validation artifacts: `docs/validation/issue_75_*` and
  `docs/validation/issue_76_*` (report, session log, chat log, prompt).