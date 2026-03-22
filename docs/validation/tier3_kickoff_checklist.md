---
id: tier3_kickoff_checklist
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
---

# Tier 3 Kickoff Checklist

## Purpose

This checklist is the working tracker for starting **Tier 3: Engagement
Intelligence**.

It separates:

- what must happen before any Tier 3 implementation work starts
- what can proceed in parallel as planning/spec work
- what should happen before the later Tier 3 enrichment/provenance phases

Use this as the operational tracker. Update statuses as items are completed,
waived, or intentionally deferred.

## Decision Rule

Tier 3 **planning** may proceed now.

Tier 3 **implementation** should begin only when one of these is true:

- Tier 2 is formally closed, or
- Tier 2 has an explicit written waiver for the still-open items

Without one of those, the correct status is:

- `DO NOT START TIER 3 IMPLEMENTATION YET`

## Current Working Interpretation

- Tier 2 planning/status docs say Tier 3 planning can proceed in parallel.
- Tier 2 closeout docs say Tier 3 implementation should not start without a
  closeout decision or explicit waiver.
- `folio ingest` is the recommended first Tier 3 implementation slice.
- Per-stage routing plus a real library rerun is useful hardening, but not a
  hard blocker for the first `folio ingest` PR.
- A real engagement-library rerun is a stronger prerequisite for later
  `folio enrich` / provenance work than for initial ingest scaffolding.

## Required Before Any Tier 3 Code

| Seq | Action | Required | Machine | Owner | PASS Means | Required Artifact | Status |
|---|---|---|---|---|---|---|---|
| 1 | Sync baseline docs if still stale beyond PR #30 | Yes | Personal Folio dev laptop | Agents draft, you review/merge | PRD/roadmap/baseline docs match shipped reality closely enough for future prompts | Updated docs on `main` | Done |
| 2 | Make Tier 2 decision explicit (`GO` or waiver) | Yes | Personal Folio dev laptop | You decide; agents can draft wording | A written decision exists stating whether Tier 3 implementation is allowed to begin | `tier2_to_tier3_waiver_note.md` or equivalent decision note | Done |
| 3 | Freeze the first Tier 3 implementation slice as `folio ingest` only | Yes | Personal Folio dev laptop | Agents draft, you approve | Scope is explicit: no entities/enrich/provenance creep in the first PR | `docs/specs/v0.5.0_tier3_ingest_spec.md` | Drafted (pending review) |
| 4 | Assemble initial Tier 3 fixtures | Yes | Personal Folio dev laptop; McKinsey laptop if using real examples | Shared | Repo contains the minimum realistic inputs to drive ingest design and tests | Transcript fixtures, context example, org-chart CSV fixture | Not started |

## Safe To Start Immediately After The Gate

These items can begin once the required gate above is satisfied.

| Seq | Action | Required | Machine | Owner | PASS Means | Required Artifact | Status |
|---|---|---|---|---|---|---|---|
| 5 | Implement `folio ingest` CLI scaffold and tests | Yes | Personal Folio dev laptop | Agents implement, you review | CLI entrypoint exists with passing tests and narrow v1 scope | PR for `folio ingest` scaffold | Not started |
| 6 | Add interaction output contract | Yes | Personal Folio dev laptop | Agents implement | `type: interaction` output shape, frontmatter, and markdown body are defined and tested | Markdown/template + tests | Not started |
| 7 | Validate `folio ingest` on sample transcripts | Yes | Personal Folio dev laptop | Agents implement; you spot-check | Ingest works on representative sample inputs without expanding scope prematurely | Validation notes and tests | Not started |

## Strongly Recommended Before `folio enrich` / Provenance Work

These are not required to start the first Tier 3 PR, but should be completed
before the later enrichment and provenance-heavy workstreams.

| Seq | Action | Required | Machine | Owner | PASS Means | Required Artifact | Status |
|---|---|---|---|---|---|---|---|
| 8 | Decide whether to ship per-stage routing | Recommended | Personal Folio dev laptop | Agents draft/implement, you approve | Decision is explicit: implement now, defer, or waive | Short decision note or PR | Not started |
| 9 | Rerun the real engagement/library corpus with the current pipeline | Recommended before `enrich` | McKinsey laptop | You run; agents prepare commands/checklists | The working library reflects the latest quality/performance improvements before enrichment begins | Rerun notes/report | Not started |
| 10 | Validate real vault behavior on the engagement library | Recommended before `enrich` | McKinsey laptop | You | Obsidian behavior and real outputs are acceptable enough for Tier 3 enrichment to build on | Validation note/screenshots if useful | Not started |

## Machine Guide

| Work Type | Machine |
|---|---|
| Product docs, roadmap, PRD, prompts, specs | Personal Folio dev laptop |
| Code implementation, unit tests, integration tests, CLI scaffolding | Personal Folio dev laptop |
| Real engagement corpus reruns | McKinsey laptop |
| PowerPoint / real diagram-heavy deck validation | McKinsey laptop |
| Obsidian vault open/render checks on the real library | McKinsey laptop |
| 2-week daily-driver validation | McKinsey laptop |

## Owner Guide

| Work Type | Owner |
|---|---|
| Tier 2 go/waive decision | You |
| Drafting docs, prompts, specs | Agents |
| Implementing `folio ingest`, tests, fixtures | Agents |
| Reviewing scope, tradeoffs, and merges | You |
| Real engagement runs, real vault validation, daily-use validation | You |
| Preparing runbooks, commands, and checklists for real runs | Agents |

## Sequencing Rules

1. Do not start Tier 3 implementation until Seq 2 is complete.
2. Do not start entities or `folio enrich` before the first `folio ingest` slice
   is scoped and landed cleanly.
3. Do not treat per-stage routing as a blocker for the first `folio ingest` PR.
4. Do treat the real library rerun as a serious prerequisite before
   provenance-heavy or enrichment-heavy Tier 3 work.
5. Keep the first Tier 3 PR narrow: `folio ingest` only.

## Suggested Working Order

1. Update any still-stale baseline docs.
2. Record the Tier 2 go/waive decision explicitly.
3. Draft and approve the Tier 3 kickoff prompt/spec for `folio ingest`.
4. Assemble fixtures.
5. Implement `folio ingest`.
6. Decide on per-stage routing as a separate hardening track.
7. Rerun the engagement library on the McKinsey laptop before `folio enrich`.

## Live Checklist

- [x] Baseline product docs updated for PR #30
- [x] Tier 2 go/waive decision recorded explicitly
- [ ] Tier 3 kickoff prompt/spec drafted for `folio ingest`
- [ ] Initial Tier 3 fixtures assembled
- [ ] `folio ingest` scaffold implemented
- [ ] `folio ingest` output contract implemented and tested
- [ ] Sample transcript validation completed
- [ ] Per-stage routing decision recorded
- [ ] Real engagement/library rerun completed on McKinsey laptop
- [ ] Real vault validation completed on McKinsey laptop
