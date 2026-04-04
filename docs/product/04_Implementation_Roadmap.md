---
id: doc_04_implementation_roadmap
type: atom
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio: Implementation Roadmap

**February 2026 baseline | April 2026 updated**
**folio.love**

**What changed from v1:** Incorporates features from the February 2026 brainstorming session (dual ontology, interaction ingestion, authority tiers, entity extraction, temporal roll-ups, retroactive provenance). Restructured from 3 phases to 4 tiers. Original Phase 1-2 priorities are unchanged. New features slot into Tiers 3-4 based on dependency chain and real-world validation requirements. Frontmatter schema aligned to the current Folio Ontology Architecture (merged tags/concepts, date-based IDs, engagement requirement, frontmatter as relationship source of truth).

---

## March-April 2026 Status Update

Since this roadmap was published, `main` has shipped twelve important baseline
changes:

- PR #8: multi-provider LLM analysis for `folio convert` / `folio batch`
  (Anthropic, OpenAI, Google Gemini), bring-your-own credentials via
  environment variables, named profiles, route-based selection,
  provider/model-aware cache invalidation, and `_llm_metadata` provenance
- PR #10: managed-mac PowerPoint reliability work (`open -a`, dedicated-session
  batch orchestration, automatic restart cadence, and retry-once on `-9074`)
- PR #12: fixed PowerPoint sandbox staging-dir export path
  (`~/Documents/.folio_pdf_staging/`) plus a full Tier 1 rerun on the same
  50-deck real consulting corpus used in the March baseline
- PR #14: Tier 1 closeout validation confirming OneDrive portability and
  same-PDF cache rerun behavior on real retained PDFs
- PR #15: Tier 2 daily-driver implementation (`registry.json`, `folio status`,
  `folio scan`, `folio refresh`, `folio promote`, source-root routing, and
  Obsidian query docs)
- PR #17: accelerated Tier 2 operational validation on a real engagement
  corpus, with an explicit recommendation to continue Tier 3 planning while
  formal Tier 2 closeout remains pending
- PR #30: enterprise performance hardening for `folio batch` and diagram
  extraction (content-hash deduplication, table-heavy `mixed -> text`
  reclassification, post-Pass-1 diagram gating, zero-text confidence
  tightening, and large-document warnings)
- PR #32: Tier 3 interaction ingestion (`folio ingest`, ontology-native
  `interaction` notes, mixed-library registry generalization, `routing.ingest`,
  degraded-output handling, and interaction-aware `status` / `scan` /
  `refresh`)
- PR #34: Tier 3 entity registry foundation (`entities.json`, `folio entities`,
  `folio entities import <csv>`, confirmation workflow, and entity-aware
  status summaries)
- PR #35: Tier 3 ingest-time entity resolution (confirmed-only exact and alias
  matching, bounded LLM soft-match proposals, canonical wikilink rendering,
  and unresolved-entity review flow)
- PR C: `folio enrich` shipped and production-tested on the retained
  production `anthropic_sonnet4` library (115 eligible notes enriched, 0
  failures, ~17 minutes, 6 high-quality `supersedes` proposals, and visible
  entity-link insertion across the note set)
- Post-PR-C follow-on: entity stub generation plus org-chart hierarchy merge
  (entity stub notes for Obsidian graph connectivity, trusted org-chart merge
  into person entities, and legacy registry `type` compatibility fallback)

This does **not** change the roadmap hierarchy. It does change the current
implementation baseline: multi-provider LLM support is now shipped foundation,
the managed-mac automated PPTX conversion path has been rerun successfully on
the real Tier 1 corpus, and the enterprise-scale batch path now includes the
first round of runtime-waste controls discovered in field deployment. Tier 3 is
no longer purely planned scope: the Week 13-15 interaction-ingestion slice, the
Week 16-18 entity-system slice, PR C `folio enrich`, PR D
`folio provenance`, and PR E context documents are now shipped on `main`.

Late-March validation also changed the **operational baseline**. The Tier 2
platform model-comparison package is finalized, and its recorded per-stage
winners differ from the single-route runtime path currently available on
`main`. A full-corpus rerun with `anthropic_haiku45` did **not** beat the
existing production `anthropic_sonnet4` library overall, so the production
library was retained and selectively improved with 12 blind-validated
`haiku45` merges. Real vault validation then passed that production library to
PR C (`folio enrich`). Tier 3 closeout then completed on the retained
production baseline, the carried-forward production ingest validation was
closed on 2026-04-04 with a real `folio ingest` run in about 25 seconds, and
the production `entities.json` bootstrap was completed on 2026-04-04 from the
engagement org chart. See `docs/product/tier3_baseline_decision_memo.md` for
the full status delta
since the last shared PRD/roadmap sync.

Current Tier 1 reality after PR #14:

- Managed-mac automated PPTX rerun: **50/50 succeeded** on the March 2026 real
  corpus (**49/50 clean output**), with zero conversion failures during the
  main run; see `docs/validation/tier1_rerun_report.md`
- Batch fatigue mitigation: 3 automatic PowerPoint restarts, zero operator
  intervention during the main run after the one-time staging-dir grant
- Output quality: one documented template-only edge case in `building_blocks`;
  no structural silent failures in the rerun report
- Same-PDF cache rerun behavior on an identical PDF with no content change:
  **PASS** in `docs/validation/tier1_closeout_report.md`
- Automated-PPTX rerun cache persistence remains a **known deferred
  limitation** because PowerPoint PDF output is non-deterministic
- Cross-machine portability (OneDrive sync test): **PASS** in
  `docs/validation/tier1_closeout_report.md`

Remaining Tier 1 carried-forward limitations after closeout:

- Pass 2 fallback provenance should be surfaced more cleanly in execution
  metadata/frontmatter
- Automated-PPTX rerun cache persistence remains deferred until the follow-on
  cache work lands
- `building_blocks` remains a documented template-only edge case rather than a
  general pipeline defect

---

## The Hierarchy (Still Immutable)

```
1. CONVERSION QUALITY    ← Tier 1 focus
2. VERSION INTEGRITY     ← Tier 1 focus  
3. ORGANIZATION          ← Tier 2 focus
4. KNOWLEDGE GRAPH       ← Tiers 3-4 focus
```

Nothing from the brainstorm changes this ordering. The new features amplify levels 3 and 4 but depend entirely on levels 1 and 2 being solid.

---

## Architecture Evolution

The brainstorm session confirmed a dual ontology (Space + Time) and introduced several new concepts. The ontology architecture has been fully specified in `Folio_Ontology_Architecture.md` (v2). Here's what gets baked in now vs. built later:

**Bake into schema now (zero cost):**
- `authority` field in frontmatter (captured / analyzed / aligned / decided)
- `curation_level` field (L0 / L1 / L2 / L3)
- `type` and `subtype` fields aligned to ontology (evidence, deliverable, reference, context, analysis, interaction)
- Unified `tags` field (merged from separate `tags` and `concepts`) with soft vocabulary validation
- Date-based ID convention: `{client}_{engagement-short}_{type-short}_{date}_{descriptor}`
- Relationship type vocabulary (depends_on, draws_from, impacts, relates_to, supersedes, instantiates)
- `engagement` field required at L1+ for engagement-scoped types
- Frontmatter as single source of truth for relationships (wikilinks derived by `folio enrich`)

**Already shipped on `main`:**
- Interaction ingestion pipeline (Tier 3, PR #32)
- Entity registry, import, and ingest-time name resolution (Tier 3, PR #34/#35)

**Build later (requires infrastructure):**
- Enrichment engine that generates wikilinks from frontmatter and promotes manual wikilinks (Tier 3)
- Temporal roll-ups as Analysis/digest documents (Tier 4)
- Semantic search (Tier 4)

---

## Updated Frontmatter Schema

This is the target schema from day one. Not every field will be populated automatically in Tier 1, but the schema is stable so nothing needs rework later. See `Folio_Ontology_Architecture.md` Section 12 for the complete field reference.

**Key design decisions baked into this schema:**
- **Single `tags` field** (merged from separate `tags` and `concepts` fields). Soft vocabulary validation at the tool level.
- **`authority` tier** orthogonal to `curation_level`. Epistemic weight vs. document completeness.
- **`engagement` required at L1+** for engagement-scoped types (analysis, evidence, deliverable, interaction). Optional for context, not applicable to reference.
- **Date-based ID convention**: `{client}_{engagement-short}_{type-short}_{date}_{descriptor}`. IDs are immutable. Human-readable names go in `title`.
- **Frontmatter is source of truth** for relationships. Wikilinks in document bodies are derived by `folio enrich`.

```yaml
---
# Identity
id: clienta_ddq126_evidence_20260210_market-sizing
title: Market Sizing Analysis
type: evidence
subtype: research

# Source tracking
source: ../../../sources/ClientA/Project1/market_sizing.pptx
source_hash: abc123def456
source_type: deck
version: 2
converted: 2026-02-20T14:30:00Z

# Organization
client: ClientA
engagement: Due Diligence Q1 2026
status: current              # current | stale | missing

# Ontology
authority: captured          # captured | analyzed | aligned | decided
curation_level: L0           # L0 | L1 | L2 | L3

# Content classification
frameworks:
  - 2x2-matrix
  - scr
slide_types:
  - executive-summary
  - framework
tags:
  - market-sizing
  - competitive-analysis
  - retail
  - tam

# Relationships (populated manually or by folio enrich, Tier 3)
# depends_on: []
# draws_from: []
---
```

**What's new vs. v1:** `id` (date-based convention), `type`/`subtype` (ontology-aligned), `authority`, `curation_level`, `engagement`, `source_type`. Merged `concepts` into `tags`. Removed `project` (replaced by `engagement`). Relationships use frontmatter as source of truth.

---

## Tier 1: Conversion Quality (Weeks 1-6)

**Goal:** Every conversion is trustworthy. No missing images, no mangled text, no broken source links. Frontmatter includes full ontology-aware schema from day one.

**This is the original Phase 1 scope, extended by ~3 weeks to include proper testing and the schema updates.**

### Week 1-2: Core Pipeline

- Image extraction reliability (handle unusual page sizes, blank page detection)
- Text extraction accuracy (special chars, bullets, tables, automated diffing)
- Source tracking (relative paths, hash computation, validation)
- Markdown assembly with updated frontmatter schema

**Deliverable:** Pipeline that converts any PPTX/PDF without silent failures.

### Week 3: LLM Analysis

- Prompt engineering for consulting frameworks (2x2, SCR, MECE, waterfall, Gantt, org chart)
- Multi-provider LLM analysis for `convert` (Anthropic, OpenAI, Google Gemini)
- Named LLM profiles in `folio.yaml` with route-based selection for `convert`
- `--llm-profile` override for deterministic single-profile runs
- Provider-aware graceful degradation and transient-only fallback chains
- Analysis validation against human judgment on 50 slides
- Caching by image hash (skip unchanged slides on re-convert)
- Cache invalidation scoped by provider/model/prompt identity
- Error handling (graceful degradation, retry with backoff)

**Deliverable:** 90%+ framework detection accuracy. Cache invalidation is
provider/model-aware and stable for same-PDF reruns; automated-PPTX rerun cache
persistence remains deferred.

### Week 4: Version Tracking

- Change detection (single-word changes, slide reorder, add/remove)
- Staleness detection (hash comparison, clear status output)
- Version history persistence (atomic writes, survives re-conversion)
- Integration test: convert → edit source → re-convert → verify 5 versions

**Deliverable:** Change detection you can trust completely.

### Week 5-6: Validation & Hardening

- Convert 50 real consulting decks
- Fix every failure mode discovered
- Verify frontmatter completeness (all schema fields populated correctly)
- Test cross-machine portability (relative paths with OneDrive)
- Document failure modes and edge cases

**Deliverable:** Confidence to use on real engagement materials.

### Tier 1 Exit Criteria

- [ ] 50 real decks converted with zero silent failures
- [ ] Every slide has image, verbatim text, and LLM analysis
- [ ] Source tracking works across machines (OneDrive sync test)
- [ ] Change detection correctly identifies modifications, additions, removals
- [ ] Staleness detection flags outdated conversions
- [ ] Frontmatter includes all v2 schema fields (`type`, `subtype`, `authority`, `curation_level`)
- [ ] IDs follow date-based convention (`{client}_{engagement}_{type}_{date}_{descriptor}`)
- [ ] Authority defaults to `captured`, curation_level to `L0` for converted decks
- [ ] Tags populated from LLM analysis with soft vocabulary validation

### Current Status Against Tier 1 Exit Criteria

The table below tracks current progress against the exit criteria above; the
unchecked boxes remain the canonical gate list.

| Checkpoint | Current Status | Evidence / Notes |
|-----------|----------------|------------------|
| 50 real decks converted with zero silent failures | Qualified pass on managed-mac rerun (49/50 clean; 1 template edge case) | `docs/validation/tier1_rerun_report.md` records 50/50 automated PPTX success on the March corpus, with one documented `building_blocks` quality edge case |
| Every slide has image, verbatim text, and analysis | Mostly achieved; 1 documented template edge case | `building_blocks` is recorded as a non-structural quality edge case in the rerun report |
| Change detection and staleness | Achieved on sampled rerun checks | `folio status` and version increment behavior were verified during the rerun |
| Frontmatter / ontology-v2 completeness | Achieved for 49/50 in strict validation | One template edge case remains documented in the rerun report |
| IDs follow date-based convention | Achieved | Ontology-v2 schema and current product docs standardize on `{client}_{engagement}_{type}_{date}_{descriptor}` IDs |
| Authority defaults to `captured`, curation_level to `L0` | Achieved | This is the documented default for converted decks in the ontology-v2-aligned baseline |
| Tags populated from LLM analysis with soft vocabulary validation | Tags are populated by LLM analysis; vocabulary validation was not separately re-verified | The rerun exercised LLM analysis broadly, but soft vocabulary validation was not called out as a separate verification line item |
| Cross-machine portability (OneDrive sync) | Not yet tested | Still open follow-up after PR #12 |
| Automated-PPTX rerun cache persistence | Deferred known limitation | Same-PDF rerun should work; automated-PPTX rerun cache persistence remains out of scope until the follow-on cache work lands |

---

## Tier 2: Daily Driver (Weeks 7-12)

**Goal:** Folio is a tool Johnny uses every day, not a script he runs occasionally. Proper CLI, multi-engagement organization, Obsidian compatibility.

**This is the original Phase 2 scope with minor additions.**

### Week 7-8: Package & CLI

- Python package structure (pyproject.toml, pip installable)
- `folio convert <file>` with --note, --target, and `--llm-profile` flags
- `folio batch <dir>` with --pattern, progress, error-per-file, and `--llm-profile`
- `folio status [scope]` with client/engagement or library-relative scoping
- `folio scan` to find new/changed sources
- `folio refresh` to re-convert stale decks
- `folio promote <id> <level>` to update curation level

**Deliverable:** Working CLI for complete daily workflow.

### Week 9-10: Library Organization

- `folio.yaml` configuration (source roots, named LLM profiles/routing, library root)
- Client/Project/Deck directory hierarchy
- Internal and Research as top-level peers
- Registry (registry.json) with full index, status aggregation
- Source directory mapping (multiple roots)

**Deliverable:** Library with 100+ decks across 5+ clients, organized and navigable.

### Week 11-12: Obsidian Integration

- Frontmatter completeness testing (all fields, Dataview-queryable)
- Image rendering verification
- Search by tag, framework, client, doc_type, authority
- Dataview query cookbook (common queries documented)
- Basic link compatibility (standard markdown links)

**Deliverable:** Library opens as Obsidian vault with full search and filter capability.

### Tier 2 Exit Criteria

- [ ] CLI handles full daily workflow (convert, batch, status, scan, refresh, promote)
- [ ] `folio convert` and `folio batch` support route-based LLM selection plus `--llm-profile` override
- [ ] Multi-client library organized and navigable
- [ ] Obsidian opens library with no errors
- [ ] Dataview queries work for all frontmatter fields
- [ ] Configuration supports multiple source roots
- [ ] Configuration supports named LLM profiles and provider-specific credential references
- [ ] Johnny uses it daily on real engagement for 2+ weeks

### Current Status Against Tier 2 Exit Criteria

The table below tracks current progress against the Tier 2 exit criteria above.
The unchecked boxes remain the canonical gate list.

| Checkpoint | Current Status | Evidence / Notes |
|-----------|----------------|------------------|
| CLI handles full daily workflow | Achieved in accelerated operational validation | `docs/validation/tier2_accelerated_precloseout_report.md` records successful `convert`, `batch`, `status`, `scan`, `refresh`, and `promote` runs on a real engagement corpus |
| Route-based LLM selection plus `--llm-profile` override | Achieved in accelerated operational validation | Default routing and explicit `--llm-profile` override were both verified in `_llm_metadata` during the accelerated run |
| Multi-client library organized and navigable | Partial | Accelerated run validated 9 decks for 1 client; the formal 100+ deck / 5+ client target remains open |
| Obsidian opens library with no errors | Partial | Frontmatter and slide-image rendering checks passed, but manual vault-open confirmation and inline content image limitations remain open |
| Dataview queries work for all frontmatter fields | Achieved on accelerated sample | Required Dataview-queryable fields were present across the accelerated validation sample; one template file had no frameworks |
| Configuration supports multiple source roots | Partial | Non-empty `target_prefix` routing passed; empty `target_prefix` validation remains blocked by broken validation-corpus symlinks |
| Configuration supports named LLM profiles and credential references | Achieved | Named profiles, credential env-var references, route-based selection, and single-command override are all in current `main` and exercised in the accelerated run |
| Johnny uses it daily on real engagement for 2+ weeks | Not yet complete | The accelerated pre-closeout explicitly does not satisfy the formal 2-week daily-use criterion |

Current program status after the late-March validation cycle:

- Tier 2 implementation remains on `main`, though formal Tier 2 closeout is
  still pending the remaining gate items above
- Tier 3 implementation is proceeding under the explicit waiver recorded in
  `docs/validation/tier2_to_tier3_waiver_note.md`
- Week 13-15 interaction ingestion is shipped on `main` via PR #32
- Week 16-18 entity registry and ingest-time resolution are shipped on `main`
  via PR #34 and PR #35
- The Tier 2 model-comparison package, full-corpus rerun, and real vault
  validation have all completed
- The production `sonnet4` library, selectively improved with 12 blind-
  validated `haiku45` merges, is the baseline for the next slice
- PR C `folio enrich` is shipped and production-tested on the retained
  production library baseline
- The entity stubs + org-chart merge follow-on is the current closing slice
  for the enrich baseline
- PR D retroactive provenance is shipped on `main`
- PR E context docs + Tier 3 closeout is the current closing slice

---

## Tier 3: Engagement Intelligence (Weeks 13-22)

**Goal:** Folio captures the full engagement lifecycle, not just decks. Meetings, interviews, and interactions become first-class content. Entities connect across documents.

**This is entirely new scope from the February brainstorm.** The original gate
was “only start after Tier 2 is in daily use.” In practice, Week 13-15 shipped
under the explicit Tier 2 waiver while formal Tier 2 closeout remained
pending.

### Week 13-15: Interaction Ingestion

**Status:** Shipped on `main` in PR #32.

**The highest-value brainstorm feature.** Solves the 5-step manual process
(OneNote → audio → transcribe → ChatGPT → summarize) with one command.

- `folio ingest <file>` command accepting transcript (txt/md) or notes
- Interaction subtypes: client_meeting, expert_interview, internal_sync, partner_check_in, workshop
- Single ontology-native interaction note per ingest containing:
  1. Narrative summary (what happened, key takeaways)
  2. Extracted entities (people, departments, systems as unresolved wikilinks)
  3. Structured insights (claims with attribution, data points, decisions, open questions)
- "Impact on Hypotheses" section created as empty stub at L0 (LLM lacks library context at ingest time; human fills during L0→L1, enrichment refines at L2)
- Frontmatter: type=interaction, authority=captured, curation_level=L0
- Frontmatter uses `source_transcript` + `source_hash`, not evidence-only source fields
- Re-ingest resolves identity by explicit target, `source_transcript`, or `source_hash`
- Mixed-library commands now include interaction entries in `status` / `scan`; `refresh` skips them with rerun guidance to use `folio ingest`
- IDs follow date-based convention, for example: `clienta_ddq126_interview_20260213_01`

**Open question for this phase:** OneNote → Markdown pathway. For v1, copy-paste transcript text into a .txt file is acceptable. Research better pathways as a side task.

**Deliverable:** Achieved. One command converts a meeting transcript into a
structured, linked interaction note.

### Week 16-18: Entity System

**Status:** Shipped on `main` in PR #34 and PR #35.

- `entities.json` registry for known people, departments, systems, and processes
- `folio entities` command family for list/show/import/confirm/reject
- `folio entities import <csv>` for org-chart bulk import
- Ingest-time name resolution against confirmed entities using exact
  canonical-name and alias matching
- Bounded LLM-proposed soft matches with human confirmation
- Unresolved entities auto-created as unconfirmed so they are visible for
  follow-up but excluded from future resolution until confirmed
- Canonical entity wikilinks rendered during ingest and re-ingest

**Design constraint:** v1 entity resolution is exact-match + LLM-proposed soft-match with human confirmation. No fuzzy matching algorithm. Keep it simple.

**Deliverable:** Achieved. People, departments, systems, and processes can be
tracked in a canonical registry, and interaction notes can resolve common cases
to stable entity names during ingest.

### Week 19-20: Enrichment & Provenance

**Status:** PR C `folio enrich` is shipped and production-tested. PR D
retroactive provenance (`folio provenance`) is shipped on `main` (PR #39).

- `folio enrich [scope]` command for post-hoc LLM enrichment
- Enrichment pass adds: tags, relationship links, entity extraction to existing assets
- Post-PR-C follow-on adds entity stub generation and trusted org-chart
  hierarchy merge for richer graph connectivity
- Retroactive provenance linking (infrastructure + evidence version-lineage pilot): `folio provenance` matches grounded claims in newer evidence notes to structured `**Evidence:**` entries in confirmed `supersedes` predecessors
- Human confirmation step for proposed provenance links
- Relationship types active: supersedes (shipped), depends_on, draws_from, impacts

**Current baseline for this phase:** the retained production
`anthropic_sonnet4` library plus the 12 blind-validated `haiku45` merges was
used successfully for PR C production testing: 115/115 eligible notes
enriched, 0 failures, approximately 17 minutes runtime, 3 generated
`## Related` sections, and 6 plausible `supersedes` proposals.

**Deliverable:** Provenance infrastructure is proven on evidence version-lineage pairs in the retained production library. Deliverable-to-evidence provenance remains the v2 extension when deliverable notes enter the registry.

### Week 21-22: Context Documents & Integration

**Status:** PR E (`folio context init`, registry schema v2, Tier 3 lifecycle
integration test) is shipping in PR #40.

- `folio context init` creates engagement context documents at canonical paths
- Context docs are first-class registry citizens (`type: context`, `subtype: engagement`)
- Registry schema v2 supports source-less managed documents alongside evidence/interaction rows
- `folio status` shows per-type summary including context docs
- `folio scan` and `folio refresh` safely ignore context rows
- `folio enrich` and `folio provenance` do not consume context docs in v1
- Frontmatter validator treats context as a distinct first-class type
- End-to-end synthetic lifecycle test covers:
  context init → evidence seed → entity import/confirm → ingest (mocked LLM) →
  entity stubs → enrich (mocked LLM) → provenance (mocked LLM) → confirm-doc →
  status / scan / refresh → final registry validation

**Deliverable:** Context documents provide engagement scaffolding. Full
synthetic lifecycle test proves the complete Tier 3 pipeline end-to-end.

### Tier 3 Exit Criteria

- [x] `folio ingest` converts transcript to structured interaction in <60 seconds
- [x] Entity registry tracks people, departments, systems
- [x] Name resolution works for common cases (exact match + LLM soft match)
- [x] `folio enrich` adds tags and links to existing assets
- [x] Retroactive provenance infrastructure works on confirmed `supersedes`-linked evidence pairs
- [x] Context documents provide engagement scaffolding
- [x] Full engagement lifecycle tested end-to-end

### Current Status Against Tier 3 Exit Criteria

| Checkpoint | Current Status | Evidence / Notes |
|-----------|----------------|------------------|
| `folio ingest` converts transcript to structured interaction in <60 seconds | Met with production evidence | Tier 3 closeout accepted the shipped baseline, and the remaining field-validation follow-up was closed on 2026-04-04 by a real production transcript ingest in about 25 seconds using `anthropic_sonnet4` / `claude-sonnet-4-20250514`. |
| Entity registry tracks people, departments, systems | Met with production bootstrap evidence | PR #34 shipped the registry, CLI, CSV import, and confirmation workflow; on 2026-04-04 the production library bootstrap imported 1,492 people plus 9 departments into `entities.json`. |
| Name resolution works for common cases | Met | PR #35 shipped confirmed-only exact/alias resolution, bounded soft-match proposals, and unresolved-entity review flow on `main`. |
| `folio enrich` adds tags and links to existing assets | Met | PR C enriched 115/115 eligible notes on the retained production `sonnet4` library with 0 failures in about 17 minutes; Tier 3 closeout accepted the enrich path on the production baseline. |
| Retroactive provenance infrastructure works on confirmed `supersedes`-linked evidence pairs | Met | PR D (#39) shipped the `folio provenance` pipeline on `main`, and Tier 3 closeout accepted the production-validation gate. |
| Context documents provide engagement scaffolding | Met | PR E (#40) shipped `folio context init`, registry schema v2, source-less managed documents, and production validation of a real context note visible in `folio status`. |
| Full engagement lifecycle tested end-to-end | Met | PR E shipped the lifecycle integration test covering context → evidence → entity → ingest → enrich → provenance → status / scan / refresh, and Tier 3 closeout accepted it as the final integration proof. |

---

## Tier 4: Synthesis & Discovery (Weeks 23-32+)

**Goal:** The library reveals patterns, generates synthesis, and supports strategic prep. These features require volume (3+ months of daily content) to be useful.

**Only build when the library has enough depth that discovery becomes the bottleneck.**

Tier 4 is now ready to begin on the retained production library. The remaining
post-closeout operational follow-ups were closed on 2026-04-04, so the first
implementation slice is `folio digest`.

### Tier 4 Implementation Order

1. Daily digest (`folio digest`)
2. Weekly digest (`folio digest --week`)
3. Related links + Maps of Content
4. `folio synthesize`
5. Advanced / deferred discovery work (`folio search`, org traversal queries,
   graph tuning, optional watcher)

### Week 23-25: Temporal Roll-Ups

- `folio digest <scope>` generates daily digest from scoped new/modified files
- `folio digest <scope> --week` generates weekly digest from daily digests
- Each level is a different analytical altitude:
  - Note-level: "What was said"
  - Daily: "What moved forward today"
  - Weekly: "Where do we stand and what's changed"
  - SteerCo: "What leadership needs to decide"
- Manual trigger for v1 (file watcher deferred)

### Week 26-28: Cross-References & Navigation

- Wiki links between related decks (same project, same framework)
- Maps of Content: auto-generated client and framework index pages
- `folio synthesize` for cross-asset synthesis (start with pairwise interview comparison, not N-way)
- Graph view tuning in Obsidian

### Week 29-32: Advanced Discovery

- Semantic search architecture (embedding model, index, query interface)
- Org traversal queries (evaluate whether Dataview suffices or custom engine needed)
- Tag vocabulary management (`folio vocab`)
- Optional file watcher for auto-digest after the manual workflow proves useful

### Tier 4 Exit Criteria

- [ ] Daily and weekly digests generate registered `analysis/digest` notes on the retained production library
- [ ] Weekly digest is used in at least one real SteerCo-prep cycle
- [ ] Related links or Maps of Content reduce navigation work on one active engagement
- [ ] At least one Tier 4 discovery surface is useful enough to recommend the workflow to a colleague

---

## Timeline Summary

| Tier | Duration | Weeks | Focus |
|------|----------|-------|-------|
| 1: Conversion Quality | 6 weeks | 1-6 | Bulletproof pipeline + v2 schema |
| 2: Daily Driver | 6 weeks | 7-12 | CLI, organization, Obsidian |
| 3: Engagement Intelligence | 10 weeks | 13-22 | Ingest, entities, enrichment |
| 4: Synthesis & Discovery | 10+ weeks | 23-32+ | Digests, search, graph |
| **Total** | **~32 weeks** | | |

**Reality check:** These are development weeks, not calendar weeks. At 10-15 hours/week alongside a McKinsey engagement, Tier 1 is ~1-1.5 calendar months, Tier 2 is similar, and Tiers 3-4 stretch across multiple engagements.

---

## Updated CLI Command Map

### Tier 1 (internal only, no CLI)
Pipeline runs as Python functions during development and testing.

### Tier 2 (daily driver)
```bash
folio convert <file> [--note "..."] [--target <path>]
folio batch <dir> [--pattern "*.pptx"]
folio status [scope]
folio scan
folio refresh [--scope <path>]
folio promote <id> <level>
```

### Tier 3 (engagement intelligence)
```bash
folio ingest <file> --type <subtype> --date YYYY-MM-DD [--client X] [--engagement Y] [--participants "A, B"] [--llm-profile profile]
folio entities [--type person|department|system|process] [--unconfirmed]
folio entities show <name> [--type person|department|system|process]
folio entities import <csv>
folio entities confirm <name>
folio entities reject <name>
folio enrich [scope]
folio provenance [scope] [--dry-run] [--llm-profile <profile>] [--limit N] [--force] [--clear-rejections]
folio provenance review [scope] [--include-low] [--stale] [--doc <doc_id>] [--target <doc_id>] [--page N]
folio provenance status [scope]
folio provenance confirm-doc <doc_id>
folio context init --client <name> --engagement <name> [--target <path>]
folio link <id> <id> [type]
```

### Tier 4 (synthesis & discovery)
```bash
folio digest <scope> [--date YYYY-MM-DD] [--week] [--llm-profile <profile>]
folio synthesize <doc_a> <doc_b> [options]
folio search <query>
folio vocab
```

---

## Risk Register (Updated)

| Risk | Likelihood | Impact | Tier | Mitigation |
|------|------------|--------|------|------------|
| Text extraction accuracy issues | Medium | Critical | 1 | Extensive testing, fallback to image-only |
| LLM analysis inconsistent | Medium | Medium | 1 | Prompt iteration, manual override option |
| Source path breaks on sync | Medium | High | 1 | Test with OneDrive/Dropbox early |
| Scope creep from brainstorm features | **High** | **High** | All | **Strict tier gating. Don't start Tier N+1 until Tier N exit criteria pass.** |
| Entity name resolution too hard | Medium | Medium | 3 | Start with exact match + human confirmation. No fuzzy matching in v1. |
| Semantic search architectural lock-in | Medium | High | 4 | Defer until query patterns are clear from real usage. Don't pick an embedding model prematurely. |
| Org traversal exceeds Obsidian capability | High | Medium | 4 | Flat entity queries (Tier 3) cover 80% of cases. Only invest in traversal if real need demonstrated. |
| Tier 4 LLM cost grows with library volume | Medium | Medium | 4 | Keep digest manual by default, scope runs to one engagement, and measure prompt/runtime cost before adding automation. |
| Time constraints (active engagement) | **High** | **High** | All | Tier 1 is the minimum viable product. Everything after is incremental value. |

---

## Quality Gates

### Tier 1 Gate (Must Pass)
- [ ] Zero silent conversion failures in 50-deck test
- [ ] Text extraction accuracy >99%
- [ ] Image present for every slide
- [ ] Source path valid for every conversion
- [ ] Change detection accuracy >95%
- [ ] Frontmatter v2 schema complete

### Tier 2 Gate (Must Pass)
- [ ] CLI handles daily workflow for 2+ weeks
- [ ] 100+ deck library organized correctly
- [ ] Obsidian opens without errors
- [ ] Dataview queries work for all frontmatter fields

### Tier 3 Gate (Must Pass)
- [ ] `folio ingest` replaces manual meeting note workflow
- [ ] Entity registry tracks engagement stakeholders
- [ ] Enrichment adds useful connections to existing assets
- [ ] Full engagement lifecycle captured end-to-end

### Tier 4 Gate
- [ ] Daily and weekly digests generate registered `analysis/digest` notes on the retained production library
- [ ] Weekly digest is used in at least one real SteerCo-prep cycle
- [ ] Related links or Maps of Content reduce navigation work on one active engagement
- [ ] At least one Tier 4 discovery surface is useful enough to recommend the workflow to a colleague

---

## Open Design Questions (Updated)

**Resolved since v1:**
- Tags vs concepts: **Merged.** Single `tags` field with soft vocabulary validation.
- Relationship source of truth: **Frontmatter.** Wikilinks derived by `folio enrich`.
- `engagement` requirement: **Required at L1+** for engagement-scoped types. Optional for context, N/A for reference.
- ID convention: **Date-based.** `{client}_{engagement-short}_{type-short}_{date}_{descriptor}`.
- Impact on Hypotheses at L0: **Empty stub.** Human fills at L1, enrichment refines at L2.
- `project` vs `engagement`: **Resolved in docs/schema.** `engagement` is the metadata field; filesystem paths may still use project-like folder names.
- Entity resolution in v1: **Resolved.** Exact canonical-name match + alias match + bounded LLM soft match + human confirmation. No algorithmic fuzzy matcher.
- Org chart import format: **Resolved for v1.** CSV via `folio entities import <csv>`.

**Still open:**

| # | Question | Tier | Notes |
|---|----------|------|-------|
| 1 | Semantic search architecture (embedding model, index, query interface) | 4 | Don't decide until query patterns are clear. |
| 2 | Entity resolution beyond v1 (production-scale exercise, enrichment-time backfill) | 3 | v1 shipped: exact + alias + bounded LLM soft match. Production exercise and enrichment-time entity backfill remain untested. |
| 3 | File watcher vs manual trigger for digest | 4 | Manual trigger for v1. |
| 4 | Context as standalone type vs metadata | 3 | **Resolved in PR E.** Context is a standalone first-class managed document type with its own registry schema, CLI surface (`folio context init`), and frontmatter contract. |
| 5 | OneNote → Markdown pathway | 3 | Copy-paste for v1. Research better paths as side task. |
| 6 | PyPI package name availability (`folio`) | 2 | Check before Tier 2 packaging work. |
| 7 | LLM cost management at scale | 2 | Estimate per-deck cost. Consider capping batch operations. |
| 8 | Cross-engagement pattern detection | Future backlog | Keep out of the committed Tier 4 feature set until digest, synthesize, and search prove a concrete multi-engagement need. |

---

## What Didn't Change

The original design principles, technology stack, library structure, conversion pipeline stages, and output format are all unchanged. The v2 roadmap adds scope and refines the schema but doesn't alter the architecture established in January.

The hierarchy of value remains the governing constraint: conversion quality first, always.
