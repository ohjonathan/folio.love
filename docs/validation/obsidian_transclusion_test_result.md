---
id: obsidian_transclusion_test_result
type: atom
status: active
ontos_schema: 2.2
curation_level: 0
created: 2026-03-16
---

# Obsidian Transclusion Test Result

## Environment

- OS: macOS (darwin 25.3.0)
- Obsidian version: 1.12.4
- Vault path: OneDrive-synced directory

## Checks

| Check | Result |
|-------|--------|
| Source note Mermaid renders | PASS |
| Deck note transcluded Mermaid renders | PASS |
| Deck note transcluded components table renders | PASS |
| Deck note transcluded connections table renders | PASS |
| Edit propagation works | PASS |
| Restart persistence works | PASS |

## Decision

**PASS -> PR 6 uses transclusion (`![[note#section]]`)**

## Notes

- No visual glitches or caveats observed
- Edit propagation was instant (no manual refresh needed)
- Vault is on OneDrive-synced path; no sync-related issues
- Test used synthetic diagram-note and deck-note per the runbook at
  `obsidian-mermaid-transclusion-test.md`

## Test Details

### Synthetic Test

Two synthetic files placed in an existing Obsidian vault:

- `diagram-note.md` — standalone note with Mermaid graph, Components table,
  Connections table
- `deck-note.md` — transcludes all three sections via `![[diagram-note#Section]]`

### Edit propagation

Added a `Cache` node to the Mermaid diagram and a `Cache` row to the
Components table in `diagram-note.md`. Both changes appeared immediately in
`deck-note.md` without manual refresh.

### Restart

Quit Obsidian entirely and reopened. All transclusions rendered correctly on
restart with no degradation.

### Real PR 5 Renderer Test

Generated a diagram note using the actual `graph_to_mermaid()` renderer from
`folio/output/diagram_rendering.py` with a realistic graph:

- 8 nodes across 5 nested subgroups (Frontend Tier, Backend Services,
  Data Layer, Messaging, External Systems)
- Multiple node shapes (database, cache, queue, external, service)
- 7 edges including one bidirectional (`<->`)
- Sanitized labels (parentheses, brackets, special chars stripped by renderer)
- Technology annotations on each node

Result: both the source `real-diagram-note.md` and the transclusion in
`real-deck-note.md` rendered the full complex Mermaid diagram correctly,
including all subgroups and node shapes. No raw code, no blank areas, no
rendering glitches.

This addresses the P3 residual risk that synthetic-only testing did not cover
nested groups and sanitized labels from real PR 5 output.
