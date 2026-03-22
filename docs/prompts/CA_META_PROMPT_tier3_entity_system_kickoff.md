---
id: ca_meta_prompt_tier3_entity_system_kickoff
type: atom
status: draft
ontos_schema: 2.2
generated_by: codex
created: 2026-03-22
---

# Prompt for CA: Draft the Tier 3 Entity-System Kickoff Spec

## Your Role

You are the **Chief Architect** for Folio Tier 3 planning.

Your task is to draft the **next kickoff spec**, not to implement code and not
to write an implementation prompt yet.

You are drafting the narrow follow-on spec after `folio ingest`:

- **Week 16-18: Entity System**

This is a **spec-authoring task only**.

Do not write code.
Do not start implementation decomposition.
Do not produce a Claude Code implementation prompt yet.

Your job is to read the current codebase and docs, identify where the approved
Tier 3 ingest slice ended, and write a **review-ready kickoff spec** for the
entity-system slice only.

---

## Task Context

`folio ingest` is now merged on `main` via PR #32.

That means the baseline has changed:

- interaction notes are now first-class `type: interaction` documents
- `folio ingest` already extracts entity-like mentions during ingest
- those entities are currently rendered as **unresolved wikilinks**
- mixed-library registry/status/scan behavior already supports interactions
- there is still **no entity registry**, **no `folio entities` command**, **no
  entity import path**, and **no registry-backed name resolution**

The roadmap says the next active slice is:

- **Entity registry**
- **name resolution during ingest**
- **`folio entities`**
- **`folio entities import <csv>`**

This prompt exists to make sure the next spec starts from the **actual merged
post-ingest reality**, not from older brainstorm language.

---

## What You Are Writing

Write a single markdown spec for the **entity-system kickoff slice**.

Proposed output path:

- `docs/specs/v0.5.1_tier3_entity_system_spec.md`

If, after reading the repo, you believe the version label should be different,
state that explicitly at the top of the spec and explain why. Do not silently
rename the slice.

The spec must be detailed enough that:

- other LLMs can review it critically
- a later CA prompt can use it as the approved source of truth
- a future implementation prompt can be written without re-inventing product
  decisions

---

## Required Reading Before Writing

Read these documents first.

### Product / architecture context

1. `docs/architecture/Folio_Ontology_Architecture.md`
   - especially the entity graph section and the rules that entities are graph
     nodes, not normal Folio documents
2. `docs/product/02_Product_Requirements_Document.md`
   - especially FR-500, FR-600, and FR-700
3. `docs/product/04_Implementation_Roadmap.md`
   - especially Tier 3 Week 16-18 and the current status tables
4. `docs/product/Folio_Feature_Handoff_Brief.md`
5. `docs/product/06_Prioritization_Matrix.md`
6. `docs/validation/tier3_kickoff_checklist.md`
7. `docs/validation/tier2_to_tier3_waiver_note.md`

### Prior Tier 3 slice

8. `docs/specs/v0.5.0_tier3_ingest_spec.md`
   - this is the immediate predecessor slice and contains deliberate deferrals
     around entity registry mutation and name resolution

### Live codebase reality

Read the current implementation, because the spec must anchor to what is
already shipped.

9. `folio/ingest.py`
10. `folio/pipeline/interaction_analysis.py`
11. `folio/output/interaction_markdown.py`
12. `folio/output/frontmatter.py`
13. `folio/cli.py`
14. `folio/tracking/registry.py`
15. `folio/tracking/versions.py`
16. `tests/validation/validate_frontmatter.py`
17. `tests/test_ingest_integration.py`
18. `tests/test_interaction_analysis.py`
19. `tests/test_registry.py`
20. `tests/test_cli_tier2.py`

Do not rely on summaries alone.

---

## Current Codebase Reality You Must Lock In

Your spec must explicitly reflect these facts if they are still true after your
codebase read:

1. `folio ingest` is already shipped and creates ontology-native interaction
   notes.
2. `interaction_analysis.py` already extracts people, departments, systems, and
   processes from source text.
3. `interaction_markdown.py` already renders those entities as unresolved
   wikilinks in `## Entities Mentioned`.
4. Mixed-library support is already present:
   - `registry.json` supports interaction entries
   - `folio status` includes interaction documents
   - `folio scan` includes `.txt` / `.md` transcript sources
   - `folio refresh` skips interaction entries and tells the user to re-run
     `folio ingest`
5. There is no shipped entity registry yet.
6. There is no shipped `folio entities` CLI yet.
7. There is no shipped entity import path yet.
8. There is no shipped registry-backed entity resolution yet.
9. `folio enrich` is still a later slice and must not be pulled into this spec.

If any of the above are no longer true, call that out explicitly in your draft.

---

## The Problem This Spec Must Solve

The current system surfaces entities visually, but not structurally.

Today, an interaction note can contain:

- `[[Jane Smith]]`
- `[[Engineering]]`
- `[[SAP ERP]]`

But those links are only unresolved names in markdown. There is no canonical
registry behind them, no import path for known org data, and no deliberate
policy for how ingest should decide whether:

- `Jane`
- `Jane Smith`
- `the CTO`

all refer to the same node.

The next spec must define the minimum viable entity system that makes these
names real graph nodes without collapsing into a broad enrichment platform.

---

## Scope You Must Cover

Your spec must decide, explicitly and concretely, at least these topics.

### 1. Entity registry model

- storage format for v1:
  - JSON file
  - markdown directory
  - or another minimal format if you can justify it from the current repo
- library location and path contract
- canonical schema per entity type
- whether the registry is global, client-scoped, or mixed
- how aliases are stored
- how `needs_confirmation` is represented

### 2. Supported entity types in the first slice

At minimum, evaluate:

- people
- departments
- systems
- processes

You must decide whether all four belong in the first entity-system slice or
whether the spec should narrow further. If you narrow it, explain why.

### 3. CLI surface

Define the intended v1 CLI contract for:

- `folio entities`
- `folio entities import <csv>`

Be explicit about whether the first version supports only:

- list/view
- import
- basic lookup

or whether it also supports create/edit/merge commands.

Do not hand-wave this as “to be decided later.”

### 4. Import contract

Define:

- required CSV columns
- optional CSV columns
- normalization rules
- duplicate handling
- update vs create behavior
- client-scoped vs global import behavior

The ontology currently points to org-chart import. Your spec must decide what
minimum viable import actually looks like in this repo.

### 5. Ingest-time resolution behavior

This is the most important design boundary.

Your spec must say exactly how the entity system interacts with already-shipped
`folio ingest`.

You must define:

- what ingest continues to extract
- how exact match works
- how aliases work
- how LLM-proposed soft match works, if included
- what happens when resolution is ambiguous
- whether new entities are auto-created, flagged, deferred, or written with
  `needs_confirmation`
- whether existing unresolved wikilinks from current ingest output should be
  preserved, rewritten, or only affected on re-ingest

### 6. Human confirmation boundary

The ontology and roadmap both imply human confirmation for ambiguous cases.

Your spec must define:

- what “human confirmation” means in the first slice
- whether it is CLI-driven, file-driven, or registry-flag driven
- what the user sees when ambiguity exists
- what is explicitly deferred to a later operational UX pass

### 7. Mixed-library and upgrade behavior

Your spec must explain how the entity system coexists with the already shipped:

- interaction notes
- registry.json
- `folio status`
- `folio scan`
- `folio refresh`
- `folio promote`

Be explicit about whether this slice:

- backfills existing interaction notes
- only affects new ingests
- supports targeted re-ingest for canonicalization
- requires any migration

### 8. Test and fixture plan

Your spec must define the fixture plan and test plan for the entity slice.

At minimum, cover:

- imported org-chart CSV
- exact-match resolution
- alias resolution
- ambiguous-match behavior
- unmatched entity creation/defer behavior
- interaction note rendering after resolution
- mixed-library regression behavior

---

## Constraints and Guardrails

The spec must stay narrow.

### Do not let the spec expand into:

- `folio enrich`
- retroactive provenance linking
- relationship graph authoring beyond what is strictly necessary for entities
- semantic search
- recursive org traversal
- broad context-document design
- broad ontology rewrites
- generic “knowledge graph platform” language without repo-grounded decisions

### Do not silently violate these existing choices:

- `folio ingest` already shipped with unresolved wikilinks
- the entity system is the next slice, not the whole remainder of Tier 3
- v1 entity resolution is supposed to remain:
  - exact match
  - LLM-proposed soft match
  - human confirmation
  - no fuzzy matching algorithm

If you think any of those boundaries are wrong, say so explicitly in a
“challenge to current assumptions” section. Do not quietly override them.

---

## Specific Questions The Spec Must Answer

Your draft should not leave these implicit:

1. Are entities stored as JSON, markdown files, or both in v1?
2. What exact fields exist for each entity type?
3. What is the canonical name vs alias policy?
4. How does `folio entities import` handle duplicates and updates?
5. What exact behavior should happen when ingest sees:
   - one exact match
   - multiple possible matches
   - no match
6. Does the first slice write new entity nodes automatically, or only after
   confirmation?
7. How do existing unresolved `[[Entity]]` mentions in already-created
   interaction notes relate to the new registry?
8. What minimal user workflow makes this useful before `folio enrich` exists?
9. Which parts of the ontology’s entity design are product requirements now,
   and which remain deferred?
10. What is the smallest buildable slice that materially improves the current
    shipped ingest baseline?

---

## Required Output Structure

Write the entity-system kickoff spec as a single markdown document with, at
minimum, these sections:

1. Overview
2. Why This Slice Comes Next
3. Goals
4. Non-Goals
5. Current Shipped Baseline
6. Key Decisions
7. Entity Registry Model
8. CLI Contract
9. Import Contract
10. Ingest-Time Resolution Contract
11. Human Confirmation / Ambiguity Handling
12. Mixed-Library / Migration Behavior
13. Test Plan
14. Acceptance Criteria
15. Open Questions for Reviewers

If you need additional sections, add them. But do not produce a vague memo.
This must be an implementation-adjacent kickoff spec, not a brainstorm recap.

---

## Review Standard

Write this as if it will be sent to other strong LLMs and reviewers for
critique.

That means:

- be concrete
- use file and command examples where helpful
- distinguish shipped reality from proposed changes
- separate product decisions from implementation details
- make the boundaries with `folio ingest` and `folio enrich` obvious

If you find a genuine conflict between the ontology, roadmap, and current code,
call it out explicitly in the spec rather than smoothing it over.

---

## What Not To Do

- Do not write code
- Do not generate an implementation plan
- Do not generate a Claude Code implementation prompt
- Do not redesign Tier 3 wholesale
- Do not pull `enrich` into scope
- Do not assume unresolved ingest wikilinks mean the entity problem is already
  solved
- Do not ignore the current repo state in favor of older brainstorm docs

---

## Final Instruction

Draft the entity-system kickoff spec so that, after review and approval, a
future CA session can turn it into an implementation prompt without reopening
the product decisions.
