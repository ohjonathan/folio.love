---
id: log_20260415_tier-4-graph-ops-layer
type: log
status: active
event_type: feature
source: codex
branch: main
created: 2026-04-15
---

# Tier 4 graph ops layer

## Summary

Implemented the Tier 4 graph operations layer around canonical note relationships,
graph health inspection, entity identity hygiene, and managed analysis note
initialization.

## Implementation

Added `folio links` review/confirm/reject flows for standardized relationship
proposals stored under `_llm_metadata.<producer>.axes.relationships.proposals`.
Confirmation now promotes canonical frontmatter links and records confirmation
audit metadata under `_llm_metadata.links.confirmed_relationships`, while
rejection preserves suppression state through `basis_fingerprint`.

Added `folio graph status` and `folio graph doctor` to report pending proposals,
zero-link docs, orphaned canonical targets, enrich-protected notes, entity
confirmation/stub gaps, duplicate-person candidates, and stale analysis
artifacts from stored graph input fingerprints.

Extended entity operations with deterministic person merge suggestions and a
person merge command that rewrites internal references, absorbs loser aliases
into the winner, and relies on forced stub regeneration to remove stale
auto-generated loser stubs while preserving manual stubs.

Added `folio analysis init` for managed source-less analysis notes, including
registry integration, default review metadata, validated `draws_from` /
`depends_on` inputs, and graph input fingerprinting for stale detection.

## Testing

Ran:

- `python3 -m pytest tests/test_enrich_data.py tests/test_links_cli.py tests/test_graph_cli.py tests/test_analysis_docs.py tests/test_provenance_cli.py tests/test_cli_entities.py tests/test_enrich.py tests/test_enrich_integration.py tests/test_context.py -q`

Result: `196 passed`

## Documentation

Added focused regression coverage for the new CLI surfaces and registry flows in
`tests/test_links_cli.py`, `tests/test_graph_cli.py`, and
`tests/test_analysis_docs.py`. Updated existing entity, provenance, enrich, and
context coverage to reflect the new proposal schema and managed-analysis
behavior.

## Goal

Ship the Tier 4 delta needed to make ontology and knowledge-graph operations
explicit, reviewable, and inspectable before higher-level digest and synthesis
features build on top of them.

## Key Decisions

- Keep canonical graph state in note frontmatter and existing registries instead
  of introducing a separate graph store.
- Reuse the existing proposal-review pattern from provenance for document-level
  relationship confirmation and rejection.
- Treat analysis notes as source-less managed documents, matching the existing
  context-note pattern.
- Preserve manual entity stubs during merge cleanup and surface them as operator
  follow-up instead of deleting them.

## Alternatives Considered

- Auto-confirming model-suggested relationships: rejected because it bypasses
  the explicit human review gate.
- Rewriting existing note bodies during person merge: deferred to keep this
  slice low-risk and registry-focused.
- Building a graph database or separate relationship registry: deferred because
  frontmatter plus registries already provide the canonical state needed for
  this slice.

## Impacts

- `digest` / `synthesize` now have a concrete review surface to target for
  relationship proposals instead of inventing parallel state.
- Operators can inspect graph health and stale analysis artifacts before
  compounding issues into downstream synthesis work.
- Entity cleanup is safer because merges now carry alias lineage forward and
  stub regeneration removes stale auto-generated loser notes without touching
  manual notes.
