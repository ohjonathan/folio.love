---
id: doc_04_implementation_roadmap_v2
type: atom
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio: Implementation Roadmap v2

**Version 2.0 | February 2026**  
**folio.love**

**What changed from v1:** Incorporates features from the February 2026 brainstorming session (dual ontology, interaction ingestion, authority tiers, entity extraction, temporal roll-ups, retroactive provenance). Restructured from 3 phases to 4 tiers. Original Phase 1-2 priorities are unchanged. New features slot into Tiers 3-4 based on dependency chain and real-world validation requirements. Frontmatter schema aligned to Folio Ontology Architecture v2 (merged tags/concepts, date-based IDs, engagement requirement, frontmatter as relationship source of truth).

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

**Build later (requires infrastructure):**
- Interaction ingestion pipeline (Tier 3)
- Entity extraction, registry, and name resolution (Tier 3)
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
- Analysis validation against human judgment on 50 slides
- Caching by image hash (skip unchanged slides on re-convert)
- Error handling (graceful degradation, retry with backoff)

**Deliverable:** 90%+ framework detection accuracy. Cached analysis persists across runs.

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

---

## Tier 2: Daily Driver (Weeks 7-12)

**Goal:** Folio is a tool Johnny uses every day, not a script he runs occasionally. Proper CLI, multi-project organization, Obsidian compatibility.

**This is the original Phase 2 scope with minor additions.**

### Week 7-8: Package & CLI

- Python package structure (pyproject.toml, pip installable)
- `folio convert <file>` with --note, --target flags
- `folio batch <dir>` with --pattern, progress, error-per-file
- `folio status [scope]` with client/project scoping
- `folio scan` to find new/changed sources
- `folio refresh` to re-convert stale decks
- `folio promote <id> <level>` to update curation level

**Deliverable:** Working CLI for complete daily workflow.

### Week 9-10: Library Organization

- `folio.yaml` configuration (source roots, LLM settings, library root)
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
- [ ] Multi-client library organized and navigable
- [ ] Obsidian opens library with no errors
- [ ] Dataview queries work for all frontmatter fields
- [ ] Configuration supports multiple source roots
- [ ] Johnny uses it daily on real engagement for 2+ weeks

---

## Tier 3: Engagement Intelligence (Weeks 13-22)

**Goal:** Folio captures the full engagement lifecycle, not just decks. Meetings, interviews, and interactions become first-class content. Entities connect across documents.

**This is entirely new scope from the February brainstorm. Only start after Tier 2 is in daily use.**

### Week 13-15: Interaction Ingestion

**The highest-value brainstorm feature.** Solves the 5-step manual process (OneNote → audio → transcribe → ChatGPT → summarize) with one command.

- `folio ingest <file>` command accepting transcript (txt/md) or notes
- Interaction subtypes: client_meeting, expert_interview, internal_sync, partner_check_in, workshop
- Three auto-generated outputs per interaction:
  1. Narrative summary (what happened, key takeaways)
  2. Extracted entities (people, departments, systems as wikilinks)
  3. Structured insights (claims with attribution, data points, decisions, open questions)
- "Impact on Hypotheses" section created as empty stub at L0 (LLM lacks library context at ingest time; human fills during L0→L1, enrichment refines at L2)
- Frontmatter: type=interaction, authority=captured, curation_level=L0
- IDs follow date-based convention: `clienta_ddq126_interview_20260213_01`

**Open question for this phase:** OneNote → Markdown pathway. For v1, copy-paste transcript text into a .txt file is acceptable. Research better pathways as a side task.

**Deliverable:** One command converts a meeting transcript into structured, linked Markdown.

### Week 16-18: Entity System

- Entity registry (JSON file or markdown directory) for known people, departments, systems
- Name resolution during ingest: LLM proposes matches against registry, flags ambiguous cases
- `folio entities` command to view/manage registry
- `folio entities import <csv>` for bulk import (org chart)
- Entity wikilinks auto-created during ingest and enrich
- Person nodes with: name, title, department, reports_to

**Design constraint:** v1 entity resolution is exact-match + LLM-proposed soft-match with human confirmation. No fuzzy matching algorithm. Keep it simple.

**Deliverable:** People and departments are linked across interactions. "Show me all interviews mentioning Engineering" works via Obsidian search.

### Week 19-20: Enrichment & Provenance

- `folio enrich [scope]` command for post-hoc LLM enrichment
- Enrichment pass adds: tags, relationship links, entity extraction to existing assets
- Retroactive provenance linking: match deliverable claims against library evidence
- Human confirmation step for proposed provenance links
- Relationship types active: depends_on, draws_from, impacts

**Deliverable:** Even messy, fast-produced deliverables get connected to the clean library.

### Week 21-22: Context Documents & Integration

- Context document template (engagement scaffolding: client, SOW, team, industry, timeline)
- Context as single source for engagement metadata (other docs reference it)
- End-to-end test: full engagement lifecycle in Folio
  - Context doc → deck conversions → meeting ingestion → enrichment → linked library

**Deliverable:** Complete engagement captured in Folio with cross-document relationships.

### Tier 3 Exit Criteria

- [ ] `folio ingest` converts transcript to structured interaction in <60 seconds
- [ ] Entity registry tracks people, departments, systems
- [ ] Name resolution works for common cases (exact match + LLM soft match)
- [ ] `folio enrich` adds tags and links to existing assets
- [ ] Retroactive provenance links deliverable slides to evidence
- [ ] Context documents provide engagement scaffolding
- [ ] Full engagement lifecycle tested end-to-end

---

## Tier 4: Synthesis & Discovery (Weeks 23-32+)

**Goal:** The library reveals patterns, generates synthesis, and supports strategic prep. These features require volume (3+ months of daily content) to be useful.

**Only build when the library has enough depth that discovery becomes the bottleneck.**

### Week 23-25: Temporal Roll-Ups

- `folio digest` generates daily digest from all new/modified files
- `folio digest --week` generates weekly digest from daily digests
- Each level is a different analytical altitude:
  - Note-level: "What was said"
  - Daily: "What moved forward today"
  - Weekly: "Where do we stand and what's changed"
- Manual trigger for v1 (file watcher deferred)

### Week 26-28: Cross-References & Navigation

- Wiki links between related decks (same project, same framework)
- Maps of Content: auto-generated client and framework index pages
- `folio synthesize` for cross-asset synthesis (start with pairwise interview comparison, not N-way)
- Graph view tuning in Obsidian

### Week 29-32: Advanced Discovery

- Semantic search architecture (embedding model, index, query interface)
- Org chart traversal queries (evaluate whether Dataview suffices or custom engine needed)
- Concept vocabulary management (`folio vocab`)
- Cross-engagement pattern detection

### Tier 4 Exit Criteria

- [ ] Weekly digest saves real time on SteerCo prep
- [ ] Graph view shows meaningful structure across engagements
- [ ] Cross-references help navigate related content
- [ ] Would recommend the workflow to a colleague

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
folio ingest <file> --type <subtype> [--client X] [--notes raw.md]
folio enrich [scope]
folio entities [view|import <csv>]
folio link <id> <id> [type]
```

### Tier 4 (synthesis & discovery)
```bash
folio digest [--date today] [--week]
folio synthesize [options]
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

### Tier 4 Gate (Subjective)
- [ ] Synthesis features save real prep time
- [ ] Discovery reveals patterns not found manually
- [ ] System used across multiple engagements

---

## Open Design Questions (Updated)

**Resolved since v1:**
- Tags vs concepts: **Merged.** Single `tags` field with soft vocabulary validation.
- Relationship source of truth: **Frontmatter.** Wikilinks derived by `folio enrich`.
- `engagement` requirement: **Required at L1+** for engagement-scoped types. Optional for context, N/A for reference.
- ID convention: **Date-based.** `{client}_{engagement-short}_{type-short}_{date}_{descriptor}`.
- Impact on Hypotheses at L0: **Empty stub.** Human fills at L1, enrichment refines at L2.

**Still open:**

| # | Question | Tier | Notes |
|---|----------|------|-------|
| 1 | Semantic search architecture (embedding model, index, query interface) | 4 | Don't decide until query patterns are clear. |
| 2 | Entity resolution specifics (fuzzy matching approach) | 3 | v1: exact match + LLM soft match + human confirmation. |
| 3 | File watcher vs manual trigger for digest | 4 | Manual trigger for v1. |
| 4 | Context as standalone type vs metadata | 3 | Current spec: standalone document. Validate during Tier 3. |
| 5 | Org chart export format | 3 | Research what Johnny can actually export. CSV likely. |
| 6 | OneNote → Markdown pathway | 3 | Copy-paste for v1. Research better paths as side task. |
| 7 | PyPI package name availability (`folio`) | 2 | Check before Tier 2 packaging work. |
| 8 | LLM cost management at scale | 2 | Estimate per-deck cost. Consider capping batch operations. |
| 9 | `project` vs `engagement` field migration | 1 | Original docs used `project`. Ontology v2 uses `engagement`. Need to confirm these are interchangeable or define the mapping. |

---

## What Didn't Change

The original design principles, technology stack, library structure, conversion pipeline stages, and output format are all unchanged. The v2 roadmap adds scope and refines the schema but doesn't alter the architecture established in January.

The hierarchy of value remains the governing constraint: conversion quality first, always.
