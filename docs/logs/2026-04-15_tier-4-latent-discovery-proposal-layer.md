---
id: log_20260415_tier-4-latent-discovery-proposal-layer
type: log
status: active
event_type: tier-4-latent-discovery-proposal-layer-proposal-revision
source: codex
branch: codex/tier4-latent-discovery-proposal-layer
created: 2026-04-15
---

# Tier 4 latent discovery proposal layer

## Summary

Revised the Tier 4 proposal so Folio explicitly distinguishes non-canonical
latent discovery / proposal handling from canonical ontology / graph state.
Updated the PRD, roadmap, prioritization matrix, ontology architecture, and
digest spec, and added a dedicated Tier 4 discovery / proposal layer spec.

## Changes Made

- Added FR-813 and FR-814 to the Tier 4 PRD for the latent discovery layer and
  shared proposal object lifecycle
- Revised existing Tier 4 PRD requirements so related links, synthesize,
  semantic search, trust behavior, and relation validation build on the shared
  proposal layer
- Added F-414 and F-415 to the prioritization matrix and Tier 4 roadmap
- Added a bounded validation workstream for document relationship proposals,
  entity merge proposals, and diagram archetype clustering
- Added explicit canonical-boundary language to the ontology architecture
- Added `docs/specs/tier4_discovery_proposal_layer_spec.md`
- Aligned the digest spec to reference the shared proposal lifecycle

## Testing

Documentation consistency review only:
- verified FR and F crosswalk updates
- verified shared terminology (`latent discovery layer`, `proposal layer`)
- checked that the docs keep canonical state as frontmatter + registries

## Goal

Update the Tier 4 proposal so latent discovery and proposal handling are
explicitly defined as non-canonical foundations that feed human review before
any graph promotion.

## Key Decisions

- Keep canonical graph truth as frontmatter plus registries only
- Define a non-canonical latent discovery layer and shared proposal layer
- Add FR-813 / FR-814 and F-414 / F-415 rather than burying the concept inside
  existing Tier 4 features
- Keep the bounded experiments as a validation workstream, not committed
  product features
- Leave proposal-layer storage technology unspecified in the proposal

## Alternatives Considered

- Folding the discovery / proposal concept into existing FRs without adding new
  requirement IDs
- Limiting the update to PRD / roadmap docs only
- Committing the validation tracks as new Tier 4 product features immediately

## Impacts

- Clarifies the boundary between probabilistic discovery and canonical
  ontology growth
- Gives Tier 4 a reusable proposal contract that later search and synthesis
  work can build on
- Keeps Folio aligned with the existing graph-ops foundation without adding new
  CLI commitments or a graph database dependency
