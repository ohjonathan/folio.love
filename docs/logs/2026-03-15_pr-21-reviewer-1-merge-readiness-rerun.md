---
id: log_20260315_pr-21-reviewer-1-merge-readiness-rerun
type: log
status: active
event_type: decision
source: codex
branch: codex/diagram-pr3-schema-cache
created: 2026-03-15
---

# pr-21-reviewer-1-merge-readiness-rerun

## Context

Merge-readiness rerun for PR #21 on branch
`codex/diagram-pr3-schema-cache` at
`4c4e50d423651aa459a2f3d559cf63a88a1c3213`, compared against `main`
with special focus on the delta since
`1bc56bca6c20680cf512e99df8683cddfc4093b1`.

## Goal

Verify whether the latest follow-up commit actually closes the remaining
contract issues around stable edge IDs and partial diagram payload
hardening, and whether the branch is merge-ready overall.

## Decision

Request changes.

## Rationale

- Ran Ontos activation and reviewed the PR 3 schema-cache prompt, the
  approved diagram extraction proposal, and the prior PR 21 rerun review
  logs before inspecting code.
- Compared `main...HEAD` and `1bc56bca6c20680cf512e99df8683cddfc4093b1..HEAD`.
  The rerun delta touched only `folio/pipeline/analysis.py` and
  `tests/test_diagram_analysis.py`.
- Ran targeted validation:
  - `.venv/bin/python -m pytest tests/test_diagram_analysis.py tests/test_analysis_cache.py tests/test_converter_integration.py tests/test_grounding.py -q`
    -> `230 passed`
  - `.venv/bin/python -m pytest tests -q`
    -> `767 passed, 3 skipped`
- Reproduced that `_rewrite_edge_ids()` is still not fully order-independent:
  same-pair edges with identical `(label, direction)` keys still swap IDs when
  input order changes because the sort key does not break ties.
- Reproduced that the new partial-payload hardening is incomplete at the
  document-review level: `DiagramAnalysis.from_dict()` sets
  `review_required=True`, but `assess_review_state()` ignores that field, so a
  marker-only payload like `{"description": "..."}` still yields
  `ReviewAssessment(status='clean', flags=[], confidence=None)`.

## Key Decisions

- Treated the approved proposal and PR 3 prompt as the merge contract, not the
  green test suite alone.
- Counted the remaining edge-ID instability as a blocking correctness issue
  because PR 3 is establishing the stable-ID foundation for future override
  persistence.
- Counted the partial-payload gap as still open because the hardening does not
  actually prevent clean document-level surfacing in the current pipeline.

## Alternatives Considered

- Approve because the latest commit improves both previously flagged areas and
  the full suite is green. Rejected because both areas still fail under direct
  adversarial repros.
- Downgrade the partial-payload issue to a future follow-up. Rejected because
  the new helper explicitly claims partial payloads should not surface as clean
  analyses, which is not true today.

## Consequences

- Merge should remain blocked until edge-ID assignment is stable for same-key
  parallel edges and partial diagram payloads actually affect review-state /
  output safety rather than only mutating an internal flag.
- Once those two issues are fixed, the rest of the branch looks healthy:
  routing, cache metadata/versioning, warm-cache polymorphic deserialization,
  abstention handling, and the broader test suite all check out.

## Impacts

- Prevents PR 3 from locking in a still-order-sensitive edge identity scheme
  for parallel connections.
- Prevents malformed or sparse diagram cache entries from appearing
  document-clean despite carrying no trustworthy inherited slide analysis.
