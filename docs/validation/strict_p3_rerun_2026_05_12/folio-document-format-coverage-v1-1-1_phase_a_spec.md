---
id: folio-document-format-coverage-v1-1-1-phase-a-spec
deliverable_id: folio-document-format-coverage-v1-1-1
phase: A
role: spec-author
family: claude-opus
status: completed
---

# Phase A Spec: folio-document-format-coverage-v1-1-1
## Scope
This strict-P3 rerun slice addresses issue #56. The scope authority is `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`; prior `folio_*_v1_*` artifacts are not lifecycle evidence.
## Acceptance Criteria
- Accept `.docx` in `folio convert`.
- Use document text extraction rather than slide image extraction.
- Emit a single evidence note with full document text, `source_type: document`, and compatibility `slide_count: 1`.
## Implementation Surface
- `folio/converter.py`
- `tests/test_docx_conversion.py`
## Required Validation
- `./.venv/bin/python -m pytest tests/test_docx_conversion.py -q`
- `scripts/llm-dev verify <manifest>`
- Negative control: `scripts/llm-dev verify-lifecycle <manifest>` must fail with `review_pending` before receipts exist.
- Dispatch B.1, D.2, and D.5 through `dispatch-family-review.sh --append-receipt` for `claude-sonnet`, `codex`, and `gemini`.
- D.6 final approval must include the exact strict-P3 receipt row and pass `verify-d6-gate.sh --strict-p3 --manifest <manifest> <final_approval>`.
## Non-Goals
- Do not count any old artifacts from the prior failed closeout as evidence.
- Do not commit API keys or local `.env` files.

