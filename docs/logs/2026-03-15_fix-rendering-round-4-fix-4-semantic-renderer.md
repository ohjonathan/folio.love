---
id: log_20260315_fix-rendering-round-4-fix-4-semantic-renderer
type: log
status: active
event_type: 2026-03-15_pr23-reviewer1-peer-review-rerun-head-172c51a
source: codex
branch: codex/diagram-pr5-rendering
created: 2026-03-15
---

# fix(rendering): Round 4 — fix 4 semantic renderer 

## Context

Peer review rerun for PR #23 on branch `codex/diagram-pr5-rendering` at
`172c51a`, compared against base `97f03b9`, after the prior rerun review at
`6a83d3a` requested follow-up on renderer correctness and Mermaid validation
behavior.

## Goal

Verify whether the new Round 4 changes actually close the previously reported
gaps, with emphasis on Mermaid completeness, sanitization / omit-and-flag,
recursive nesting and depth-limit behavior, determinism, prose and table
quality, parser-backed validation, runtime state handling, and regression
coverage.

## Decision

Request changes.

## Key Decisions

- Re-ran Ontos activation and reviewed the Tier 1 map, proposal sections
  11-13, the PR 5 rendering prompt, and the prior rerun review logs before
  re-checking the code.
- Treated the approved proposal and live PR 5 prompt as the contract, not the
  PR description.
- Counted the parser-backed Mermaid harness as still healthy based on a green
  parser-backed pytest run and a direct `node tests/mermaid/validate.mjs`
  smoke check.
- Counted the current head as fixing the prior safe-ID collision issue, the
  normal-depth `node.group_id` regroup rendering issue, and the general
  descendant-loss issue for over-depth groups that still use `group.contains`.
- Counted the PR as still not merge-ready because direct repros exposed three
  remaining contract gaps: regrouped nodes still disappear when they are both
  depth-overflowed and represented only via `node.group_id`, unsafe Mermaid
  technology labels are still silently dropped without omit-and-flag review
  signaling, and connection tables still render unknown directions as `?`
  instead of a conservative unknown form.

## Alternatives Considered

- Approve because the full suite is now green. Rejected because targeted
  runtime repros still show silent diagram corruption / contract drift in
  Mermaid and connection-table output.
- Downgrade the unsafe-technology and unknown-direction issues to test-only
  disagreements. Rejected because the runtime output itself suppresses or
  distorts graph information without review signaling.
- Treat the depth-overflow regroup bug as already fixed by the new recursion
  logic. Rejected after reproducing that the fix does not cover the live PR 4
  `node.group_id` regroup path once the group is flattened for depth safety.

## Impacts

- Ran:
  - `.venv/bin/python -m pytest tests/test_diagram_rendering.py -q`
    -> `108 passed`
  - `.venv/bin/python -m pytest tests/ -q`
    -> `1002 passed, 3 skipped`
  - `printf 'graph TD\n  A --> B\n' | node tests/mermaid/validate.mjs`
    -> exit `0`
- Direct repros on current head:
  - Unsafe technology `()` renders as `graph TD` with the node still present,
    but returns no uncertainty and leaves `review_required=False`.
  - A regrouped node assigned only via `node.group_id` still disappears when
    it lives below the depth limit, and an edge to it produces an implicit
    phantom Mermaid node instead of a flattened explicit node.
  - An edge direction like `"mystery"` renders as `?` in the connection table
    instead of a conservative unknown / none symbol.
- The incremental code changes since `6a83d3a` are limited to
  `folio/output/diagram_rendering.py`, `tests/test_diagram_rendering.py`, and
  docs; parser tooling, converter integration, and analysis serialization were
  unchanged in this rerun.
