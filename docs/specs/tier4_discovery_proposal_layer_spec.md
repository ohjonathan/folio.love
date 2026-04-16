---
id: tier4_discovery_proposal_layer_spec
type: spec
status: draft
ontos_schema: 2.2
created: 2026-04-15
revision: 4
revision_note: |
  Rev 4 (2026-04-15, post Pre-A Round 2): Close the one preserved blocker B-4
  (canonical verdict: docs/validation/v0.6.0_pre_a_proposal_canonical_verdict_round2.md)
  raised by gemini against Rev 3's §9.2 "rolling window" framing — that framing
  required a `rejected_at` timestamp that folio/links.py's `reject_proposal`
  does not write. Rev 4 replaces the rolling-window semantics with a cumulative
  acceptance rate plus a 10-reviewed-proposal warm-up, both computable at query
  time from existing frontmatter without any new persistence, timestamps, or
  producer-state files. Rev 3's B-1, B-2 cap, and B-3 fixes are preserved
  unchanged.
  Rev 3 (2026-04-15, post Pre-A Round 1): Close three blocker findings raised
  by the llm-dev-v1.1 Pre-A.proposal Template 16 review (canonical verdict:
  docs/validation/v0.6.0_pre_a_proposal_canonical_verdict.md):
  - B-1: resolve the §10.1 vs §13.1 gate 4 contradiction on rejected-
    suggestion resurfacing — §10.1 remains a zero-defect product invariant;
    §13.1 gate 4 is now framed as a validation-convergence threshold, not
    a stable-state target.
  - B-2: operationalize the §9 queue cap — reframe as a queued-state cap
    (pending-proposal count) enforceable against current folio/links.py
    structure, with explicit suppression-count diagnostics; acceptance-rate
    gate reframed as rolling-window-based.
  - B-3: define "normalized claim identity" in §7 per proposal_type with
    explicit normalization rules that cross-reference folio/links.py's
    existing basis_fingerprint convention.
  Rev 2 (2026-04-15): Reframe the doc around operator review pain and narrow
  the committed scope to proposal review hardening. Keep latent discovery as
  background architecture and validation framing rather than a standalone
  committed Tier 4 feature.
depends_on:
  - doc_02_product_requirements_document
  - doc_04_implementation_roadmap
  - doc_06_prioritization_matrix
  - folio_ontology_architecture
  - folio_feature_handoff_brief
  - folio_enrich_spec
  - folio_provenance_spec
  - tier4_digest_design_spec
---

# Tier 4 Proposal Review Hardening Spec

## 1. Overview

Folio's long-term graph flow still looks like this:

```text
raw evidence -> derived signals -> latent discovery -> proposal / review -> canonical graph
```

But the committed problem in this spec is narrower and more immediate.
Johnny is reviewing machine-suggested relationships during SteerCo prep. The
same rejected suggestion can recur across reruns. Flagged notes can disappear
from synthesis or search without an obvious operator escape hatch. Review
surfaces can easily turn into noise if proposal identity, trust posture, and
suppression behavior are underspecified.

This spec hardens the proposal and review boundary that existing and planned
Tier 4 surfaces already need. It does not commit Folio to a standalone latent
discovery product slice, a graph database, or any new discovery-specific CLI
family.

## 2. Scope

This spec commits Tier 4 to:

1. one shared non-canonical proposal contract for machine suggestions
2. one explicit lifecycle for review, suppression, and stale handling
3. stable proposal identity and invalidation rules
4. compact operator-facing review rendering
5. bounded queue behavior so proposal volume does not outrun operator value
6. trust-aware surfacing with explicit override and explicit exclusion
   disclosure

Latent discovery remains valid architecture framing and validation context for
future search, clustering, and multimodal experiments, but it is not a
standalone committed requirement in this revision.

## 3. Non-Goals

The following are explicitly out of scope for this proposal revision:

| Item | Why deferred |
|------|--------------|
| Standalone latent-discovery user surface | The immediate product problem is reviewability and governance, not a new discovery UX. |
| New discovery-specific CLI family | Existing and planned surfaces consume shared proposal objects; no separate proposal CLI family is committed here. |
| Automatic confirmation of machine suggestions | Review remains explicit. |
| Custom graph database | Canonical state remains frontmatter plus registries. |
| Unsupervised schema minting | Discovery may surface pressure for new ontology terms, but it does not create them. |
| Locked storage design for proposal objects | A rebuildable sidecar store is allowed later, but this spec does not choose one. |
| Full diagram parsing | Diagram archetype clustering remains a bounded validation track only. |

## 4. Canonical Boundary

Folio distinguishes three layers:

| Layer | Role | Canonical? |
|-------|------|------------|
| **Latent discovery** | Finds patterns worth reviewing | No |
| **Proposal / review** | Packages those patterns into reviewable assertions | No |
| **Canonical graph state** | Stores governed ontology and reviewed relations | Yes |

Rules:

1. clusters, topics, similarities, and inferred relations are discovery aids,
   not ontology terms by themselves
2. proposal objects are non-canonical until explicitly reviewed and promoted
3. canonical graph truth remains frontmatter plus registries only
4. any proposal store or index used later must be derived and rebuildable
5. probabilistic ranking may affect ordering, not canonical writes

## 5. Proposal Object Contract

Every machine-generated Tier 4 suggestion must be representable as a proposal
object with this required contract:

| Field | Purpose |
|-------|---------|
| `proposal_type` | The kind of suggestion being reviewed |
| `source_id` / `target_id` / `subject_id` | IDs for the docs or entities involved, as applicable |
| `evidence_bundle` | Concrete support such as note IDs, spans, pages, screenshots, or matching fields |
| `reason_summary` | Compact operator-facing explanation of why the suggestion exists |
| `trust_status` | Trust posture of the supporting inputs and surfaced confidence metadata |
| `schema_gate_result` | Result of relation-rule checks needed before review |
| `producer` | Which workflow created the suggestion |
| `input_fingerprint` | Material identity used for suppression and stale handling |
| `lifecycle_state` | Current state in the proposal lifecycle |

Optional expanded evidence, reason, or trust payloads may exist, but the
fields above are the minimum shared contract.

## 6. Lifecycle

Required lifecycle states:

- `queued`
- `accepted`
- `rejected`
- `suppressed`
- `stale`
- `superseded`

State meanings:

1. `queued` means eligible for operator review
2. `accepted` means promoted to canonical graph state or accepted as the
   winning identity action
3. `rejected` means explicitly declined by an operator
4. `suppressed` means hidden because rejection memory or policy blocks
   resurfacing
5. `stale` means the material input basis changed and the prior decision can no
   longer be trusted automatically
6. `superseded` means a deterministic rewrite replaced the proposal with an
   equivalent or newer canonical claim

`expired` is not a required core state in this revision.

## 7. Fingerprint And Schema Invalidation

`input_fingerprint` must include:

1. **normalized claim identity** (defined per `proposal_type`):
   - *relationship proposals*: the lexicographically-sorted pair of `source_id` and `target_id` — so `A→B` and `B→A` fingerprint identically for symmetric relation kinds; asymmetric relations carry directionality via the relation-kind qualifier in item 4.
   - *entity-merge proposals*: the lexicographically-sorted set of candidate entity IDs together with `subject_type`.
   - *diagram-archetype proposals*: the lexicographically-sorted member-set identity of the cluster being proposed (stable cluster identity regardless of input ordering).
   - *in all cases*: case-preserving; trailing whitespace normalized; provenance-indicating ID prefixes stripped; identity-indicating ID content retained.
   - *implementation invariant*: the normalization for relationship proposals must match the `basis_fingerprint` convention already in `folio/links.py`. Producers shipping new `proposal_type` values must add a normalization clause to this section in a follow-up spec revision before ingest is enabled for the new type.
2. supporting managed-document IDs
3. each supporting input's current version or source identifiers
4. relation kind
5. producer identity

`input_fingerprint` must exclude:

1. prompt text
2. model identifier
3. tokenizer changes

Relation-rule changes are tracked separately as schema-version invalidation
inside `schema_gate_result`; they are not fingerprint drift.

This matters because the system must suppress repeated bad suggestions without
treating harmless prompt churn as a new proposal.

## 8. Review Rendering Contract

Default operator-facing review surfaces must render:

1. a compact summary
2. a trust label
3. any schema warning
4. one to three concrete evidence locators

Raw bundles belong in expanded detail views or JSON output, not in the default
review row.

The review surface must optimize for fast triage, not for dumping the entire
reasoning trace into the first screen.

## 9. Queue Bounds And Producer Admission

To keep review burden bounded:

1. **Pending-queue cap.** No producer may hold more than 20 proposals in
   lifecycle state `queued` (i.e., awaiting operator review) for a single
   engagement at any time. When a producer attempts to emit a new proposal
   while its pending-queue is already at the cap, the enrichment pipeline
   **must** refuse to enqueue the additional proposal, increment a
   suppression counter, and surface the counter in producer diagnostics
   (`folio enrich diagnose` and equivalent surfaces for later producers).
   This rule is enforceable against the current `folio/links.py` state
   model without new persistence: pending count = length of
   `_llm_metadata.<producer>.axes.relationships.proposals` filtered to
   `lifecycle_state == "queued"`.
2. **Cumulative acceptance-rate gate.** Any producer must sustain a cumulative
   acceptance rate of at least 50% across all its *reviewed* proposals
   (reviewed = lifecycle state moved out of `queued` to `accepted` / `rejected`;
   `suppressed` and `stale` transitions are excluded from the denominator).
   The rate is computed at query time by aggregating `lifecycle_state` values
   from all entries of `_llm_metadata.<producer>.axes.relationships.proposals`
   across all managed documents — **no `rejected_at` timestamp, no global
   chronological ordering, and no new per-producer persistence is required**.
   A 10-reviewed-proposal warm-up applies: the gate does not restrict default
   surfacing until the producer has accumulated at least 10 reviewed proposals
   cumulatively, so newly-introduced producers are not gated on small-sample
   noise. Producers below the gate after warm-up continue to emit proposals,
   but those proposals land in a non-default-surfaced state visible only via
   explicit operator inspection.

   The cumulative framing is a deliberate tradeoff against the rolling-window
   framing of prior revisions: cumulative is less responsive to recent trend
   improvement (a producer that fixed a prior bad patch still carries the tail
   of old rejections in its rate) but is operationally simpler and requires no
   infrastructure the current code does not already provide. If field evidence
   shows the tail drag produces unfair gating for recovered producers, a
   follow-up spec can reintroduce a time-windowed variant once timestamping is
   available.

These are operational guardrails for default surfacing, not a statement that
all proposals above the cap are deleted or forgotten. Suppressed emissions
and non-default-surfaced proposals remain retrievable via explicit operator
queries; they simply do not appear in the default review queue.

**Units (explicit):** "engagement" = one folio library (one client workspace
/ one `folio` root). "Per engagement" means per folio library, not per
client-report or per SteerCo session. The cap is a state cap (pending-queue
size), not a rate cap (per-run or per-time-window), because `folio/links.py`
today does not persist a run counter and this spec explicitly does not
commit to adding one.

## 10. Rejection Memory, Merge Dampener, And Staleness

### 10.1 Rejection memory

Rejected proposals must stay suppressed until the material input basis changes.
Any exact rejected-suggestion resurfacing without material input change is a
**product defect to be fixed, not harmless repetition** — this is the
stable-state invariant. See §13.1 gate 4 for the *validation-phase*
observation threshold (≤5%), which is a convergence tolerance for the
implementation as it hardens, not a relaxation of the stable-state zero-
defect invariant declared here.

### 10.2 Merge dampener

Entity merges complicate proposal identity. When a merge deterministically
rewrites a proposal to the same canonical claim:

1. the old proposal is marked `superseded`
2. the system does not re-queue human review just because the losing entity ID
   disappeared

Only conflicting or semantically changed rewrites become `stale`.

### 10.3 Stale invalidation

At minimum, proposals become `stale` when:

1. supporting managed inputs change materially
2. the canonical claim changes materially after identity rewrite
3. trust posture changes in a way that alters default surfacing

Semantic stale revalidation for already-confirmed canonical links remains out
of scope for this proposal revision.

## 11. Trust-Gated Surfacing

Trust-aware graph behavior applies to proposal surfacing as well as downstream
graph outputs.

Rules:

1. `review_status: flagged` inputs are excluded by default
2. proposals that depend on flagged inputs may exist, but their trust posture
   must surface explicitly
3. committed Tier 4 surfaces must provide an explicit operator override for
   including flagged inputs where that surface is in scope
4. surfaces must disclose excluded flagged-input counts
5. no surface may silently report an empty result when excluded flagged inputs
   are the real cause
6. `extraction_confidence` remains surfaced trust metadata, not a second hard
   exclusion rule in v1

For `folio digest`, the committed override is `--include-flagged`. Equivalent
explicit overrides are part of the requirement for `folio synthesize`,
semantic search, and traversal when those surfaces ship.

## 12. Shared Consumers

Existing and planned Tier 4 surfaces consume the shared proposal contract
rather than inventing independent proposal lifecycles:

- `folio links`
- `folio entities`
- `folio graph`
- `folio digest`
- `folio synthesize`
- `folio search`

This does not require identical UX across those surfaces. It does require the
same non-canonical proposal identity, trust posture, and review semantics.

## 13. Validation Workstream

Folio should run a bounded validation workstream before expanding discovery or
automation further. The workstream covers:

1. document relationship proposals
2. entity merge proposals
3. diagram archetype clustering

These are validation tracks, not committed standalone product features in this
revision.

### 13.1 Validation gates

The workstream clears only if:

1. top-10 document-relationship proposal acceptance rate is at least 60%
2. entity-merge suggestion acceptance rate is at least 75%
3. entity-merge post-accept undo or reopen rate is at most 10%
4. during the validation workstream's observation window, observed rate of
   exact rejected-suggestion resurfacing without material input change is at
   or below 5%. This is a *convergence* threshold — a tolerance for the
   implementation to iterate toward the stable-state invariant in §10.1
   (zero-defect resurfacing). The workstream does not clear at >5% observed
   resurfacing; at ≤5% the workstream clears and the implementation must
   continue driving toward the §10.1 invariant as product work, not
   validation work.
5. median review decision time for top-ranked proposals is at most 30 seconds
6. at least 60% of reviewed top-10 diagram archetype clusters are judged
   useful for navigation or triage
7. no canonical auto-promotion is introduced

## 14. Acceptance Criteria

- [ ] Tier 4 docs distinguish canonical graph state from non-canonical
      proposal handling, with latent discovery kept as background architecture
      rather than a standalone committed feature
- [ ] Proposal objects use one shared minimum contract across Tier 4 with the
      required fields named in this spec
- [ ] Proposal lifecycle, fingerprint inputs and exclusions, schema-version
      invalidation, merge dampening, and queue bounds are explicit
- [ ] Default review rendering is defined as compact summary + trust label +
      schema warning + one to three evidence locators
- [ ] Trust-gated surfacing includes default exclusion, explicit override, and
      excluded-count disclosure
- [ ] The validation workstream has numeric gates for document relationships,
      entity merges, rejection suppression, review speed, and diagram-cluster
      usefulness
- [ ] This spec does not commit Folio to a custom graph database, automatic
      confirmation, unsupervised schema minting, or full diagram parsing
