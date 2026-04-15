---
id: log_20260415_tier-4-proposal-revision-graph-ops-quality-layer
type: log
status: active
event_type: feature
source: codex
branch: main
created: 2026-04-15
---

# Tier 4 proposal revision: graph ops + quality layer

## Summary

Revised the live Tier 4 proposal docs so the roadmap, PRD, prioritization
matrix, and digest design spec all treat the shipped graph-ops layer as the
foundation for later synthesis and discovery work.

## Implementation

Updated the Tier 4 roadmap to frame `folio links`, `folio graph`, entity merge
hygiene, and `folio analysis init` as the shared foundation for future
`digest`, `synthesize`, traversal, and search work.

Added the proposal-level quality layer to the roadmap and prioritization
matrix: `folio enrich diagnose`, trust-aware graph behavior, and
relation-schema validation.

Expanded the PRD's FR-800 family to include the shared graph-ops framing and
new FR-810 through FR-812 quality-layer requirements.

Revised the first-slice digest design spec so it aligns with the proposal:
flagged source-backed inputs excluded by default, trust notes surfaced in the
output, and later digest-generated relationship suggestions routed through
`folio links`.

## Testing

Validated the edited documentation by:

- reading the updated Tier 4 sections in the roadmap, PRD, prioritization
  matrix, and digest design spec for consistency
- regenerating `Ontos_Context_Map.md` and syncing `AGENTS.md` with
  `ontos map --sync-agents`

## Documentation

Updated:

- `docs/product/04_Implementation_Roadmap.md`
- `docs/product/02_Product_Requirements_Document.md`
- `docs/product/06_Prioritization_Matrix.md`
- `docs/specs/tier4_digest_design_spec.md`

## Goal

Revise the Tier 4 proposal so it stays centered on the shipped graph-ops layer
while absorbing the highest-value analysis insights without widening into
implementation work or unrelated follow-ons.

## Key Decisions

- Keep the graph-ops framing and explicitly reject producer-specific
  relationship-review UX such as `folio enrich confirm`.
- Add three proposal-level follow-ons only: `folio enrich diagnose`,
  trust-aware graph behavior, and relation-schema validation.
- Keep canonical graph state in frontmatter plus existing registries rather
  than proposing a separate graph database.
- Preserve the current digest review posture while excluding flagged
  source-backed inputs by default in the first digest slice.

## Alternatives Considered

- Leave the proposal unchanged and treat the analysis as advisory only.
  Rejected because the live roadmap and PRD would remain misaligned with the
  actual graph-ops foundation.
- Reframe the proposal around enrich-specific review commands. Rejected because
  it would duplicate the shared `folio links` surface and create parallel
  workflows for future Tier 4 producers.
- Pull semantic stale revalidation or enrich cost budgeting into this revision.
  Rejected because they are useful later operational follow-ons, not part of
  the current proposal revision.

## Impacts

- The live Tier 4 proposal now says that future machine-suggested
  relationships flow through one shared review path.
- Graph quality and trust posture are now explicit planning concerns before
  deeper synthesis and discovery work lands.
- The first digest spec now aligns with the revised Tier 4 proposal instead of
  drifting from it.
