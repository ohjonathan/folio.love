# Issue #75 — Implementation Prompt (scoped)

> Scoped extract of the orchestration prompt for Slice A. The full orchestration
> covered issues #75 and #76; this records the #75-relevant task as executed.

## Goal

Address GitHub issue #75 (`ohjonathan/folio.love`): VTT-derived analysis
timestamps are sometimes malformed (`04:21:900`, `01:20:49:519`, `01:22:44:700`,
inverted range `03:03:03.650 - 03:18:819`). Make all VTT-derived analysis
timestamps canonical and machine-parseable.

## Acceptance criteria

- VTT-derived findings, quotes, action items, decisions, and open questions use
  one canonical timestamp format (`HH:MM:SS.mmm` / `HH:MM:SS.mmm - HH:MM:SS.mmm`).
- Milliseconds represented consistently if retained.
- Ranges preserve both start and end.
- Invalid formats like `04:21:900` and `01:20:49:519` do not appear in notes.
- Existing `.txt`/`.md` transcript ingest behavior is unchanged.
- Add regression coverage using representative VTT cue ranges.

## Implementation guidance

- Find the VTT ingest/parsing path and interaction-analysis extraction pipeline.
- Normalize cue timestamps before prompt construction when possible.
- Add post-processing validation/repair for extracted timestamp fields.
- Repair only unambiguous malformed timestamps; otherwise flag the finding for
  timestamp review rather than silently emitting bad data.
- Prefer a single shared timestamp normalization helper with focused tests.

## Constraints

- No live LLM/provider/API calls required for regression tests.
- Two-branch / two-PR delivery; this slice on `fix/issue-75-vtt-timestamp-normalization`.
- Produce four Tier-validation artifacts in `docs/validation/`.
