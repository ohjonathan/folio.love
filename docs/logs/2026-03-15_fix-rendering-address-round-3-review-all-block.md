---
id: log_20260315_fix-rendering-address-round-3-review-all-block
type: log
status: active
event_type: pr-23-reviewer-2-alignment-review-rerun-head-6a83d3a
source: cli
branch: codex/diagram-pr5-rendering
created: 2026-03-15
---

# fix(rendering): address Round 3 review — all block

## Goal

Review PR #23 rerun at `6a83d3a` against base `97f03b9` for proposal
alignment, PR 4 runtime compatibility, backward compatibility, and
verification that previously reported renderer deviations were actually fixed.

## Key Decisions

- Re-ran Ontos activation and reloaded only the PR 5 rendering prompt,
  proposal, PR 4 extraction prompt, prior alignment review log, prior peer
  review log, and PR 22 extraction-fix log.
- Treated the live PR 4 runtime as authoritative where it diverges from the
  older proposal text, especially for edge directions and `regroup`
  semantics.
- Counted the Mermaid parser harness as fixed after direct `node
  tests/mermaid/validate.mjs` validation and a full green test suite with the
  parser-backed tests enabled.
- Counted `group_id`-only regroup rendering as still broken because Mermaid
  can silently drop regrouped nodes when `group.contains` is stale.
- Counted sanitization as still drifting from the approved proposal because
  unsanitizable node labels still render as fallback IDs instead of being
  omitted from Mermaid.

## Alternatives Considered

- Approve because the previously reported parser, unknown-direction, and
  rootless-cycle issues are resolved. Rejected because the regrouped-node
  rendering bug breaks alignment with the live PR 4 runtime, and the
  sanitization behavior still does not match the proposal's omit-and-flag
  contract.
- Ignore the regroup issue as test-only because the component table handles
  `node.group_id`. Rejected after direct repro showed Mermaid output can
  become effectively empty for a regrouped node while the table still shows it
  as grouped.

## Impacts

- Verified scoped diff remained limited to:
  - `folio/output/diagram_rendering.py`
  - `folio/pipeline/analysis.py`
  - `folio/converter.py`
  - `tests/mermaid/package.json`
  - `tests/mermaid/validate.mjs`
  - `tests/test_diagram_rendering.py`
- Ran:
  - `.venv/bin/python -m pytest tests/test_diagram_rendering.py -q`
    -> `102 passed`
  - `.venv/bin/python -m pytest tests/test_diagram_analysis.py tests/test_converter_integration.py tests/test_frontmatter.py tests/test_pipeline_integration.py -q`
    -> `187 passed`
  - `.venv/bin/python -m pytest tests -q`
    -> `996 passed, 3 skipped`
  - `printf 'graph TD\n  A --> B\n' | node tests/mermaid/validate.mjs`
    -> exit `0`
- Direct repros on current head:
  - Unknown directions now render conservatively as undirected with an
    uncertainty.
  - Rootless group cycles now flatten instead of silently dropping all nodes.
  - Unsanitizable labels still render fallback IDs in Mermaid.
  - Nodes grouped only via `node.group_id` can disappear from Mermaid because
    subgraph bodies still iterate `group.contains`.
