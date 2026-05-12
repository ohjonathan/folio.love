---
id: folio-config-defaults-v1-2-0-phase-a-spec
deliverable_id: folio-config-defaults-v1-2-0
phase: A
role: spec-author
family: claude-opus
status: completed
---

# Phase A Spec: folio-config-defaults-v1-2-0
## Scope
This strict-P3 rerun slice addresses issue #63. The scope authority is `docs/validation/strict_p3_rerun_2026_05_12/pre_a_triage.md`; prior `folio_*_v1_*` artifacts are not lifecycle evidence.
## Acceptance Criteria
- Support `defaults` and `defaults.derive` blocks in config.
- Resolve metadata in order: CLI flag, derivation, defaults, then error.
- Make ingest date/type optional at Click parsing level while preserving required resolved metadata before ingest commits.
- Apply the resolution order to `folio ingest` metadata fields `client`, `engagement`, `target`, `type`, `date`, and `participants`.
- Preserve the same CLI precedence for the `.eml` route exposed through `folio ingest <path.eml> --type email_thread`.
- Apply the same defaults/derivation surface to `folio convert` for `client`, `engagement`, and `target`, including source-root client/engagement derivation before config defaults.
## Implementation Surface
- `folio/config.py`
- `folio/defaults.py`
- `folio/cli.py`
- `folio/converter.py`
- `folio/correspondence.py`
- `tests/test_config_defaults.py`
- `tests/test_cli_ingest.py`
- `tests/test_cli_correspondence.py`
## Required Validation
- `./.venv/bin/python -m pytest tests/test_config_defaults.py tests/test_cli_ingest.py tests/test_cli_correspondence.py -q`
- `scripts/llm-dev verify <manifest>`
- Negative control: `scripts/llm-dev verify-lifecycle <manifest>` must fail with `review_pending` before receipts exist.
- Dispatch B.1, D.2, and D.5 through `dispatch-family-review.sh --append-receipt` for `claude-sonnet`, `codex`, and `gemini`.
- D.6 final approval must include the exact strict-P3 receipt row and pass `verify-d6-gate.sh --strict-p3 --manifest <manifest> <final_approval>`.
## Non-Goals
- Do not count any old artifacts from the prior failed closeout as evidence.
- Do not commit API keys or local `.env` files.
