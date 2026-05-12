---
id: folio-github-closeout-v1-0-0-phase-a-spec
deliverable_id: folio-github-closeout-v1-0-0
phase: A
role: spec-author
family: claude-opus
status: completed
---

# Phase A Spec: folio-github-closeout-v1-0-0
## Scope
This strict-P3 rerun slice addresses PR #50, issue #69. The scope authority is `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`; prior `folio_*_v1_*` artifacts are not lifecycle evidence.
## Acceptance Criteria
- Verify PR #50 is merged, docs-only, and its logs remain present on main.
- Verify transcript-native ingest for .vtt and .srt remains implemented by PR #73.
- Run the transcript-format focused test suite and record evidence before re-closing #69.
## Implementation Surface
- `tests/test_transcript_formats.py`
- `folio/pipeline/transcript_formats.py`
## Required Validation
- `./.venv/bin/python -m pytest tests/test_transcript_formats.py -q`
- `scripts/llm-dev verify <manifest>`
- Negative control: `scripts/llm-dev verify-lifecycle <manifest>` must fail with `review_pending` before receipts exist.
- Dispatch B.1, D.2, and D.5 through `dispatch-family-review.sh --append-receipt` for `claude-sonnet`, `codex`, and `gemini`.
- D.6 final approval must include the exact strict-P3 receipt row and pass `verify-d6-gate.sh --strict-p3 --manifest <manifest> <final_approval>`.
## Non-Goals
- Do not count any old artifacts from the prior failed closeout as evidence.
- Do not commit API keys or local `.env` files.

