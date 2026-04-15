---
id: tier4_discovery_proposal_layer_spec
type: spec
status: draft
ontos_schema: 2.2
created: 2026-04-15
revision: 1
revision_note: |
  Introduces the Tier 4 latent discovery / proposal layer as the explicit
  boundary between probabilistic discovery and canonical graph state.
depends_on:
  - doc_02_product_requirements_document
  - doc_04_implementation_roadmap
  - doc_06_prioritization_matrix
  - folio_ontology_architecture
  - folio_feature_handoff_brief
---

# Tier 4 Discovery / Proposal Layer Spec

## 1. Overview

This spec defines the shared Tier 4 layer that sits between raw managed
content and canonical graph state:

```text
raw evidence -> derived signals -> latent discovery -> proposal / review -> canonical graph
```

The purpose of this layer is to let Folio discover patterns across messy
consulting corpora without allowing probabilistic guesses to become ontology
or canonical graph truth by default.

This spec is proposal-only. It does not commit Folio to a specific storage
engine, vector store, or graph database.

## 2. Goals

The latent discovery / proposal layer must:

1. support non-canonical discovery views such as clusters, similarities,
   candidate links, candidate merges, drift signals, and multimodal groupings
2. package those discoveries into shared proposal objects that existing and
   planned Tier 4 surfaces can consume
3. enforce a hard boundary between probabilistic discovery and canonical graph
   state
4. support rejection memory and stale invalidation so review burden stays
   bounded over time
5. remain compatible with frontmatter + registries as the canonical graph
   source of truth

## 3. Non-Goals

The following are explicitly out of scope for this proposal revision:

| Item | Why deferred |
|------|--------------|
| New CLI command families | Existing and planned surfaces consume shared proposal objects; no additional user-facing CLI is required in this revision. |
| Automatic confirmation of machine suggestions | Review remains explicit. |
| Custom graph database | Canonical state remains frontmatter + registries. |
| Unsupervised schema minting | Discovery may suggest pressure for new concepts or relations, but it does not create ontology terms automatically. |
| Full diagram parsing | Diagram archetype clustering is the bounded first validation track. |
| Locked storage design for proposal objects | A derived sidecar index or proposal store is allowed, but this spec intentionally does not choose one. |

## 4. Canonical Boundary

Folio distinguishes three states:

| State | Role | Canonical? |
|-------|------|------------|
| **Latent discovery layer** | Finds patterns worth reviewing | No |
| **Proposal layer** | Packages those patterns into reviewable assertions | No |
| **Canonical graph state** | Stores governed ontology and reviewed relations | Yes |

Rules:

1. clusters, topics, similarities, and inferred relations are discovery aids,
   not ontology terms on their own
2. proposal objects are non-canonical until explicitly reviewed and promoted
3. canonical graph state remains frontmatter plus registries only
4. any sidecar index or proposal store must be derived and rebuildable
5. probabilistic scoring may influence ranking and surfacing, but not
   canonical writes

## 5. Proposal Object Contract

Every machine-generated Tier 4 suggestion must be representable as a proposal
object with this minimum contract:

| Field | Purpose |
|-------|---------|
| `proposal_type` | What kind of suggestion this is |
| `subject_id` / `source_id` / `target_id` | Identifiers for the nodes or docs involved, as applicable |
| `evidence_bundle` | Concrete source spans, note IDs, pages, images, or matching fields supporting the suggestion |
| `reason_bundle` | Why the suggestion was made (similarity, co-occurrence, merge heuristic, multimodal match, etc.) |
| `trust_bundle` | Trust posture of the supporting inputs and surfaced confidence metadata |
| `schema_gate_result` | Whether the suggestion passes relation / type / cardinality checks required before review |
| `producer` | Which workflow created the proposal |
| `input_fingerprint` | Material basis for staleness detection |
| `lifecycle_state` | Current review state |

The proposal layer may support more fields later, but this minimum contract is
the shared Tier 4 baseline.

## 6. Lifecycle

Minimum lifecycle states:

- `suggested`
- `queued`
- `accepted`
- `rejected`
- `suppressed`
- `stale`
- `expired`
- `superseded`

State expectations:

1. `suggested` means discovery produced the item but it has not yet been
   surfaced for review
2. `queued` means it is eligible for review in an operator-facing surface
3. `accepted` means the suggestion was promoted to canonical graph state
4. `rejected` means it was declined explicitly
5. `suppressed` means it is hidden because rejection memory or policy blocks
   resurfacing
6. `stale` means the proposal's input basis changed materially and the current
   proposal should no longer be trusted without re-evaluation
7. `expired` and `superseded` allow bounded queue management without forcing
   deletion semantics into the spec

## 7. Rejection Memory And Staleness

### 7.1 Rejection Memory

Tier 4 proposal handling must preserve durable rejection memory so bad
suggestions do not recur indefinitely.

At minimum, rejection memory must track:

1. the normalized suggestion identity
2. the rejection decision
3. the proposal's staleness basis at rejection time
4. enough context to determine whether the suggestion is materially the same
   or has changed

Rejected proposals stay suppressed until their staleness basis changes
materially.

### 7.2 Stale Invalidation

Proposal staleness must be triggered by at least:

1. changed upstream inputs
2. entity identity changes such as merges
3. relation-rule or schema-gate changes

This spec does not require semantic stale revalidation for confirmed canonical
links. That remains outside the current proposal revision.

## 8. Trust-Gated Surfacing

Trust-aware graph behavior applies to proposal generation and surfacing, not
only to downstream graph outputs.

Rules:

1. `review_status: flagged` inputs are excluded by default from graph-oriented
   Tier 4 discovery and output surfaces
2. proposals that depend on flagged inputs may exist, but they must surface as
   trust-degraded and remain excluded by default unless an operator chooses
   otherwise
3. `extraction_confidence` is surfaced trust metadata, not a second hard gate
   in v1

## 9. Shared Consumers

Existing and planned Tier 4 surfaces consume the shared proposal layer rather
than inventing independent proposal lifecycles:

- `folio links`
- `folio entities`
- `folio graph`
- `folio digest`
- `folio synthesize`
- `folio search`

This spec does not require these surfaces to expose identical UX, but it does
require them to use the same non-canonical proposal contract and lifecycle
before canonical promotion.

## 10. Validation Workstream

Before broader Tier 4 automation is expanded, Folio should run a bounded
validation workstream over:

1. document relationship proposals
2. entity merge proposals
3. diagram archetype clustering

These are validation tracks, not committed product features in this revision.

### 10.1 Promotion Gates

The validation workstream clears only if:

1. top-ranked proposal acceptance quality is strong enough to trust review
   ordering
2. review burden stays manageable
3. rejection memory suppresses repeated bad suggestions
4. no canonical auto-promotion is introduced
5. diagram clustering proves useful before any full parsing commitment

## 11. Acceptance Criteria

- [ ] Tier 4 docs distinguish canonical graph state from non-canonical latent
      discovery views
- [ ] Proposal objects have one shared minimum contract across Tier 4
- [ ] Proposal lifecycle states, rejection memory, and stale invalidation are
      explicitly defined
- [ ] Trust-aware graph behavior applies to proposal surfacing as well as
      downstream graph outputs
- [ ] The spec does not commit to a custom graph database, automatic
      confirmation, unsupervised schema minting, or full diagram parsing
