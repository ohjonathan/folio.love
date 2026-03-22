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
- The next active development slice is **Entity System**.
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
| PR A | Entity registry core + `folio entities` + `folio entities import <csv>` | Not started | 4-6 dev days | Personal Folio dev laptop | Agents draft/implement, you review | Approved entity-system kickoff spec | Week 16-18: Entity System | FR-403, FR-500 family, FR-503, FR-504, roadmap-primary for entity registry/import | Canonical entity store, basic view/search CLI, org-chart import path, no ingest-time resolution yet |
| PR B | Ingest-time entity resolution against registry | Not started | 4-6 dev days | Personal Folio dev laptop | Agents implement, you review | PR A merged | Week 16-18: Entity System | FR-506, FR-701 to FR-704, FR-403, roadmap-primary for exact match + LLM soft match + human confirmation | `folio ingest` resolves entities against the registry, handles ambiguity deliberately, and upgrades unresolved mentions into canonical links where appropriate |
| PR C | `folio enrich` core | Not started | 5-7 dev days | Personal Folio dev laptop | Agents implement, you review | PR A and PR B merged; real library rerun strongly recommended first | Week 19-20: Enrichment & Provenance | FR-402, FR-403, FR-500 family, FR-700, FR-706 | Post-hoc enrichment over existing assets for tags, frontmatter relationships, and entity backfill |
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

### PR A: Entity registry core

**Status:** Next planned implementation PR after the spec is approved.

What it should deliver:
- canonical entity registry storage
- entity types for the first slice
- `folio entities` for basic view/search/list behavior
- `folio entities import <csv>` for org-chart bulk load
- no ingest-time resolution yet

Why it is separated:
- registry shape and import semantics are foundational
- ingest-time resolution should not be designed before the registry contract is
  explicit and testable

### PR B: Ingest-time resolution

What it should deliver:
- exact-match resolution against the registry
- alias-aware matching if the registry supports aliases in PR A
- LLM-proposed soft match only where explicitly approved by the spec
- deliberate ambiguity handling and human-confirmation boundary
- re-ingest behavior that can improve earlier unresolved entity mentions

Why it is separated:
- this is where the highest-risk heuristics live
- keeping it separate makes false-match and ambiguity regressions easier to
  isolate

### PR C: `folio enrich` core

What it should deliver:
- post-hoc enrichment over existing notes
- tags and relationship frontmatter population where in scope
- entity backfill across already-existing assets
- no retroactive provenance matching yet

Why it is separated:
- enrichment touches far more existing content than ingest-time resolution
- it should not be bundled with provenance matching on the first pass

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
| 3 | Entity-system kickoff spec | Yes | Personal Folio dev laptop | Agents draft, you approve | Freezes scope before PR A begins | Not started |
| 4 | Entity-system fixtures | Yes | Personal Folio dev laptop; McKinsey laptop if using real examples | Shared | Gives PR A and PR B grounded fixtures for import and resolution behavior | Not started |
| 5 | Per-stage routing decision | Recommended | Personal Folio dev laptop | Agents draft, you approve | Useful Tier 2/Tier 3 hardening, but not a blocker for PR A or PR B | Not started |
| 6 | Real engagement/library rerun | Recommended before PR C | McKinsey laptop | You run; agents prepare runbook | Ensures `enrich` starts from the best current library baseline | Not started |
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
2. Do not start PR A until the entity-system kickoff spec is approved.
3. Do not start PR B before PR A is merged.
4. Do not start PR C before PR A and PR B are merged.
5. Treat the real library rerun and real vault validation as serious
   prerequisites before PR C and PR D.
6. Do not bundle retroactive provenance into the first `folio enrich` PR by
   default.
7. Do not bundle `.overrides.json` or interaction-specific override UX into
   retroactive provenance unless a later spec explicitly requires it.
8. Keep each Tier 3 PR narrow enough that review can isolate regressions.

## Recommended Working Order

1. Draft and approve the entity-system kickoff spec.
2. Assemble entity-system fixtures.
3. Implement PR A: entity registry core.
4. Implement PR B: ingest-time resolution.
5. Record the per-stage routing decision as a separate hardening track.
6. Run the real engagement/library rerun on the McKinsey laptop.
7. Validate real vault behavior on the McKinsey laptop.
8. Implement PR C: `folio enrich` core.
9. Implement PR D: retroactive provenance.
10. Implement PR E: context docs and Tier 3 closeout.

## Live Checklist

- [x] Tier 2 go/waive decision recorded explicitly
- [x] `folio ingest` kickoff spec drafted and approved
- [x] `folio ingest` fixtures assembled
- [x] `folio ingest` shipped on `main`
- [x] Product docs synced to the merged ingest baseline
- [ ] Entity-system kickoff spec drafted
- [ ] Entity-system kickoff spec approved
- [ ] Entity-system fixtures assembled
- [ ] PR A merged: entity registry core
- [ ] PR B merged: ingest-time entity resolution
- [ ] Per-stage routing decision recorded
- [ ] Real engagement/library rerun completed on McKinsey laptop
- [ ] Real vault validation completed on McKinsey laptop
- [ ] PR C merged: `folio enrich` core
- [ ] PR D merged: retroactive provenance
- [ ] PR E merged: context docs + Tier 3 closeout
