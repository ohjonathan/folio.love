---
id: log_20260315_pr23-reviewer1-peer-review-rerun-head-6a83d3a
type: log
status: active
event_type: decision
source: codex
branch: codex/diagram-pr5-rendering
created: 2026-03-15
---

# pr23-reviewer1-peer-review-rerun-head-6a83d3a

## Context

Peer review rerun for PR #23 on branch `codex/diagram-pr5-rendering` at
`6a83d3a`, compared against base `97f03b9`, with extra attention to whether
previously reported Mermaid validation, group rendering, sanitization, and
direction-handling issues were actually fixed.

## Goal

Review the deterministic diagram rendering PR for completeness, correctness,
maintainability, and merge readiness, with emphasis on Mermaid completeness,
sanitization/omit-and-flag behavior, recursive grouping semantics,
determinism, prose/table quality, entity resolution, parser-backed validation,
runtime state handling, and regression coverage.

## Decision

Request changes.

## Rationale

- Verified the parser-backed Mermaid harness now works after the `jsdom`
  integration. Direct `node tests/mermaid/validate.mjs` validation succeeded,
  and the parser-backed pytest cases executed instead of failing up front.
- Re-ran targeted and full validation:
  - `.venv/bin/python -m pytest tests/test_diagram_rendering.py -q`
    -> `102 passed`
  - `.venv/bin/python -m pytest tests/test_diagram_analysis.py tests/test_converter_integration.py tests/test_frontmatter.py tests/test_pipeline_integration.py -q`
    -> `187 passed`
  - `.venv/bin/python -m pytest tests -q`
    -> `996 passed, 3 skipped`
- Confirmed several prior findings are fixed:
  - broken Mermaid parser harness
  - rootless group cycle handling
  - unknown direction fallback in Mermaid
  - prose/table cleanup for multiline values and control characters
- Found three remaining correctness issues in `folio/output/diagram_rendering.py`:
  - Mermaid still drops nodes that exist only via `node.group_id` reconciliation.
  - Over-depth group “flattening” stops recursion and silently loses deeper descendants.
  - Non-ASCII/safe-ID collisions are not stable between node emission and edge emission, so edges can point at phantom implicit nodes.
- Found one remaining sanitization gap:
  - Mermaid label sanitization still allows ASCII control bytes through and silently drops unsanitizable technology second lines without flagging review.

## Key Decisions

- Treated runtime correctness over green tests when the current test coverage
  failed to exercise real failure paths.
- Counted parser-harness recovery as a verified fix, not a presumed one.
- Kept the review focused on the scoped PR files and ignored unrelated dirty
  worktree changes outside the review scope.

## Alternatives Considered

- Approve because the full suite is now green. Rejected because direct repros
  still show silent graph loss/corruption in Mermaid output.
- Downgrade the `node.group_id` and depth-limit issues to minor because they
  involve edge cases. Rejected because both violate explicit PR requirements
  and can silently misrepresent extracted graphs.
- Treat the control-character leak as harmless because the current parser
  accepts the output. Rejected because the renderer contract is sanitization
  plus omit-and-flag, not merely “parser does not crash”.

## Consequences

- PR #23 should remain blocked until Mermaid grouping/rendering correctness is
  fixed for reconciled groups, over-depth descendants, and safe-ID collisions.
- Follow-up tests should cover the failing runtime paths, not only nearby
  success cases.

## Impacts

- Prevents merge with a Mermaid renderer that can silently omit regrouped
  nodes, lose deeply nested descendants, or mis-wire edges under ID
  collisions.
- Confirms the parser-backed validation infrastructure is now operational and
  should remain in the test suite.
