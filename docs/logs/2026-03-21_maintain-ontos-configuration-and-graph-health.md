---
id: log_20260321_maintain-ontos-configuration-and-graph-health
type: log
status: active
event_type: chore
source: codex
branch: main
created: 2026-03-21
concepts: [ontos, context-map, agents, metadata-hygiene]
---

# Maintain Ontos configuration and graph health

## Summary

Restored a working root Ontos configuration, removed duplicate graph inputs that
were breaking `ontos map`, normalized a few live documents to the current Ontos
schema, and regenerated the project context artifacts.

## Goal

- Restore `ontos map`, `ontos map --sync-agents`, and `ontos doctor` to a
  working state
- Remove duplicate or generated documents that should not participate in the
  graph
- Leave the repo with a canonical strategic memo path and current AGENTS/context
  artifacts

## Changes Made

- Added a root `.ontos.toml` configured for `docs/` scanning, root context-map
  output, and archive/generated-file exclusions
- Deleted `docs/reference/Ontos_Context_Map.md`, which was a stale generated
  duplicate of the root context map
- Deleted `docs/vision/strategic_direction_memo.md`, leaving
  `docs/product/strategic_direction_memo.md` as the canonical memo path already
  referenced elsewhere in the repo
- Added Ontos frontmatter to `docs/product/strategic_direction_memo.md`
- Normalized `docs/prompts/deep_research_diagram_extraction.md` from obsolete
  `type: prompt` / `status: ready` to current Ontos-compatible metadata
- Normalized `docs/logs/2026-03-15_add-25-regression-tests-for-type-gate-highlights.md`
  from `status: closed` to `status: complete` and added `concepts`
- Regenerated `Ontos_Context_Map.md` and `AGENTS.md`

## Key Decisions

- Used `docs/product/strategic_direction_memo.md` as the canonical strategic
  memo because existing prompt and product-doc references already point there
- Restored a root `.ontos.toml` instead of relying on Ontos defaults so archive
  exclusions and generation targets are explicit again
- Treated the broken duplicate-ID state as the primary maintenance issue; left
  broader graph-hygiene warnings alone because they are longstanding and not
  blocking command health

## Alternatives Considered

- Keeping duplicate docs and trying to suppress them only with broader skip
  patterns. Rejected because the repo would still contain ambiguous canonical
  sources.
- Reintroducing the older `docs_dir = "."` scan scope from the archived config.
  Rejected because the current live documentation set is under `docs/`, and the
  narrower scope avoids scanning root/generated artifacts.
- Running full Ontos maintenance tasks with write actions like log
  consolidation. Rejected for this pass because the immediate goal was repairing
  broken Ontos health without broad unrelated document churn.

## Impacts

- `ontos map` now succeeds
- `ontos map --sync-agents` now succeeds
- `ontos doctor` now passes all checks except a remaining generic validation
  warning
- The canonical strategic memo path is unambiguous again
- Generated context artifacts are back in sync with the repo state

## Testing

- `ontos map`
- `ontos map --sync-agents`
- `ontos agents --force`
- `ontos doctor`
- `ontos doctor --json`
- `ontos maintain --dry-run --verbose`
- `ontos map --strict`
