---
id: log_20260321_cap-diagram-max-tokens-at-32768-proposal-ceiling
type: log
status: active
event_type: pr28-field-hardening-stage1-review-rounds
source: cli
branch: fix/v0.1.1-field-hardening-stage1
created: 2026-03-21
---

# PR #28 Field Hardening Stage 1 — Review Rounds 3–6

## Goal

Address all blocking reviewer findings across 4 review rounds on PR #28 (v0.1.1 field‐hardening Stage 1).

## Key Decisions

- **Pass A truncation contract** (§6.1): truncated retry is a failure, not `truncated_success`. Original `pass_a_raw` is discarded before retry so failed retries can't silently preserve partial data.
- **Deck-level `text_validation_unavailable`**: derived from `slide_texts` for all reviewable slides, not from evidence or analysis state. Pending slides with unavailable text still count.
- **`SlideText.is_empty`**: all three detection paths (`_validate_evidence`, diagram confidence, `assess_review_state`) now respect `is_empty`.
- **Analysis cache version**: bumped 3→4 to invalidate pre-hardening cached evidence.
- **`diagram_max_tokens` ceiling**: capped at 32768 in config validation + defensive clamp at extraction site.
- **`EndpointNotAllowedError`**: classified as `endpoint_blocked` instead of `unknown`.
- **A0 fallback**: oversized-page DPI backoff uses A0 (2383.94×3370.39pt) instead of US Letter.

## Alternatives Considered

- Pending-gate vs slide_texts-gate for deck flag: R4 used pending gate, R6 switched to slide_texts-based check per proposal §6.3.
- `truncated_success` continue vs failure: R3–R4 allowed truncated data through, R5 made it a strict failure per §6.1.

## Impacts

- All Review Round 3–6 blocking issues resolved
- 983 passed, 3 skipped, 0 failures
- Ready to merge

## Testing

Full regression: `python3 -m pytest tests/ --ignore=tests/test_inspect.py --ignore=tests/test_normalize.py`
Result: 983 passed, 3 skipped