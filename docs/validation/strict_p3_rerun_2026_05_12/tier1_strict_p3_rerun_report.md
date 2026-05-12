# Strict-P3 Rerun Validation Report

## Status
Passed local strict-P3 validation for all scoped slices.

## Baseline
- `folio.love` baseline: `origin/main` at `8fbddf7369684ad5609ec3ac450ce986932f21d9`.
- Initial `llm-dev-framework` baseline: `df39e6e3de47b2b5a970b99aa1580c1463dd97e0`.
- Framework compatibility fix used for final gates: `65750453ed5befb83ec50d67bd1a8ae21365c5f2`, published as `ohjonathan/llm-dev-framework` PR #7. The fix preserves strict dispatch verification and passes framework `verify-all.sh`.

## Gate Decision
PASS. Each slice has:
- a `manifest_version: "1.6.0"` manifest under `frameworks/manifests/`,
- a strict lifecycle receipt inventory under this validation directory,
- B.1, D.2, and D.5 receipts from `claude-sonnet`, `codex`, and `gemini`,
- a D.6 final approval with the `Strict-P3 lifecycle receipts verified` row,
- `scripts/llm-dev verify-lifecycle <manifest>` returning `status=strict_p3_review_complete`,
- `verify-d6-gate.sh --strict-p3 --manifest <manifest> <final_approval>` passing.

## GitHub Closeout
- Folio PR: https://github.com/ohjonathan/folio.love/pull/74, mergeable with GitHub pytest checks passing on Python 3.10 and 3.13.
- Framework compatibility PR: https://github.com/ohjonathan/llm-dev-framework/pull/7.
- Closed issues with strict-P3 evidence comments: #56, #61, #62, #63, #64, #69, #70, #71.

## Validation Results
- `scripts/llm-dev doctor`: PASS.
- `.llm-dev/framework/scripts/verify-all.sh`: PASS.
- `scripts/llm-dev verify <manifest>`: PASS for all six strict-P3 manifests.
- Negative lifecycle controls before receipt completion: FAIL as expected with `status=review_pending`.
- `scripts/llm-dev verify-lifecycle <manifest>`: PASS for all six strict-P3 manifests.
- `bash .llm-dev/framework/scripts/verify-d6-gate.sh --strict-p3 --manifest <manifest> <final_approval>`: PASS for all six slices.
- Focused transcript closeout test: `5 passed, 35 deselected`.
- Final full suite: `2100 passed, 6 skipped, 5 warnings in 16.91s`.

## Code Changes Made During Validation
- Added action-item extraction/rendering and deterministic speaker analytics in frontmatter, markdown, and registry summaries.
- Added document-oriented `.docx` conversion with `source_type: document`, one evidence note, and compatibility `slide_count: 1`.
- Added `folio.yaml` `defaults` / `derive` metadata resolution with CLI flag precedence.
- Added EML correspondence ingest, `folio ingest-email`, `.eml` routing through `folio ingest --type email_thread`, metadata/header/message/attachment parsing, `message_ids`, and Message-ID overlap continuation with `--as-new-entry`.
- Added `folio watch` with `--once`, `--dry-run`, `--quiet`, extension routing, stable-size wait, serial processing, success archive, and `_failed/` quarantine.
- Added focused tests for each slice and preserved all new lifecycle evidence under `docs/validation/strict_p3_rerun_2026_05_12/`.

## Framework Finding
The pulled strict-P3 framework at `df39e6e` rejected canonical adopter installs under `.llm-dev/framework` during D.6 because `verify-lifecycle.sh` delegated to `verify-family-dispatch.sh`, which recomputed repo root from the framework checkout rather than the adopter manifest. The fix passes the lifecycle verifier's detected adopter root into the nested dispatch verifier via `LLM_DEV_REPO_ROOT`; no receipt checks are skipped or weakened.
