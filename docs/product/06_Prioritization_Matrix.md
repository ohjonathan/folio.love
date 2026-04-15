---
id: doc_06_prioritization_matrix
type: product
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio: Feature Prioritization Matrix

**Version 2.2 | April 2026**
**folio.love**

---

## How to Read This

Every feature from both sessions (January architecture + February brainstorm) is mapped here. The matrix uses two axes:

- **Value:** How much this improves Johnny's actual workflow. Scored relative to the hierarchy of value (conversion quality > version integrity > organization > knowledge graph).
- **Effort:** Implementation complexity including dependencies, external services, and design risk. Scored as engineering weeks for a solo developer using agentic tools.

Features are grouped into implementation tiers, not by when they were conceived.

---

## Tier 1: Foundation (Build First)

These are the original Phase 1 features plus cheap schema decisions from the brainstorm that avoid rework later.

| ID | Feature | Value | Effort | Rationale |
|----|---------|-------|--------|-----------|
| F-101 | Slide image extraction (PNG, 150 DPI) | Critical | 1 week | Core pipeline. POC validated. Needs hardening. |
| F-102 | Verbatim text extraction (MarkItDown) | Critical | 1 week | Core pipeline. Special chars, tables need testing. |
| F-103 | LLM slide analysis (framework detection) | Critical | 1.5 weeks | Prompt engineering + caching. POC validated approach. |
| F-104 | Source file tracking (relative paths, hash) | Critical | 0.5 weeks | Straightforward. Path computation + SHA256. |
| F-105 | Markdown assembly with frontmatter | Critical | 0.5 weeks | Template-driven. Include new schema fields from day one. |
| F-106 | Change detection (text diff per slide) | Critical | 1 week | Text cache comparison. Slide reorder is the hard case. |
| F-107 | Version history (version_history.json) | Critical | 0.5 weeks | JSON read/write with atomic writes. |
| F-108 | Staleness detection (hash comparison) | Critical | 0.5 weeks | Simple hash check. Needs `status` command to surface it. |
| **F-109** | **Authority tier in frontmatter** | **High** | **0 weeks** | **Free. Just a YAML field. Bake into schema now, assign manually.** |
| **F-110** | **Curation level (L0-L3) in frontmatter** | **High** | **0 weeks** | **Free. Default to L0 on convert. Human promotes later.** |
| **F-111** | **Ontology-aligned type/subtype fields** | **High** | **0 weeks** | **Free. Classify during convert (evidence/deck for PPTX). Aligns to dual ontology.** |
| **F-112** | **Date-based ID convention** | **High** | **0.5 weeks** | **Auto-generate IDs in CLI. Convention: `{client}_{engagement}_{type}_{date}_{descriptor}`. Define once, enforce everywhere.** |
| **F-113** | **Unified tags field (merged tags+concepts)** | **High** | **0 weeks** | **Free. Single field with soft vocabulary validation at tool level.** |
| **F-114** | **Engagement field (required at L1+ for scoped types)** | **High** | **0 weeks** | **Free. Schema decision. Required for analysis, evidence, deliverable, interaction. Optional for context, N/A for reference.** |

**Tier 1 total: ~7 weeks** (added 0.5 weeks for ID convention implementation)  
**Exit criteria:** Convert 50 real decks with zero silent failures. Every output has image, text, analysis, and the full ontology-aware frontmatter schema.

---

## Tier 2: Daily Driver (Build When Using Tier 1 Daily)

CLI, multi-project organization, and Obsidian compatibility. This is what makes Folio usable as a tool rather than a script.

| ID | Feature | Value | Effort | Rationale |
|----|---------|-------|--------|-----------|
| F-201 | `folio convert` CLI command | High | 1 week | Click CLI. Single file conversion with --note flag. |
| F-202 | `folio batch` CLI command | High | 0.5 weeks | Wraps convert with progress, error-per-file handling. |
| F-203 | `folio status` CLI command | High | 1 week | Registry query + staleness check. Scoping by client/project. |
| F-204 | `folio scan` (find new/changed sources) | Medium | 0.5 weeks | Walk source dirs, compare against registry. |
| F-205 | `folio refresh` (re-convert stale) | Medium | 0.5 weeks | Batch re-convert filtered by staleness. |
| F-206 | `folio.yaml` configuration | High | 0.5 weeks | Source roots, LLM settings, library root. |
| F-207 | Multi-client directory structure | High | 0.5 weeks | Client/Project/Deck hierarchy with Internal + Research. |
| F-208 | Registry (registry.json) | Medium | 1 week | Global index. CRUD operations. Fast status queries. |
| F-209 | Obsidian frontmatter completeness | High | 0.5 weeks | Tags, frameworks, slide types. Dataview-queryable. |
| F-210 | Python package (pip installable) | Medium | 0.5 weeks | pyproject.toml, entry points, proper imports. |
| **F-211** | **`folio promote` command** | **Medium** | **0.5 weeks** | **Update curation level. Simple frontmatter edit.** |

**Tier 2 total: ~7 weeks**  
**Exit criteria:** Johnny uses Folio daily on an active engagement. CLI handles full workflow. Library opens cleanly in Obsidian.

---

## Tier 3: Engagement Intelligence (Partly Shipped, Continue During Engagement)

This is where the February brainstorm features land. They require Tier 1+2 to be live and generating real content.

| ID | Feature | Value | Effort | Risk | Rationale |
|----|---------|-------|--------|------|-----------|
| F-301 | `folio ingest` (transcript/notes to interaction MD) | **Very High** | 2 weeks | Low | **Shipped on `main` (PR #32).** Converts transcript/notes sources into ontology-native interaction notes with re-ingest identity and degraded-output handling. |
| F-302 | Interaction subtypes (client_meeting, expert_interview, etc.) | High | 0.5 weeks | Low | **Shipped on `main` (PR #32).** Subtype-specific interaction analysis and output shapes now exist in the baseline. |
| F-303 | Ingest-time entity extraction and canonical wikilinks | High | 1.5 weeks | Medium | **Shipped on `main` (PR #35).** v1 supports exact/alias resolution, bounded LLM soft-match proposals, and unresolved-entity follow-up; broader production-scale entity backfill remains open. |
| F-304 | Entity registry and review workflow | High | 2 weeks | Medium | **Shipped on `main` (PR #34/#35).** `entities.json`, `folio entities`, CSV import, confirmation/rejection flow, and ingest-time registry use are in the current baseline. |
| F-305 | `folio enrich` (LLM enrichment pass) | High | 1.5 weeks | Medium | Post-hoc tagging, linking, entity extraction. Generates wikilink "Related" section from frontmatter. Detects manual wikilinks and offers to promote to frontmatter. |
| F-306 | Retroactive provenance linking | Medium | 1 week | Medium | During enrich, match deliverable claims against library evidence. Human confirms. |
| F-307 | Relationship types (depends_on, draws_from, impacts) | Medium | 1 week | Low | Frontmatter is source of truth. Wikilinks derived. Start with 3 types per recommendation. |
| F-308 | Context documents (engagement scaffolding) | Medium | 0.5 weeks | Low | Template for client/engagement/SOW context. Single source of engagement metadata. |

**Tier 3 remaining planned work: ~4 weeks**
**Exit criteria:** Full engagement lifecycle captured in Folio. Meetings ingested with one command. Entities linked across documents.

---

## Tier 4: Synthesis & Discovery (Build When Library Has 3+ Months of Content)

These features need volume to be useful. Building them before the library has depth is premature.

PRD crosswalk:
- F-401 / F-402 → FR-801 / FR-802
- F-403 / F-404 → FR-803
- F-405 → FR-804
- F-406 → FR-805
- F-407 → FR-806
- F-408 → FR-808
- F-409 → FR-809
- F-410 → FR-807
- F-411 → FR-810
- F-412 → FR-811
- F-413 → FR-812
- F-415 → FR-813

| ID | Feature | Value | Effort | Risk | Rationale |
|----|---------|-------|--------|------|-----------|
| F-401 | Daily digest (`folio digest`) | High | 1.5 weeks | Low | Aggregate day's new/modified content. Different analytical altitude than source notes. |
| F-402 | Weekly digest (`folio digest --week`) | High | 1 week | Low | Roll up daily digests. SteerCo prep input. |
| F-411 | `folio enrich diagnose` | Medium | 0.5 weeks | Low | Makes body-coverage blockers visible before graph-density work stalls silently. |
| F-412 | Trust-aware graph behavior | High | 1 week | Medium | Keeps digest, synthesize, traversal, and search from silently excluding or compounding flagged inputs. |
| F-413 | Relation-schema validation | High | 1 week | Medium | Enforces ontology quality for canonical relationships instead of trusting ad hoc writes. |
| F-403 | Wiki links between related decks | Medium | 1.5 weeks | Low | Same-project, same-framework auto-linking. |
| F-404 | Maps of Content (framework/client index pages) | Medium | 1 week | Low | Auto-generated index pages. Updated on conversion. |
| F-405 | `folio synthesize` (cross-asset synthesis) | High | 2 weeks | High | Interview synthesis across multiple interactions. Needs careful prompt design. |
| F-415 | Proposal review hardening | High | 1 week | Medium | Hardens the shared review contract with stable fingerprints, bounded queue volume, trust rendering, and rejection memory for producers already in play. |
| F-406 | Org traversal queries | Medium | 3 weeks | **High** | The Tier 3 entity import baseline is already shipped. The remaining work is recursive traversal, which exceeds Dataview capabilities and may need a custom query engine or graph DB. |
| F-407 | Semantic search (`folio search`) | High | 3 weeks | **High** | Embedding model selection, index storage, query interface. Significant architectural decision. |
| F-408 | Graph view optimization | Low | 2 weeks | Medium | Obsidian graph tuning. Subjective value. |
| F-409 | File watcher for auto-digest | Low | 1 week | Low | Quality of life. Manual trigger sufficient for v1. |
| F-410 | `folio vocab` (tag vocabulary) | Low | 1 week | Low | Controlled vocabulary for the unified `tags` field. Nice for consistency, not blocking. |

**Tier 4 total: ~21 weeks**
**Exit criteria:** Library reveals patterns across engagements. Synthesis features save prep time.

### Tier 4 validation workstream (not yet committed product features)

This workstream is attached to F-415 and exists to validate proposal review
quality before broader automation or discovery investment:

- document relationship proposals
- entity merge proposals
- diagram archetype clustering

Promotion gates:
- top-10 document-relationship proposal acceptance rate is at least 60%
- entity-merge suggestion acceptance rate is at least 75%, with post-accept
  undo or reopen rate at most 10%
- exact rejected-suggestion resurfacing without material input change stays at
  or below 5%
- median review decision time for top-ranked proposals is at most 30 seconds
- at least 60% of reviewed top-10 diagram archetype clusters are judged useful
  for navigation or triage
- no canonical auto-promotion is introduced

---

## The "Not Yet" List

Features identified but explicitly deferred. Not on any roadmap until a real need forces the question.

| Feature | Why Deferred |
|---------|-------------|
| OneNote → Markdown pathway | Research needed on export mechanism. Copy-paste may be sufficient for v1 of ingest. |
| Audio file ingestion (direct) | Depends on transcription service selection. Transcript → ingest is the v1 path. |
| Cross-engagement pattern detection | Keep out of the committed Tier 4 set until digest, synthesize, and search prove a real multi-engagement need. |
| Multi-user collaboration | Personal tool. No collaboration requirement. |
| Real-time sync | Obsidian + OneDrive handles this passively. |
| Custom graph DB migration | Obsidian + Dataview covers 80% of queries. Revisit when queries demonstrably exceed its capability. |
| Full diagram parsing | Keep out of the committed Tier 4 set until archetype clustering proves useful on real consulting artifacts. |

---

## Effort vs. Value Plot

```
                        HIGH VALUE
                            │
          F-301 (ingest)    │    F-101-108 (core pipeline)
          F-401/402 (digest)│    F-109-111 (schema fields)
          F-303/304 (entity)│    F-201-210 (CLI + org)
                            │
     LOW EFFORT ────────────┼──────────── HIGH EFFORT
                            │
          F-410 (vocab)     │    F-406 (org traversal)
          F-409 (watcher)   │    F-407 (semantic search)
          F-408 (graph opt) │
                            │
                        LOW VALUE
```

**Top-right (high value, high effort):** Core pipeline. No shortcut. Do it right.  
**Top-left (high value, low effort):** Ingest, digest, schema fields, graph quality controls, and proposal review hardening. Best ROI after foundation ships.
**Bottom-right (low value, high effort):** Org traversal, semantic search. Don't touch until real queries demand it.  
**Bottom-left (low value, low effort):** Nice-to-haves. Build when bored.

---

## Key Dependencies

```
F-101 through F-108 (core pipeline)
    └── F-201 through F-210 (CLI + organization)
        ├── F-301 (ingest) ← requires working library structure
        │   ├── F-303/304 (entity extraction) ← requires ingest producing content
        │   └── F-401/402 (digest) ← requires daily content flow
        ├── F-305 (enrich) ← requires library with content to enrich
        │   ├── F-306 (provenance) ← requires enrich infrastructure
        │   └── F-411 (enrich diagnose) ← requires enrich protection rules
        └── F-403/404 (wiki links, MOCs) ← requires multi-deck library
            ├── F-412 (trust-aware graph behavior) ← requires shipped review/trust metadata
            ├── F-413 (relation-schema validation) ← requires shared graph surfaces
            ├── F-405 (`folio synthesize`) ← requires digest and shared review surfaces
            ├── F-415 (proposal review hardening) ← requires producers already in play and review surfaces
            └── F-407 (semantic search) ← requires substantial content volume
```

---

## Risk Flags

| Feature | Risk | Mitigation |
|---------|------|------------|
| F-304 Entity registry | Name resolution beyond v1 is genuinely hard ("Jane" vs "Jane Smith" vs "the CTO") | v1 shipped with exact match, alias match, bounded LLM soft match, and human confirmation. Do not add an algorithmic fuzzy matcher until production-scale evidence justifies it. |
| F-406 Org traversal | Dataview can't do recursive queries. This is a different product. | Build flat entity queries first (F-303). Only invest in traversal if Johnny actually needs it on a real engagement. |
| F-407 Semantic search | Embedding model + vector store is a significant architectural commitment | Obsidian's built-in search + Dataview covers most cases. Defer until search is demonstrably insufficient. |
| F-405 Cross-asset synthesis | LLM synthesis quality across many documents is unpredictable | Start with pairwise comparison (2 interviews), not N-way synthesis. Build up. |
| F-415 Proposal review hardening | Review queues can swamp operators with plausible but low-value suggestions | Keep proposal objects non-canonical, cap default surfacing volume, and require measured acceptance quality before expanding proposal volume. |
