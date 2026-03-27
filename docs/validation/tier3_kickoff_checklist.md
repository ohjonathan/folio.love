---
id: tier3_kickoff_checklist
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
---

# Tier 3 Development Tracker

## Purpose

This file is the live tracker for **all Tier 3: Engagement Intelligence**
development, starting from the now-merged `folio ingest` baseline.

It is no longer just a pre-start checklist. It now tracks:

- shipped Tier 3 baseline
- remaining PR slices
- non-PR prerequisites and hardening tracks
- machine split
- owner split
- roadmap and PRD alignment for each major slice

Use this as the single operational tracker for Tier 3 sequencing.

## Tier 3 Baseline

- Tier 2 is **not** formally closed.
- Tier 3 implementation is proceeding under the explicit waiver in
  `docs/validation/tier2_to_tier3_waiver_note.md`.
- `folio ingest` is already shipped on `main` via PR #32.
- The entity-system kickoff spec is approved in
  `docs/specs/v0.5.1_tier3_entity_system_spec.md`.
- PR #34 shipped the entity registry foundation on `main`.
- PR #35 shipped ingest-time entity resolution on `main`.
- The Tier 2 platform model-comparison package is now finalized in canonical
  form under `docs/validation/`.
- The per-stage routing recommendation is now recorded:
  - Pass 1: `openai_gpt53`
  - diagram stage: `anthropic_haiku45`
  - interim Pass 2: `anthropic_haiku45`
  - current single-route default on `main`: `anthropic_haiku45`
- The Tier 2 real-library rerun is now complete on the McKinsey laptop:
  - runtime passed operationally on the full 161-file corpus
  - the `haiku45` scratch rerun did **not** beat the production library at
    full-corpus scale
  - the production `sonnet4` library remains the baseline for vault validation
    and PR C input
- The next active feature slice is **PR C: `folio enrich` core**.
- Before PR C, the recommended hardening track is:
  - real vault validation
- `folio enrich`, retroactive provenance, and context-doc integration remain
  unstarted.

## Source Of Truth

Use these references when evaluating whether a Tier 3 PR is in scope:

- Product requirements: `docs/product/02_Product_Requirements_Document.md`
- Tier sequencing and feature intent:
  `docs/product/04_Implementation_Roadmap.md`
- Ontology and entity model:
  `docs/architecture/Folio_Ontology_Architecture.md`
- Tier 2 waiver:
  `docs/validation/tier2_to_tier3_waiver_note.md`

## PRD Coverage Note

Tier 3 is only partially explicit in the PRD today.

- `folio ingest` is now explicitly represented in the PRD.
- Later Tier 3 slices such as entity registry, `folio enrich`, retroactive
  provenance, and context docs are still more fully defined by the roadmap and
  ontology than by the PRD.

So for each remaining PR below:

- the **roadmap** is the primary feature-sequencing source
- the **PRD** is the primary requirements source where applicable
- the **ontology** is the structural source when the PRD is still sparse

## Tier 3 PR Map

| PR | Slice | Status | Estimated Effort | Machine | Owner | Depends On | Primary Roadmap Reference | Primary PRD Reference | Deliverable |
|---|---|---|---|---|---|---|---|---|---|
| PR #32 | `folio ingest` interaction baseline | Shipped | Completed | Personal Folio dev laptop | Agents implemented, you reviewed/merged | Tier 2 waiver + ingest spec | Week 13-15: Interaction Ingestion | FR-403, FR-500, FR-506, FR-604, FR-607, FR-701 to FR-704 | Ontology-native interaction notes, mixed-library support, degraded-output handling, unresolved entity wikilinks |
| PR #34 / PR A | Entity registry core + `folio entities` + `folio entities import <csv>` | Shipped | Completed | Personal Folio dev laptop | Agents implemented, you reviewed/merged | Approved entity-system kickoff spec | Week 16-18: Entity System | FR-403, FR-500 family, FR-503, FR-504, roadmap-primary for entity registry/import | Canonical entity store, `folio entities` CLI, org-chart import path, confirm/reject flow, no ingest-time resolution yet |
| PR #35 / PR B | Ingest-time entity resolution against registry | Shipped | Completed | Personal Folio dev laptop | Agents implemented, you reviewed/merged | PR #34 merged | Week 16-18: Entity System | FR-506, FR-701 to FR-704, FR-403, roadmap-primary for exact match + LLM soft match + human confirmation | `folio ingest` resolves entities against the registry, auto-creates unresolved entities as unconfirmed, adds bounded soft-match proposals, and canonicalizes rendered entity links during ingest |
| PR C | `folio enrich` core | Next feature slice | 5-7 dev days | Personal Folio dev laptop | Agents implement, you review | PR #34 and PR #35 merged; use the production `sonnet4` library after real vault validation | Week 19-20: Enrichment & Provenance | FR-402, FR-403, FR-500 family, FR-700, FR-706 | Post-hoc enrichment over existing assets for tags, frontmatter relationships, and entity backfill |
| PR D | Retroactive provenance linking | Not started | 4-6 dev days | Personal Folio dev laptop | Agents implement, you review | PR C merged | Week 19-20: Enrichment & Provenance | FR-701 to FR-706, roadmap retroactive provenance bullet | Proposed deliverable-to-evidence links with human confirmation and clear provenance metadata |
| PR E | Context docs + end-to-end Tier 3 integration + closeout | Not started | 3-5 dev days | Personal Folio dev laptop for templates/tests; McKinsey laptop for real validation | Agents draft/implement, you validate/close out | PR A through PR D merged; rerun and vault validation completed | Week 21-22: Context Documents & Integration | FR-402, FR-403, FR-700 where generated content applies; roadmap-primary for context-doc behavior | Context template, full engagement lifecycle test, Tier 3 validation and closeout package |

## PR Breakdown Details

### PR #32: `folio ingest` interaction baseline

**Status:** Shipped

What it delivered:
- `folio ingest`
- ontology-native `interaction` notes
- subtype-aware interaction analysis
- interaction frontmatter and markdown contract
- mixed-library registry/status/scan behavior
- unresolved entity wikilinks as first-pass placeholders

Why it matters:
- establishes the raw material that the entity system will now canonicalize
- keeps `enrich` and registry-backed resolution out of the first slice

### PR #34 / PR A: Entity registry core

**Status:** Shipped on `main`.

**Progress snapshot:**
- Merged as PR #34 on 2026-03-22 at commit `e322660`
- Added the entity registry foundation in `folio/tracking/entities.py`
- Added CSV import flow in `folio/entity_import.py`
- Added `folio entities` CLI surface in `folio/cli.py`
  - list/view
  - import
  - confirm
  - reject
- Added org-chart and registry fixtures plus focused CLI/import/entity tests
- Left ingest-time resolution explicitly out of scope for the follow-on PR

What it delivered:
- canonical entity registry storage
- entity types for the first slice
- `folio entities` for basic view/search/list behavior
- `folio entities import <csv>` for org-chart bulk load
- confirm / reject workflow for pending entities
- no ingest-time resolution yet

Why it was separated:
- registry shape and import semantics are foundational
- ingest-time resolution should not be designed before the registry contract is
  explicit and testable

### PR #35 / PR B: Ingest-time resolution

**Status:** Shipped on `main`.

**Progress snapshot:**
- Merged as PR #35 on 2026-03-23 at commit `2a61d02`
- Added ingest-time resolver in `folio/pipeline/entity_resolution.py`
- Wired resolution into `ingest_source()` before note-write and version side
  effects
- Implemented exact and alias matching against **confirmed** entities only
- Kept lookup type-strict and deduplicated entities after canonicalization
- Auto-created unresolved entities in `entities.json` as unconfirmed
- Added bounded LLM soft-match proposals when exact/alias match failed
- Surfaced `proposed_match` in existing `folio entities` review output without
  changing the command surface
- Preserved existing `client`, `engagement`, and `participants` on re-ingest;
  conflicting overrides are ignored with warnings so note metadata and
  `registry.json` stay aligned
- Treated missing `entities.json` as a no-op, but failed ingest when an
  existing registry was unreadable/corrupt
- Added resolver unit tests, CLI coverage, ingest integration coverage, and
  the `test_transcript_entities.txt` fixture

What it delivered:
- exact-match resolution against the registry
- alias-aware resolution where aliases exist in PR A data
- LLM-proposed soft match as a bounded fallback
- deliberate ambiguity handling through proposals and confirmation flow
- re-ingest behavior that can improve earlier unresolved entity mentions

Why it was separated:
- this is where the highest-risk heuristics live
- keeping it separate made false-match and ambiguity regressions easier to
  isolate from the registry foundation

### PR C: `folio enrich` core

What it should deliver:
- post-hoc enrichment over existing notes
- tags and relationship frontmatter population where in scope
- entity backfill across already-existing assets
- no retroactive provenance matching yet

Why it is separated:
- enrichment touches far more existing content than ingest-time resolution
- it should not be bundled with provenance matching on the first pass

Current baseline note:
- use the production `sonnet4` library as PR C input
- do not switch PR C input to the `haiku45` scratch rerun library
- keep the rerun outputs as comparative evidence, not as the new production
  baseline

### PR D: Retroactive provenance linking

What it should deliver:
- proposed links between deliverable claims and supporting evidence
- human confirmation path for those links
- explicit provenance metadata on the resulting links or outputs

Why it is separated:
- provenance is a graph/evidence problem, not just a generic enrichment problem
- it deserves its own reviewability and confirmation surface

### PR E: Context docs + Tier 3 closeout

What it should deliver:
- context-doc template and behavior
- end-to-end Tier 3 lifecycle validation
- final Tier 3 closeout package

Why it is separated:
- this is the integration and validation slice, not a foundational data-model
  slice
- context docs should land after the upstream graph pieces are in place

## Non-PR Tracks And Prerequisites

These items do not have to map 1:1 to feature PRs, but they affect sequencing
and merge readiness.

| Seq | Track | Required | Machine | Owner | Why It Matters | Status |
|---|---|---|---|---|---|---|
| 1 | Tier 2 waiver decision | Done | Personal Folio dev laptop | You | Authorizes Tier 3 implementation without pretending Tier 2 is formally closed | Done |
| 2 | Ingest kickoff spec | Done | Personal Folio dev laptop | Agents drafted, you approved | Enabled the shipped `folio ingest` slice | Done |
| 3 | Entity-system kickoff spec | Yes | Personal Folio dev laptop | Agents draft, you approve | Freezes scope before PR A begins | Done |
| 4 | Entity-system fixtures | Yes | Personal Folio dev laptop; McKinsey laptop if using real examples | Shared | Gives PR A and PR B grounded fixtures for import and resolution behavior | Done: PR #34 landed import/registry fixtures and PR #35 added resolution-specific fixtures |
| 5 | Per-stage routing decision | Recommended | Personal Folio dev laptop | Agents draft, you approve | Useful Tier 2/Tier 3 hardening, but not a blocker for PR A or PR B | Done: canonical Tier 2 model-comparison artifacts record Pass 1 = `openai_gpt53`, diagram = `anthropic_haiku45`, interim Pass 2 = `anthropic_haiku45`, current default = `anthropic_haiku45` |
| 6 | Real engagement/library rerun | Recommended before PR C | McKinsey laptop | You run; agents prepare runbook | Confirms runtime behavior at full-corpus scale and determines the correct library baseline before `enrich` | Done: full 161-file rerun completed; runtime passed, but production `sonnet4` library outperformed the `haiku45` scratch rerun and remains the baseline |
| 7 | Real vault validation | Recommended before PR C | McKinsey laptop | You | Confirms the production library is usable enough to justify enrichment and provenance work | Not started |

## Machine Guide

| Work Type | Machine |
|---|---|
| Product docs, roadmap, PRD, prompts, specs | Personal Folio dev laptop |
| Code implementation, unit tests, integration tests, CLI scaffolding | Personal Folio dev laptop |
| Real engagement corpus reruns | McKinsey laptop |
| Real Obsidian vault open/render checks | McKinsey laptop |
| 2-week daily-driver validation | McKinsey laptop |

## Owner Guide

| Work Type | Owner |
|---|---|
| Tier 2 go/waive decision | You |
| Drafting specs, prompts, and trackers | Agents |
| Implementing PR slices | Agents |
| Reviewing scope, tradeoffs, and merges | You |
| Real engagement runs and vault validation | You |
| Preparing runbooks/checklists for real validation work | Agents |

## Sequencing Rules

1. Treat PR #32 as shipped baseline, not future work.
2. Treat PR #34 as shipped baseline for the entity registry and CLI.
3. Treat PR #35 as shipped baseline for ingest-time entity resolution.
4. Do not start PR C before PR #34 and PR #35 are merged.
5. Treat the real library rerun and real vault validation as serious
   prerequisites before PR C and PR D.
6. Use the production `sonnet4` library, not the `haiku45` scratch rerun, as
   the current baseline for vault validation and PR C unless a later decision
   explicitly changes that.
7. Do not bundle retroactive provenance into the first `folio enrich` PR by
   default.
8. Do not bundle `.overrides.json` or interaction-specific override UX into
   retroactive provenance unless a later spec explicitly requires it.
9. Keep each Tier 3 PR narrow enough that review can isolate regressions.

## Recommended Working Order

1. Validate real vault behavior on the McKinsey laptop using the production
   `sonnet4` library.
2. Implement PR C: `folio enrich` core against the production library.
3. Implement PR D: retroactive provenance.
4. Implement PR E: context docs and Tier 3 closeout.

## Live Checklist

- [x] Tier 2 go/waive decision recorded explicitly
- [x] `folio ingest` kickoff spec drafted and approved
- [x] `folio ingest` fixtures assembled
- [x] `folio ingest` shipped on `main`
- [x] Product docs synced to the merged ingest baseline
- [x] Entity-system kickoff spec drafted
- [x] Entity-system kickoff spec approved
- [x] Entity-system fixtures fully assembled for PR B
- [x] PR A merged: entity registry core
- [x] PR B merged: ingest-time entity resolution
- [x] Per-stage routing decision recorded
- [x] Real engagement/library rerun completed on McKinsey laptop
- [ ] Real vault validation completed on McKinsey laptop
- [ ] PR C merged: `folio enrich` core
- [ ] PR D merged: retroactive provenance
- [ ] PR E merged: context docs + Tier 3 closeout
