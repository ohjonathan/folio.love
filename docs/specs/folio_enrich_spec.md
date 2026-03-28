---
id: folio_enrich_spec
type: spec
status: draft
ontos_schema: 2.2
created: 2026-03-28
revision: 4
revision_note: |
  Rev 4: Clarify `basis_fingerprint` composition for relationship proposals.
depends_on:
  - doc_02_product_requirements_document
  - doc_04_implementation_roadmap
  - folio_ontology_architecture
  - v0.5.0_tier3_ingest_spec
  - v0.5.1_tier3_entity_system_spec
  - tier3_baseline_decision_memo_20260327
  - tier2_real_library_rerun_report
  - tier2_real_vault_validation_report
  - tier3_kickoff_checklist
---

# `folio enrich` Core Spec

## 1. Overview

This spec defines **PR C: `folio enrich` core**, the next Tier 3 slice after
the shipped interaction-ingest and entity-system baseline.

`folio enrich` is a post-hoc LLM enrichment pass over **existing,
registry-managed notes**. It operates on notes that already exist in the
library and adds structure that was unavailable or intentionally deferred at
conversion/ingest time:

1. additive tag enrichment
2. entity backfill using the shipped entity registry and resolver contract
3. conservative relationship proposals plus a generated `## Related` section
   derived from canonical frontmatter relationships

This is **not** the implementation prompt. It is the feature spec that freezes
scope, interfaces, safety rules, and review boundaries before implementation.

**Output path:** `docs/specs/folio_enrich_spec.md`

**Naming rationale:** this spec intentionally uses a stable, unversioned file
name because it defines the dedicated PR C feature slice that will feed a
follow-on PRD patch and then an implementation prompt.

---

## 2. Why This Slice Comes Next

Late-March validation changed the Tier 3 baseline in three important ways:

1. `folio ingest` is already shipped on `main` (PR #32).
2. The entity registry and ingest-time resolution model are already shipped on
   `main` (PR #34 / PR #35).
3. The real-library rerun and the real-vault validation passed the
   **production `anthropic_sonnet4` library plus 12 blind-validated
   `haiku45` merges** to PR C.

The product is therefore no longer at the stage of inventing Tier 3 from
scratch. The missing piece is now **post-hoc structure over the existing
library**:

- tags are present but may be sparse or inconsistent
- pre-entity-system evidence notes do not carry entity wikilinks
- ontology relationship fields exist in schema but are mostly empty in real
  notes
- interaction notes ship with `impacts: []` stubs that need later enrichment

PR C is the smallest slice that materially improves the shipped baseline
without collapsing into the much harder PR D provenance problem.

---

## 3. Goals

1. Add a new CLI surface:
   `folio enrich [scope] [--dry-run] [--llm-profile <profile>] [--force]`.
2. Re-analyze existing evidence and interaction notes for **additive-only**
   tag enrichment.
3. Reuse the shipped entity-registry and resolution model to backfill entity
   wikilinks into existing notes.
4. Populate conservative, reviewable relationship proposals without making
   canonical relationship fields machine-owned.
5. Generate a `## Related` section from **canonical** relationship
   frontmatter, keeping frontmatter as the source of truth.
6. Make reruns safe by default through explicit idempotency markers, per-file
   skip behavior, and conservative human-edit protection.
7. Keep runtime behavior practical for the current production-scale library:
   115 registry decks, 160 evidence notes, 1,524 diagram notes, and 1,684
   total markdown files.

---

## 4. Non-Goals

These are explicitly out of scope for PR C:

| Item | Why deferred |
|------|--------------|
| Retroactive provenance linking | PR D. Document-level enrichment comes first; claim-level evidence matching is a separate reviewability problem. |
| Context document generation | PR E. |
| Cross-engagement enrichment | Tier 4 / later Tier 3 integration work only. |
| Diagram-note enrichment | Diagram notes are not registry-managed and already have a separate note model. |
| Relationship confirmation CLI | PR C uses manual confirmation through frontmatter edits. |
| Machine-written canonical relationship fields | PR C stores proposals in metadata only. Canonical fields remain human-owned. |
| Auto-clearing existing `review_status: flagged` | Enrich does not redefine the underlying review-state model. |
| Mandatory stale source-path repair | Important adjacent cleanup, but not required for PR C correctness. |
| Per-stage routing implementation | `routing.enrich` is added; stage splitting is still deferred. |
| New entity arrays in top-level frontmatter | Not anticipated by the ontology or current PRD. |
| Entity markdown stub files | Nice-to-have, not necessary for PR C. |
| Manual wikilink promotion from arbitrary body text | The ontology names this as a `folio enrich` responsibility in sections 2.6 and 6.3, but PR C deliberately defers it because v1 keeps frontmatter authoritative and avoids rewriting arbitrary user-authored links before override persistence exists. |
| Rewriting verbatim extracted evidence text, evidence quotes, or raw transcripts | Unsafe in v1. |
| `folio status` enrichment-state reporting | Deferred because PR C keeps enrich durability in note frontmatter and does not extend `registry.json`. |
| Per-note enrich opt-out switch | Deferred; v1 uses scope narrowing or non-L0 curation to keep notes out of body mutation. |
| `--max-calls` or budget stop valve | Deferred; Rev 3 adds pre-run call estimates but not budget enforcement. |

---

## 5. Current Shipped Baseline

### 5.1 Operational baseline

PR C starts from the validated production library recorded in the late-March
decision memo and vault validation:

- production baseline: `anthropic_sonnet4`
- plus 12 blind-validated `haiku45` merges
- 115 registry decks
- 160 evidence notes
- 1,524 diagram notes
- 1,684 total markdown files
- 0 YAML parse errors
- 0 broken inline images

This production library, not the full `haiku45` scratch rerun, is the only
approved enrich baseline.

### 5.2 Registry and document baseline

Verified against the current codebase:

1. `registry.json` tracks **evidence** and **interaction** documents.
2. Diagram notes are separate markdown assets and are not represented in
   `registry.json`.
3. Evidence notes already carry:
   - `tags`
   - `review_status`, `review_flags`, `extraction_confidence`
   - `grounding_summary`
   - `_llm_metadata.convert`
4. Evidence notes do **not** currently emit `depends_on`, `draws_from`,
   `relates_to`, `supersedes`, `instantiates`, or enrich-specific metadata.
5. Interaction notes already carry:
   - `impacts: []`
   - `tags`
   - `source_transcript`
   - `_llm_metadata.ingest`
   - canonical or unresolved entity wikilinks in the body
6. `entities.json` exists as the only shipped entity store.
7. `folio/pipeline/entity_resolution.py` implements the approved v1 entity
   policy:
   - confirmed-only exact match
   - confirmed-only alias match
   - bounded LLM soft-match proposal
   - unresolved auto-create as unconfirmed
8. `folio refresh` preserves tags indirectly by feeding existing `tags` back
   into conversion, but it does **not** preserve manually added relationship
   fields. This is a known compatibility limitation inherited from the current
   conversion path.

### 5.3 Relationship and ontology baseline

The ontology remains authoritative:

- `supersedes` applies to all document types
- `impacts` applies to interaction documents
- `depends_on` and `draws_from` apply to analysis / deliverable documents
- `relates_to` and `instantiates` exist in the ontology but are explicitly too
  noisy or too broad for PR C v1

Because PR C is scoped to registry-managed **evidence** and **interaction**
notes, the current corpus realistically activates:

- `supersedes` for evidence notes
- `impacts` for interaction notes

This is a **priority reordering**, not a schema amendment. The ontology's
field table in section 12.3 already allows `supersedes` on `all` document
types, but section 6.4 recommends starting v1 with `depends_on`,
`draws_from`, and `impacts`. PR C deliberately reorders that recommendation
because the current registry-managed corpus is evidence plus interaction only;
there are no registry-managed analysis or deliverable notes yet to support a
high-signal `depends_on` / `draws_from` pass.

The machinery must stay compatible with future `depends_on` / `draws_from`
work, but PR C does not invent ontology-external relationships to force them
into the current evidence/interaction corpus.

---

## 6. Key Decisions

### D1: Registry-managed evidence and interaction notes only

`folio enrich` processes only documents present in `registry.json` with
`type: evidence` or `type: interaction`.

Diagram notes are explicitly skipped in v1 because:

- they are not registry-managed
- they already have their own note lifecycle and freeze semantics
- including them would multiply PR C surface area without materially improving
  the next Tier 3 milestone

### D2: Add `routing.enrich`, not per-stage enrich routing

PR C adds a single new task route, `routing.enrich`, with the same resolution
semantics already used by `convert` and `ingest`:

1. `--llm-profile` override
2. `routing.enrich.primary`
3. `routing.default.primary`

Fallback behavior also mirrors the existing contract:

- route-configured fallbacks apply only when `--llm-profile` is not used
- `--llm-profile` disables fallback for that invocation

### D3: Registry-first discovery, incremental processing, and serialized axes

Discovery is registry-first:

- bootstrap or rebuild `registry.json` if missing or corrupt
- filter registry entries by scope
- process one document at a time
- never require the entire library to be loaded into memory

Per-document execution is serialized, not parallel:

1. parse the current note into a heading-aware structure
2. compute eligibility and idempotency fingerprints
3. skip unchanged notes before any enrich analysis runs
4. run one primary note-scoped enrich analysis pass that returns tag
   candidates, entity mention candidates, and relationship cues from the
   current note
5. run deterministic entity resolution
6. run a bounded relationship proposal pass only when the document is eligible
   and relationship cues exist
7. merge frontmatter and rewrite managed sections if safe

Relationship inference may read peer registry entries in the same
client/engagement scope, but enrich never writes outside the requested scope.
In v1, peer reads are limited to registry data, canonical frontmatter, and
lightweight document descriptors already available without loading full peer
bodies into the LLM context. Those peer descriptors are limited to title,
type, tags, canonical relationship fields, source-lineage metadata, and
`grounding_summary`.

### D4: Tags are additive-only in v1

PR C may:

- propose and merge new tags
- normalize duplicates
- preserve existing tags

PR C may **not**:

- remove existing tags
- rewrite human-added tags away
- enforce hard vocabulary failures

### D5: Reuse the shipped resolver policy, not a second algorithm

PR C must reuse the current entity-resolution policy already implemented for
ingest. The implementation may factor shared helpers out of the current
interaction-shaped path or adapt the entrypoint for evidence notes, but it may
not define a second resolution policy.

This means enrich-time entity backfill uses the same semantics as ingest-time
resolution:

- confirmed exact match
- confirmed alias match
- bounded LLM soft-match proposal
- unconfirmed auto-create when unresolved
- no algorithmic fuzzy matcher

### D6: Ontology-bounded relationship modeling with corpus-driven priority
ordering

PR C stays within the ontology's allowed relationship vocabulary while making a
corpus-driven priority reordering inside that vocabulary.

Specifically:

- interaction notes do **not** receive canonical `draws_from`
- interaction relationship population in PR C uses `impacts`
- `draws_from` and `depends_on` remain reserved for ontology-eligible document
  types only

This keeps PR C from silently changing the ontology by implementation.

### D7: Canonical relationship fields remain human-owned

PR C does **not** write machine proposals directly into canonical relationship
fields.

Instead:

- canonical fields stay authoritative and human-owned
- machine proposals live under `_llm_metadata.enrich.axes.relationships`
- human confirmation happens by editing canonical frontmatter fields manually

This keeps machine suggestions distinguishable from confirmed graph state.

### D8: `## Related` is derived from canonical frontmatter only

PR C generates a `## Related` section from canonical relationship fields only.
It does **not** render pending machine proposals into the body in v1.

This avoids a confusing state where the body appears to confirm relationships
that still exist only as proposals.

If no canonical relationship targets resolve, enrich omits `## Related`
entirely and removes any stale previously generated section on rerun.

Placement is fixed in v1:

- evidence notes: immediately before `## Version History`, or at end-of-note
  when no version-history section exists
- interaction notes: immediately after `## Impact on Hypotheses` and before the
  raw transcript callout

### D9: Idempotency uses explicit fingerprints

PR C stores four enrich-specific control fields under `_llm_metadata.enrich`:

1. `input_fingerprint`
2. `managed_body_fingerprint`
3. `entity_resolution_fingerprint`
4. `relationship_context_fingerprint`

`input_fingerprint` is the skip marker. It is computed from:

- normalized current note content with prior enrich-managed output stripped
- current `entity_resolution_fingerprint`
- current `relationship_context_fingerprint`
- the resolved enrich profile name
- enrich spec version

`entity_resolution_fingerprint` is note-scoped. It is derived from the note's
stored enrich entity mentions and their current resolution outcomes in
`entities.json`:

- `confirmed:<type>/<key>`
- `unconfirmed:<type>/<key>`
- `proposed_match:<type>/<key>`
- `unresolved`

`relationship_context_fingerprint` is narrow by design. It is derived only
from the note's own canonical relationship targets plus the proposal targets
already recorded for that note, including their current source/version
identifiers. A new peer note elsewhere in the same engagement does not force
automatic reruns for every sibling note.

If the current `input_fingerprint` matches the stored one, enrich skips the
document as unchanged unless `--force` is used. Notes with
`_llm_metadata.enrich.status: stale` never short-circuit on fingerprint match;
they always require a fresh enrich run.

`managed_body_fingerprint` protects machine-owned sections. If those sections no
longer match the last enrich output, PR C reports a conflict and skips body
mutation.

### D10: Body mutation is allowed only inside machine-owned sections selected by
heading-aware parsing

PR C may rewrite body content only inside clearly machine-owned sections.

Implementations must use heading-aware parsing, a markdown AST, or an
equivalent subtree-selection strategy. Regex-only global search/replace is not
acceptable for v1 because older notes and overridden notes may not share a
homogeneous layout.

Allowed mutation surface:

- evidence notes:
  - each per-slide `### Analysis` subtree, stopping at the next heading that
    exits that subtree
  - generated trailing `## Related`
- interaction notes:
  - exact top-level `## Entities Mentioned`
  - exact top-level `## Impact on Hypotheses`
  - generated trailing `## Related`

Protected surface:

- evidence `### Text (Verbatim)` blockquotes
- evidence quote spans under `**Evidence:**`
- interaction `## Summary`
- interaction full `## Key Findings` subtree, including `### Claims`,
  `### Data Points`, `### Decisions`, and `### Open Questions`
- interaction `## Quotes / Evidence` quoted content
- interaction raw transcript callout
- any manual content outside enrich-managed sections

### D11: Human-edit protection is conservative

PR C skips body mutation and reports a conflict when any of the following are
true:

- `curation_level` is `L1`, `L2`, or `L3`
- `review_status` is `reviewed` or `overridden`
- current managed sections do not match the stored
  `managed_body_fingerprint`

When body mutation is skipped, PR C may still safely perform non-destructive
work:

- additive tag updates
- `_llm_metadata.enrich` updates
- entity-registry updates
- relationship proposal metadata updates

If heading-aware parsing cannot identify the expected managed sections for a
note, PR C treats the body as protected rather than conflicted:

- emit a warning
- skip all body mutation for that note
- still allow metadata-only and additive frontmatter updates
- continue the batch

### D12: Enrich state is durable across `folio refresh`, and review-state
semantics do not get redefined by enrich

PR C cannot treat enrich state as disposable if human-confirmed relationships
or prior enrich provenance would then be silently destroyed by `folio refresh`.

Minimum compatibility requirement:

- `folio refresh` must read the existing note frontmatter before re-conversion
- the refresh path must regenerate the note normally, then pass through only:
  - canonical relationship fields (`depends_on`, `draws_from`, `impacts`,
    `relates_to`, `supersedes`, `instantiates`)
  - `_llm_metadata.enrich`
- this is a **frontmatter passthrough**, not a sidecar and not a free-form
  merge of arbitrary legacy fields
- if refresh rewrites a note without a source change, the passed-through enrich
  block may remain unchanged
- if a source-changing refresh invalidates enrich-managed content, it must:
  - set `_llm_metadata.enrich.status: stale`
  - clear `input_fingerprint`, `managed_body_fingerprint`,
    `entity_resolution_fingerprint`, and `relationship_context_fingerprint`
  - clear relationship proposal records
  - preserve human-confirmed canonical relationship fields
  - regenerate or remove `## Related` from preserved canonical frontmatter only

This makes enrich state durable while still allowing refresh to invalidate
outdated machine proposals safely.

PR C does not auto-promote a document from `flagged` to `clean` just because
enrich ran successfully.

Existing review flags remain authoritative unless a later, explicit workflow
resolves the underlying cause. Enrich is additive structure, not a review-state
reset button.

### D13: Stale source-path repair is adjacent, not core

The real-vault validation found stale evidence-note source paths and a broad
review-state surface. Both matter, but neither is required for PR C to be
correct.

The vault-validation recommendation explicitly says PR C should fix the 148
legacy-root source references. Rev 3 acknowledges that recommendation and
treats stale-path repair as a deterministic PR C companion cleanup or
refresh/migration sub-deliverable, not as an LLM enrich axis.

### D14: Registry contract stays unchanged

PR C does not mirror tags, entities, relationship payloads, proposal detail,
or enrich timestamps into `registry.json`.

`registry.json` remains a discovery and path-resolution index. Durable enrich
state lives only in note frontmatter under `_llm_metadata.enrich`.

### D15: Batch behavior follows `folio batch` expectations

PR C is long-running and mutates existing notes, so it must:

- show pre-run note counts and estimated call counts
- show progress
- continue on per-file failures
- produce a final summary
- exit non-zero if any per-file failures occurred

---

## 7. CLI Contract

### 7.1 Command shape

```bash
folio enrich [scope] [--dry-run] [--llm-profile <profile>] [--force]
```

### 7.2 Scope semantics

`scope` is optional and follows the same matching pattern used by
`folio status` and `folio refresh`:

- client prefix
- engagement prefix
- any library-relative path prefix

Examples:

```bash
folio enrich
folio enrich ClientA
folio enrich ClientA/DD_Q1_2026
folio enrich ClientA/DD_Q1_2026/market_sizing
```

Write scope is limited to matching registry entries. Relationship inference may
inspect same-client / same-engagement peers outside the exact path scope, but
it never writes to those peer notes.

### 7.3 Routing and override behavior

- default route: `routing.enrich.primary`
- fallback route: `routing.default.primary`
- `--llm-profile` bypasses route resolution and disables fallback
- `--force` bypasses fingerprint-based skip and stale short-circuiting for
  eligible notes, but still respects protected-body rules and rejected
  proposal suppression when the rejection basis is unchanged

### 7.4 `--dry-run`

`--dry-run` executes only the deterministic setup path and prints what would
happen, but it writes nothing to:

- markdown notes
- `registry.json`
- `entities.json`

Dry-run also makes **no LLM calls** in v1. It reports:

- which documents are in scope
- which documents would be analyzed
- which documents would be skipped as unchanged
- which documents would be protected
- which documents would be conflicted

Dry-run intentionally does **not** preview exact proposed tags, entities, or
relationships. That keeps it useful for cost-free scoping and pipeline
validation on large libraries.

### 7.5 Progress and summary output

Minimum output requirements:

```text
Scope: 42 eligible document(s)
Estimated calls: primary=42 relationship<=17
Enriching 42 document(s)...
✓ clienta_ddq126_evidence_20260327_market-sizing  tags:+2 entities:+1 proposals:1
↷ clienta_ddq126_evidence_20260320_market-sizing  unchanged
! clienta_ddq126_interaction_20260321_cto-sync   protected; metadata only
! clienta_ddq126_interaction_20260319_ops-sync   conflict; metadata only
✗ clienta_ddq126_evidence_20260318_failover      <error>

Enrich complete: 18 updated, 20 unchanged, 2 protected, 1 conflicted, 1 failed
Dry run: 18 would_analyze, 20 would_skip, 2 would_protect, 1 would_conflict
```

### 7.6 Exit behavior

- exit `0` when all eligible documents succeed or are skipped
- exit non-zero when any per-file failures occur
- exit non-zero immediately for fatal setup failures (invalid config, unreadable
  registry, invalid LLM profile, etc.)

---

## 8. Eligibility and Candidate Discovery

### 8.1 Registry bootstrap behavior

If `registry.json` is missing, enrich bootstraps it from the library in the
same style as `status` / `refresh`.

If `registry.json` is corrupt, enrich rebuilds it before processing any notes.

### 8.2 Eligible note types

Eligible:

- `type: evidence`
- `type: interaction`

Skipped:

- `type: diagram`
- any note not present in `registry.json`
- any unsupported future type not explicitly added to enrich eligibility

Because discovery is registry-first, diagram notes are excluded at eligibility
time rather than surfaced as per-file skip rows.

### 8.3 Relationship candidate pool

Relationship inference is limited to notes that share:

- the same library
- the same `client`
- the same `engagement`

If `client` or `engagement` is missing on a document, enrich still runs tag and
entity axes, but the relationship axis is skipped for that document.

Peer context is intentionally bounded in v1. Relationship evaluation may use:

- peer registry identity and path data
- peer titles and document types
- peer canonical relationship fields
- peer tags
- peer source-lineage metadata
- peer grounding summaries already available in frontmatter

It does not load arbitrary full peer bodies into the LLM context.

---

## 9. Data Model Changes

### 9.1 Canonical frontmatter remains ontology-native

PR C reuses existing frontmatter fields. It does **not** introduce new
top-level enrich-specific fields.

Canonical fields that enrich may update directly:

- `tags` (additive merge only)

Canonical relationship fields are human-confirmed inputs that enrich may read,
preserve during refresh passthrough, and re-render into `## Related`. Enrich
does **not** machine-write proposals into those canonical fields.

Canonical fields that enrich does **not** machine-write as proposals:

- `depends_on`
- `draws_from`
- `impacts`
- `relates_to`
- `supersedes`
- `instantiates`

These remain human-owned. PR C proposal data lives in metadata only.

### 9.2 `_llm_metadata.enrich`

PR C extends the existing `_llm_metadata` block with an `enrich` entry.

Required shape:

```yaml
_llm_metadata:
  enrich:
    requested_profile: enrich_default
    profile: enrich_default
    provider: anthropic
    model: claude-sonnet-4-20250514
    fallback_used: false
    status: executed            # executed | pending | skipped | stale
    timestamp: 2026-03-28T14:30:00Z
    spec_version: 2
    input_fingerprint: sha256:...
    entity_resolution_fingerprint: sha256:...
    relationship_context_fingerprint: sha256:...
    managed_body_fingerprint: sha256:...
    axes:
      tags:
        status: updated         # updated | no_change | skipped | error
        added: [incident-management, resilience]
      entities:
        status: updated
        mentions:
          - text: engineering team
            type: department
            resolution: proposed_match:department/engineering_department
        resolved: [ServiceNow, Engineering Department]
        unresolved_created: [Engineering team]
      relationships:
        status: proposed        # proposed | no_change | skipped | error
        proposals:
          - relation: supersedes
            target_id: clienta_ddq126_evidence_20260301_market-sizing
            basis_fingerprint: sha256:...
            confidence: high
            signals: [same_source_stem, version_order]
            rationale: Same deck lineage and newer converted note.
            status: pending_human_confirmation
      body:
        status: updated         # updated | no_change | skipped_protected | conflict
```

Rules:

1. `status: skipped` means fingerprint match; no enrich analysis ran.
2. `status: pending` means enrich analysis did not run successfully or was
   intentionally deferred after setup.
3. `status: stale` means a source-changing `folio refresh` preserved enrich
   metadata shell but invalidated prior fingerprints and proposal state.
4. `entity_resolution_fingerprint` is derived from the note's stored enrich
   entity mentions and their current outcomes in `entities.json`.
5. `relationship_context_fingerprint` is derived from the note's own canonical
   relationship targets and stored proposal targets, not from every peer note
   in the engagement.
6. `managed_body_fingerprint` is omitted only when the note has never received
   enrich-managed body output.
7. `relationships.proposals` stores active pending and rejected proposals. If a
   human later copies the target into the canonical frontmatter field, the next
   enrich run removes that proposal from the active list.
8. `spec_version` increments whenever enrich-managed metadata shape or
   fingerprint semantics change incompatibly enough that previously enriched
   notes should be reconsidered on the next run.

### 9.3 Relationship proposal payload

Each proposal object must include:

- `relation`
- `target_id`
- `basis_fingerprint`
- `confidence`
- `signals`
- `rationale`
- `status`

`basis_fingerprint` is derived from:

- normalized note content hash
- the note's current `entity_resolution_fingerprint`
- the target note's current source/version identifiers

Allowed `status` values in v1:

- `pending_human_confirmation`
- `rejected`

Allowed `confidence` values in v1:

- `high`
- `medium`

Low-confidence relationship proposals are not emitted in PR C.

For `supersedes`, cardinality is singular:

- canonical frontmatter stores one target ID
- enrich stores at most one pending or rejected `supersedes` proposal per note

### 9.4 Registry contract unchanged

PR C does not add `last_enriched` or any other enrich-specific field to
`RegistryEntry`.

Rules:

1. `registry.json` remains a discovery and target-resolution index.
2. Canonical enrich provenance and idempotency live only in note frontmatter.
3. Enrich may still rely on the registry for path resolution and peer
   candidate discovery, but not as a second source of truth for enrich state.

### 9.5 No new entity arrays in top-level frontmatter

PR C does **not** add fields such as `entities`, `people`, `departments`, or
other new top-level entity arrays to note frontmatter. The entity registry
remains the canonical store; note bodies carry the human-visible links.

---

## 10. Enrichment Pipeline

For each eligible note in scope:

1. Read current frontmatter and body.
2. Parse the note into a heading-aware tree and identify managed and protected
   sections by document type.
3. If managed sections cannot be identified, mark the body protected, emit a
   warning, and continue with metadata-only/frontmatter-safe work.
4. Compute `entity_resolution_fingerprint`,
   `relationship_context_fingerprint`, and `input_fingerprint`.
5. If `--force` is not set, `_llm_metadata.enrich.status` is not `stale`, and
   the current fingerprint matches stored
   `_llm_metadata.enrich.input_fingerprint`, skip the note as unchanged.
6. Otherwise run enrich analysis.
7. Run one primary note-scoped enrich analysis pass over the current note to
   return:
   - additive tag candidates
   - entity mention candidates
   - relationship cues
8. Run deterministic entity resolution using the shipped exact / alias /
   bounded soft-match / unconfirmed-create policy and recompute the current
   `entity_resolution_fingerprint`.  **Note:** entity resolution must
   complete before relationship evaluation (step 9) because
   `basis_fingerprint` depends on `entity_resolution_fingerprint`.
9. If the relationship axis is eligible and cues exist, gather bounded peer
   descriptors from the same client/engagement scope and run one optional
   relationship-evaluation pass for allowed relationship types only.
10. Suppress any previously rejected `(relation, target_id)` proposal whose
    stored `basis_fingerprint` is unchanged. A proposal becomes eligible again
    only when note content changes, relevant entity resolution changes, the
    target note's source/version identifiers change, or `--force` is used.
11. Merge additive frontmatter and metadata updates.
12. Decide whether body mutation is safe.
13. If body mutation is safe, rewrite only managed sections selected by the
    parsed heading boundaries, and regenerate or remove `## Related` from
    canonical frontmatter as needed.
14. If body mutation is unsafe, write metadata/frontmatter only and report the
    body as protected or conflicted.
15. Write the note atomically.
16. Update `entities.json` as needed.
17. Report the per-file outcome and continue.

### 10.1 Atomicity

Markdown writes must be atomic at the file level. A failed enrich run for one
document must not corrupt that document or abort the rest of the scope.

### 10.2 Dry-run execution

Dry-run executes only the deterministic setup path:

- steps 1 through 5
- the safety checks in step 12
- summary planning

Dry-run does not execute steps 7 through 17. It makes no LLM calls, performs
no entity creation, writes no files, and reports separate `would_protect` and
`would_conflict` buckets rather than a merged body-safety count.

### 10.3 Prompt shape note

Rev 3 assumes one primary note-scoped enrich prompt plus one optional bounded
relationship-evaluation prompt. It does not assume separate tag, entity, and
relationship prompts for every note.

---

## 11. Tag Enrichment Contract

### 11.1 Inputs

PR C may inspect current note content plus existing frontmatter to suggest new
tags. It is allowed to read protected sections for analysis, but it is not
allowed to mutate them.

### 11.2 Merge behavior

Tag merge is:

- additive
- case-normalized
- deduplicated
- stable across reruns

If enrich proposes only tags that already exist, the tag axis returns
`no_change`.

### 11.3 Vocabulary stance

PR C respects the existing soft-vocabulary direction but does not add a hard
validation gate. Unrecognized tags may still be added when the content clearly
supports them.

---

## 12. Entity Backfill Contract

### 12.1 Extraction surface

PR C may inspect the full note body to identify entity mentions, including
verbatim blocks and raw transcripts. Protected sections are readable for
analysis but not writable.

### 12.2 Resolution semantics

Entity resolution must match the shipped ingest contract:

- confirmed exact canonical-name match
- confirmed alias match
- bounded LLM soft-match proposal when exact/alias match fails
- unresolved auto-create as unconfirmed
- no fuzzy matcher

This reuse is behavioral, not a promise that the current
interaction-specific function signature can be called unchanged. The
implementation may refactor shared helpers out of
`folio.pipeline.entity_resolution` so evidence notes and interaction notes use
the same resolution policy through different inputs.

### 12.3 Registry update behavior

When enrich discovers a previously unseen entity mention:

- create it in `entities.json` as `needs_confirmation: true`
- set `source: extracted`
- preserve `proposed_match` when soft match succeeds

Existing confirmation flow remains:

```bash
folio entities confirm <name>
folio entities reject <name>
```

PR C does not add a second entity-confirmation surface.

### 12.4 Body rendering rules

Entity wikilinks may be inserted only into machine-owned prose.

Interaction notes:

- allowed: `## Entities Mentioned`, `## Impact on Hypotheses`
- forbidden: raw transcript, quoted evidence text
- protected: `## Summary`, full `## Key Findings` subtree

Evidence notes:

- allowed: inline insertion only inside `### Analysis` prose fields such as
  `Visual Description`, `Key Data`, and `Main Insight`
- forbidden: `### Text (Verbatim)` blockquotes and evidence quote spans

PR C does not add a new evidence-note `### Entities Mentioned` subsection in
v1.

If a detected entity appears only inside protected verbatim content, enrich may
update metadata and the entity registry, but it must not rewrite that protected
text to force a wikilink.

### 12.5 Canonical vs unresolved links

- confirmed matches render as canonical wikilinks
- unresolved or unconfirmed entities render as normalized unresolved
  wikilinks, consistent with the current ingest boundary

After a human confirms an entity in `entities.json`, rerunning enrich may
upgrade previously unresolved links to canonical links in machine-owned
sections.

---

## 13. Relationship Proposal Contract

### 13.1 Canonical vs proposed state

Canonical relationship fields remain the source of truth.

PR C proposal flow:

1. detect high-signal relationship candidate
2. store proposal in `_llm_metadata.enrich.axes.relationships.proposals`
3. human confirms by copying the target ID into the canonical frontmatter field
   or rejects it by marking the proposal `status: rejected`
4. rerun enrich to regenerate `## Related` from canonical frontmatter and to
   drop or suppress proposals as required by their lifecycle

### 13.2 Allowed relationship types in PR C v1

#### `supersedes`

Allowed on evidence notes when all are true:

- same `client`
- same `engagement`
- same or near-identical source lineage (for example same source stem or clear
  title lineage)
- one newer note uniquely replaces one older note

This is not a schema deviation. `Folio_Ontology_Architecture.md` section 12.3
already permits `supersedes` on `all` document types. PR C uses it narrowly for
same-lineage evidence-note replacement only. Because ontology section 12.3
defines `supersedes` as singular `id`, PR C enforces singular cardinality for
both canonical state and proposals.

Allowed proposal signals:

- `same_source_stem`
- `title_lineage_match`
- `version_order`
- `newer_converted_timestamp`

#### `impacts`

Allowed on interaction notes when the interaction clearly changes, informs, or
revises a known target document in the same client/engagement scope.

Allowed proposal signals:

- `explicit_document_reference`
- `explicit_hypothesis_change`
- `shared_named_asset`

#### `depends_on` and `draws_from`

The ontology supports these, but PR C does not emit them for the current
registry-managed evidence/interaction corpus.

Reason:

- `depends_on` and `draws_from` are defined for analysis / deliverable docs
- PR C v1 is scoped to registry-managed evidence and interaction notes only
- ontology section 6.4 recommends starting with them, but Rev 3 deliberately
  reorders that recommendation to match the current corpus

The enrich proposal structure must remain compatible with future support for
those fields, but PR C does not force them into evidence notes.

### 13.3 Explicit deferrals

Do not propose in PR C:

- `relates_to`
- `instantiates`
- similarity-only relationships
- cross-engagement relationships
- interaction `draws_from`

### 13.4 `## Related` rendering

`## Related` is derived only from canonical frontmatter relationships already
present in the note.

Rendering rules:

1. Resolve target IDs through `registry.json`.
2. Render Obsidian path wikilinks using the target note's `markdown_path`
   without the `.md` suffix and with the target title as alias.
3. Group links by relationship field.
4. Skip unresolved target IDs from the body if they cannot be resolved through
   the registry, but leave the frontmatter untouched and report a warning.
5. If no canonical relationship targets resolve after filtering, omit
   `## Related` entirely and remove any stale previously generated section.
6. Place the section according to D8: before `## Version History` in evidence
   notes, and between `## Impact on Hypotheses` and the raw transcript callout
   in interaction notes.

Example:

```markdown
## Related

### Supersedes
- [[ClientA/DD_Q1_2026/market_sizing/market_sizing|Market Sizing Analysis]]
```

PR C does **not** render pending proposals into the body.

---

## 14. Body Mutation and Human Edit Safety

### 14.1 Managed sections by document type

Section targeting must come from the parsed heading tree or equivalent subtree
selection model. Regex-only global replacement is forbidden.

Evidence notes:

- every per-slide `### Analysis` subtree under its enclosing slide section,
  stopping at the next heading that exits that subtree
- trailing generated `## Related`

Interaction notes:

- exact top-level `## Entities Mentioned`
- trailing generated `## Related`

> **v1 note:** `## Impact on Hypotheses` is listed in the ontology as an
> allowed mutation surface but is excluded from the v1 managed set because
> no mutation logic exists for it yet. Including it would create false
> conflict positives when humans edit the section. It may be promoted to
> managed in a future PR when mutation logic is added.

Protected interaction subtrees:

- exact top-level `## Summary`
- exact top-level `## Key Findings`
- `## Key Findings` children `### Claims`, `### Data Points`, `### Decisions`,
  and `### Open Questions`

### 14.2 Protected states

Body mutation is skipped when:

- `curation_level != L0`
- `review_status in {reviewed, overridden}`
- the parser cannot identify the expected managed sections safely
- stored `managed_body_fingerprint` exists and the current managed sections do
  not match it

### 14.3 Conflict behavior

When the current managed sections do not match the stored
`managed_body_fingerprint`, enrich marks:

- `_llm_metadata.enrich.axes.body.status: conflict`

and:

- skips all body mutation for that note
- still allows metadata-only and additive frontmatter updates
- reports the note in the CLI summary as conflicted

Edits inside protected sections such as interaction `## Summary` or
`## Key Findings` do not by themselves trigger managed-body conflicts because
they are outside the managed surface.

### 14.4 First-run behavior

If no prior enrich metadata exists, enrich may write managed sections on
eligible L0 notes without a prior `managed_body_fingerprint`.

---

## 15. Review State, Refresh, and Cleanup Boundaries

### 15.1 Review-state behavior

PR C does not redefine `review_status`.

Rules:

1. Existing `flagged` stays `flagged` unless another workflow resolves the
   underlying issue.
2. Existing `reviewed` and `overridden` protect the body from mutation.
3. If enrich LLM analysis fails, record `_llm_metadata.enrich.status: pending`
   and surface the failure in CLI output, but do not automatically change the
   document's existing `review_status`.

### 15.2 Refresh compatibility

`folio refresh` and `folio enrich` must not form a destructive lifecycle.

Required v1 contract:

1. `refresh` reads the existing note frontmatter before re-conversion.
2. `refresh` regenerates the note normally from current conversion output.
3. Before final write, `refresh` passes through only:
   - human-confirmed canonical relationship fields
   - `_llm_metadata.enrich`
4. This passthrough is allowlisted and frontmatter-only; it is not a sidecar
   and not a free-form merge of arbitrary legacy fields.
5. If refreshed source inputs invalidate prior enrich output, `refresh` sets
   `_llm_metadata.enrich.status: stale`.
6. A stale refresh clears prior enrich fingerprints, entity-resolution
   fingerprint state, and relationship proposal records.
7. A stale refresh regenerates or removes `## Related` from preserved
   canonical frontmatter only.

This is a PR C requirement, not an optional future hardening task.

### 15.3 Registry contract unchanged

`registry.json` remains a discovery and target-resolution index only.
Enrich-specific durability lives in note frontmatter, not in the registry.

### 15.4 Stale source-path repair

The real-vault validation explicitly recommends that PR C fix the 148
legacy-root evidence-note source paths. Rev 3 acknowledges that recommendation
and classifies the fix as a deterministic companion cleanup or
refresh/migration concern, not as part of the LLM enrich decision loop.

### 15.5 Over-broad review-state surface

The current high flagged rate is a product-quality issue, but PR C does not
treat "successful enrich" as a justification to mass-clear flags. Review-state
recalibration is separate work.

---

## 16. Test Plan

### 16.1 Unit tests

Required unit coverage:

1. additive tag merge
2. enrich route resolution and `--llm-profile` override behavior
3. `--force` bypass behavior
4. input-fingerprint skip behavior
5. note-scoped `entity_resolution_fingerprint` behavior
6. rejected-proposal suppression until `basis_fingerprint` changes
7. managed-body fingerprint conflict detection
8. malformed-heading protected fallback
9. relationship proposal serialization, including singular `supersedes`
10. entity resolver policy-reuse semantics across evidence and interaction notes
11. dry-run no-write, no-LLM behavior with separate protected/conflicted counts
12. `## Related` generation from canonical frontmatter only
13. `## Related` suppression when all canonical targets are unresolved
14. stale-status transition when refresh invalidates prior enrich fingerprints

### 16.2 Body safety tests

Required body-safety coverage:

1. evidence notes:
   - `### Text (Verbatim)` is unchanged
   - evidence quote spans are unchanged
   - entity wikilinks are inserted only inline inside `### Analysis` prose
   - `### Analysis` may change when eligible
   - parsed-section targeting does not bleed into neighboring headings
2. interaction notes:
   - raw transcript callout is unchanged
   - quote text under `## Quotes / Evidence` is unchanged
   - `## Summary` is unchanged
   - full `## Key Findings` tree is unchanged
   - `## Entities Mentioned` and `## Impact on Hypotheses` may change when eligible
   - parsed-section targeting does not bleed into other top-level sections

### 16.3 Integration tests

Required integration coverage:

1. convert an evidence note, ingest a related interaction, run enrich, verify:
   - tags merged
   - entities backfilled
   - interaction relationship proposals use `impacts`, not `draws_from`
   - registry target resolution and entity updates remain consistent
2. rerun enrich twice, verify:
   - no duplicate tags
   - no duplicate entity links
   - no duplicate proposals
   - no duplicate `## Related` section
3. mark a note `reviewed` or `overridden`, rerun enrich, verify:
   - body mutation is skipped
   - metadata-only updates still behave as specified
4. refresh an enriched evidence note after a source change, verify:
   - canonical relationship fields survive
   - `_llm_metadata.enrich.status` becomes `stale`
   - pending and rejected proposals plus fingerprints are cleared
   - regenerated `## Related` reflects canonical frontmatter only
5. reject a relationship proposal, rerun enrich without basis change, verify:
   - proposal is not re-emitted
   - `--force` still respects the unchanged rejection basis
6. mutate an unrelated entity elsewhere in `entities.json`, rerun enrich, verify:
   - unaffected notes do not re-enrich solely because the registry timestamp changed

### 16.4 Scale test

PR C must include a fixture-backed scale test of **50+ files** minimum that
exercises:

- incremental processing
- continue-on-error behavior
- summary reporting
- protected/conflict paths
- diagram-note skip behavior
- dry-run planning without LLM calls
- pre-run call estimation output

The scale fixture need not match the full 1,684-file production library, but it
must materially approximate multi-client / multi-note batch behavior.

---

## 17. Acceptance Criteria

- `folio enrich [scope] [--dry-run] [--llm-profile <profile>] [--force]` exists with the
  scope semantics defined above.
- `routing.enrich` is supported.
- Enrich processes only registry-managed evidence and interaction notes.
- Diagram notes are skipped explicitly.
- Tag enrichment is additive-only.
- Entity backfill uses the shipped entity-resolution policy.
- Enrich never rewrites:
  - evidence verbatim text blocks
  - evidence quote spans
  - interaction Summary
  - interaction Key Findings subtree
  - interaction raw transcript text
  - interaction quote text
- Relationship proposals are stored only in `_llm_metadata.enrich`, not in
  canonical relationship fields.
- Rejected relationship proposals are suppressed until their
  `basis_fingerprint` changes.
- `## Related` is generated only from canonical relationship frontmatter.
- Empty or fully unresolvable canonical relationship sets do not leave a
  dangling `## Related` section.
- Rerunning enrich on unchanged input produces a no-op skip unless `--force` is
  used or the note is marked `stale`.
- L1+, `reviewed`, `overridden`, and fingerprint-conflicted notes do not
  receive body rewrites.
- `registry.json` remains lightweight and gains no enrich-specific durable
  fields.
- Dry-run writes nothing and makes no LLM API calls.
- `folio refresh` does not silently destroy human-confirmed enrich state.
- `folio refresh` preserves canonical relationship fields and
  `_llm_metadata.enrich` through an allowlisted frontmatter passthrough.
- `folio refresh` regenerates the note body, so the `## Related` body section
  is lost on refresh. Re-run `folio enrich` to restore it from the preserved
  canonical relationship fields.
- Per-file failures do not abort the remaining scope.

---

## 18. PRD Implications

This spec is not itself the PRD amendment, but it implies the following PRD
changes:

### 18.1 New FR under the CLI family

Add a new FR after FR-507:

- **FR-508: Enrich Command**

This FR should cover:

- command syntax
- scope behavior
- dry-run
- `--force`
- pre-run call estimates
- per-file error handling
- summary output

### 18.2 FR-402 (Obsidian Frontmatter)

Amend FR-402 to explicitly cover:

- `_llm_metadata.enrich`
- entity-mention metadata needed for note-scoped enrich fingerprints
- relationship proposal metadata under `_llm_metadata`
- generated `## Related` section derived from canonical relationship fields

### 18.3 FR-403 (Registry)

Amend FR-403 to explicitly cover:

- registry-first enrich discovery
- enrich operating on registry-managed evidence and interaction notes

### 18.4 FR-404 (Entity Registry)

Amend FR-404 to explicitly cover:

- enrich-time entity backfill using the existing entity registry
- reuse of exact / alias / bounded LLM soft-match resolution semantics
- unconfirmed entity creation during enrich

### 18.5 FR-505 (Refresh Command)

Amend FR-505 to explicitly cover:

- allowlisted frontmatter passthrough of canonical relationship fields and
  `_llm_metadata.enrich` during re-conversion
- stale invalidation behavior for preserved enrich metadata
- regeneration of `## Related` from preserved canonical relationship fields

### 18.6 FR-604 (Task Routing)

Add:

- `routing.enrich` controls the `folio enrich` path in v1

### 18.7 FR-606 and FR-706 (Execution transparency and provenance)

Amend both to explicitly cover:

- enrich requested profile
- resolved profile
- provider / model
- fallback activation
- enrich timestamp
- enrich idempotency fingerprints
- per-axis enrich outcomes and proposal metadata

### 18.8 FR-705 (Human Override Persistence)

Amend FR-705 to explicitly cover:

- enrich-managed body sections versus protected record sections
- interaction `## Summary` and `## Key Findings` as protected content
- malformed-heading fallback to protected behavior rather than destructive
  rewrite

### 18.9 Ontology-ordering and deferral note

The PRD patch should state explicitly that enrich:

- may add structure and provenance metadata
- does not auto-clear review flags or auto-promote `review_status`
- preserves human-confirmed enrich state across `folio refresh`
- deliberately prioritizes `supersedes` / `impacts` ahead of
  `depends_on` / `draws_from` for the current corpus
- deliberately defers manual body-wikilink promotion from arbitrary user links

---

## 19. Open Questions for Reviewers

No blocking product questions remain after the codebase read and scope lock.

The following are explicit **deferrals**, not open questions:

- review-state recalibration
- manual wikilink promotion
- diagram-note enrichment
- relationship confirmation CLI
- `folio status` enrichment-state reporting
- per-note enrich opt-out switch
- `--max-calls` budget valve
- retroactive provenance

---

## 20. Sequencing / Preconditions

Before implementation starts, the following must be treated as true:

1. The production `anthropic_sonnet4` library plus 12 validated `haiku45`
   merges is the only approved enrich baseline.
2. PR #32, PR #34, and PR #35 are already the shipped foundation.
3. The real-library rerun and real-vault validation are complete and do not
   need to be reopened to start PR C.
4. The PRD still needs an explicit `folio enrich` FR patch before or alongside
   implementation.
5. `folio refresh` compatibility changes needed to preserve enrich state are a
   PR C implementation prerequisite, not optional later cleanup.
6. Note-scoped enrich fingerprints and rejected-proposal lifecycle are part of
   core PR C, not optional polish.
7. PR C remains separate from PR D provenance work.
8. Relationship confirmation and rejection remain manual through frontmatter or
   enrich metadata edits in v1.
9. Diagram notes remain out of scope for PR C v1.
10. The follow-on deliverable after approval is an implementation prompt, not
   code directly from this spec.

---

## 21. Summary Decision Record

PR C is a **conservative enrich pass**:

- registry-first
- evidence + interaction only
- additive tags
- shipped entity resolver reused
- ontology-bounded relationships with corpus-driven priority ordering
- canonical relationship fields human-owned
- stub-only interaction body mutation
- `## Related` derived from canonical frontmatter
- refresh-compatible enrich state preserved in frontmatter
- idempotent reruns via note-scoped enrich fingerprints
- rejected proposals suppressed by basis fingerprint
- `--force` available for deliberate re-analysis
- strict no-LLM dry-run
- strict body-safety rules for verbatim and quoted content

That is the correct scope boundary for the first `folio enrich` PR.

---

## 22. Review Resolution Map

| Review item | Rev 3 disposition | Resolution |
|-------------|-------------------|------------|
| B1 refresh destroys enrich state | Adopted | D12, Section 15.2, and Section 18.5 now specify an allowlisted frontmatter passthrough that preserves canonical relationship fields and `_llm_metadata.enrich` across refresh. |
| B2 file-level entity timestamp causes mass reruns | Adopted | D9, Section 9.2, and Section 10 replace `entities.json.updated_at` with a note-scoped `entity_resolution_fingerprint`. |
| B3 no proposal rejection lifecycle | Adopted | Sections 9.2, 9.3, 10, and 13.1 add `rejected` status plus `basis_fingerprint`-based suppression and reproposal rules. |
| B4 interaction mutation violates append-only rule | Adopted | D10, Section 12.4, and Section 14 restrict interaction mutation to `## Entities Mentioned`, `## Impact on Hypotheses`, and generated `## Related`. |
| B5 wikilink-promotion deferral unacknowledged | Adopted | Section 4 and Section 18.9 now call this out as a deliberate ontology-specified deferral. |
| B6 `## Key Findings` subtree unspecified | Adopted | D10 and Section 14 explicitly protect the full `## Key Findings` tree and keep it outside the managed surface. |
| S1 peer-change cascade from broad scope fingerprint | Adopted | D9 and Sections 9.2/10 replace engagement-wide invalidation with note-local `relationship_context_fingerprint`. |
| S2 ontology v1 recommendation reorder mischaracterized | Adopted | Section 5.3, D6, and Section 18.9 now describe this as a deliberate corpus-driven priority reordering. |
| S3 evidence-note entity rendering location unspecified | Adopted | Section 12.4 now limits evidence entity-link insertion to inline `### Analysis` prose fields only. |
| S4 no rerun override | Adopted | Goals, Section 7, Section 10, Section 16, and Section 17 now add `--force`. |
| S5 cost estimation / guardrails absent | Adopted | D15 and Section 7.5 add pre-run eligible-note and estimated-call reporting; `--max-calls` remains deferred. |
| S6 malformed heading fallback undefined | Adopted | D11, Section 10, and Section 14 define malformed parses as protected metadata-only handling with warning and continue-on-error behavior. |
| S7 canonical-field wording ambiguous | Adopted | Section 9.1 now separates tag writes from relationship-field reads/preservation and states proposals never write canonical fields. |
| S8 FR-505 missing from PRD amendments | Adopted | Section 18.5 now adds a formal FR-505 amendment. |
| S9 stale source-path recommendation ignored | Adopted | D13 and Section 15.4 now cite the vault-validation recommendation and classify it as deterministic companion cleanup, not an enrich LLM axis. |
| m1 `supersedes` singular cardinality | Adopted | Sections 9.3 and 13.2 now enforce singular canonical/proposal cardinality. |
| m2 `## Related` placement unspecified | Adopted | D8 and Section 13.4 now lock placement for evidence and interaction notes. |
| m3 diagram skip progress symbol absent | Deferred | Section 8.2 explains diagram notes are excluded at registry-first eligibility time, so Rev 3 keeps summary-only out-of-scope behavior rather than per-file skip rows. |
| m4 `spec_version` policy absent | Adopted | Section 9.2 now defines when `spec_version` increments. |
| m5 scope-fingerprint derivation underspecified | Adopted | D9 and Section 9.2 replace it with explicit `relationship_context_fingerprint` rules. |
| m6 dry-run protected vs conflicted not separated | Adopted | Sections 7.4, 7.5, and 10.2 now separate the two buckets. |
| m7 `stale` behavior missing from pipeline | Adopted | D9 and Section 10 now require stale notes to bypass skip logic and re-run on next enrich. |
| m8 no per-note enrich opt-out | Deferred | Section 4 and Section 19 explicitly defer this; v1 relies on scope narrowing or non-L0 curation. |
| m9 body-safety contract not anchored to PRD FR | Adopted | Section 18.8 adds an FR-705 amendment covering managed versus protected sections. |
| m10 `folio status` integration missing | Deferred | Section 4 and Section 19 explicitly defer status integration because the registry stays unchanged in PR C. |
| m11 no prompt strategy guidance | Adopted | Section 10.3 adds the non-normative prompt-shape note. |
| m12 peer-read `summary` field does not exist | Adopted | D3 and Section 8.3 replace that language with actual available peer fields. |
