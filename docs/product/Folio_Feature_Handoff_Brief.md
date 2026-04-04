---
id: folio_feature_handoff_brief
type: product
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio Feature & Architecture Handoff Brief

**Date:** 2026-02-20
**Source:** Feature brainstorming session during active McKinsey engagement
**Context:** Johnny is mid-engagement and identifying features from real workflow pain points.
**Purpose:** Feed into the master Folio development session. Everything here is a decision or design direction, not exploratory.

---

## 1. Architectural Decision: Dual Ontology (Confirmed)

Folio adopts a Space + Time dual ontology, adapted from Johnny's Project Ontos system (see: `Folio_Ontology_Architecture.md` for full spec).

**Space (Knowledge Graph)** — What we know. Five document types:
- **Context** — Engagement scaffolding (client, SOW, team, industry)
- **Analysis** — Thinking work (hypotheses, issue trees, synthesis, framework applications)
- **Evidence** — What we found (converted decks, data, research, external reports)
- **Deliverable** — What we said (decks, memos, models, recommendations)
- **Reference** — Reusable firm knowledge (templates, methodologies, playbooks)

**Time (Interaction History)** — What happened. One document type:
- **Interaction** — Meetings, interviews, calls, workshops. Immutable once created.

**Bridge mechanism:** Interactions `impacts` Space documents. "This interview changed our hypothesis."

**Key departure from Ontos:** Folio rejects Ontos's "Deterministic Purity" principle. Folio uses structure (tags, links, Dataview) AND semantic search. Structure for navigation, search for discovery.

---

## 2. New Feature: Interaction Ingestion Pipeline

**Problem:** Johnny currently takes meeting notes in OneNote, records audio, transcribes, then manually asks ChatGPT to summarize. Five manual steps per meeting.

**Solution:** `folio ingest` command.

```bash
folio ingest <transcript_or_notes> --type <interaction_subtype> [--client X] [--notes raw_notes.md]
folio ingest <audio_file> --type <interaction_subtype> [--client X]
```

**Interaction subtypes:** `client_meeting`, `expert_interview`, `internal_sync`, `partner_check_in`, `workshop`

**Every interaction produces three outputs automatically:**
1. **Summary** — Narrative of what happened and key takeaways
2. **Extracted entities** — People, departments, systems, processes → auto-linked as wikilinks
3. **Structured insights** — Claims (with attribution), data points, decisions, contradictions, open questions

**Output lands as L0.** Human adds engagement context to promote to L1. Claude enrichment adds cross-asset links for L2.

---

## 3. New Feature: Temporal Roll-Up Pipeline

**Problem:** Johnny needs daily and weekly synthesis to feed into steerco prep. Currently rebuilt manually each week.

**Solution:** Automated roll-up hierarchy: Note → Day → Week → Steerco

```bash
folio digest <scope> [--date YYYY-MM-DD]          # Generate daily digest for one engagement scope
folio digest <scope> --week [--date YYYY-MM-DD]   # Generate weekly digest from that scope's daily digests
```

**Critical design principle:** Each level is a different analytical altitude, not just compression:
- **Note-level summary:** "What was said"
- **Daily digest:** "What moved forward today"
- **Weekly digest:** "Where do we stand and what's changed"
- **Steerco input:** "What does leadership need to decide"

Should start as a single end-of-day command. File-watcher automation is a
later quality-of-life extension, not the v1 default.

---

## 4. New Feature: Entity Extraction & People Graph

**Problem:** Across 30+ interviews, people reference other people, departments, and systems. These connections are lost in flat notes. Johnny wants to query: "Show me all interviews with anyone reporting to the CFO, two levels deep."

**Solution:** Entities as first-class graph nodes.

**Person nodes** — Lightweight markdown files (or registry entries) with properties:
- `name`, `title`, `department`, `reports_to` (→ another person node)
- Created automatically during interview summarization, resolved against a registry

**Org chart import baseline** — Import org structure (CSV or manual build) to
establish `reports_to` hierarchy. Tier 3 ships the import baseline; the
remaining Tier 4 work is traversal-oriented querying over that hierarchy.

**Entity extraction during ingest** — The LLM summarization step doesn't just summarize. It:
- Identifies all people mentioned
- Resolves names against entity registry ("Jane," "Jane Smith," "the CTO" → `[[Jane Smith]]`)
- Extracts departments, systems, processes as additional entity types
- Creates wikilinks and frontmatter entries automatically

**Query patterns this enables:**
- All interviews with Engineering department (flat filter)
- All interviews with anyone reporting to Jane, N levels deep (org traversal)
- What did Operations people say about the ERP migration? (entity + semantic search)
- Who contradicted whom across interviews? (cross-interview entity comparison)

**Name resolution challenge:** People get referred to inconsistently. Folio needs an entity registry that the LLM checks against during extraction. Soft-match with human confirmation for ambiguous cases.

**Extends beyond people:** Departments, systems (ERP, CRM), processes, locations — any entity that appears across multiple documents and connects them.

---

## 5. New Feature: Authority Tiers

**Problem:** Not all knowledge is equal. A raw interview note shouldn't carry the same weight as a client-aligned steerco deck when an AI assistant is resolving conflicting information.

**Solution:** Authority tiers (orthogonal to curation levels L0-L3):

| Tier | Name | Meaning | Example |
|------|------|---------|---------|
| T1 | **Captured** | One person said it | Interview note, raw meeting note |
| T2 | **Analyzed** | Team processed it | Synthesis doc, hypothesis tracker |
| T3 | **Aligned** | Team + client agreed | Steerco deck, approved recommendation |
| T4 | **Decided** | Formally signed off | Final deliverable, board presentation |

**Curation level ≠ Authority.** A perfectly curated (L3) interview note is still T1. A rough (L1) steerco deck is T3. Authority is about epistemic weight, not document completeness.

**Use case:** When an AI assistant is drafting a slide and finds conflicting information in the library, authority tier tells it which source wins.

New frontmatter field:
```yaml
authority: aligned  # captured | analyzed | aligned | decided
```

---

## 6. New Feature: Retroactive Provenance Linking

**Problem:** In reality, deliverables often get made fast, outside Folio. The PowerPoint comes first, the library connection comes later. Other team members may not use or know about Folio.

**Solution:** Backward provenance inference during `folio enrich`.

When a deliverable is converted and enriched, the LLM reads the slide content, matches claims/data against existing library assets, and proposes provenance links:
- "Slide 7 appears to draw from [[retail_market_sizing_2025]]"
- "The 18-month timeline claim matches [[clienta_dd_expert_interview_01]]"

Human confirms or corrects proposed links. This means even messy, fast-produced deliverables can get retroactively connected to the clean library.

**Design principle:** The library is the source of truth, deliverables are downstream expressions. Even when reality forces deliverable-first workflow, Folio provides eventual consistency through retroactive linking.

---

## 7. Progressive Formalization (Updated)

Extended from Ontos's L0-L2 to L0-L3:

| Level | Name | How It Gets Here | What's Required |
|-------|------|-------------------|-----------------|
| **L0** | Raw | Auto-generated by `folio convert` or `folio ingest` | `id`, `type`, auto-extracted metadata |
| **L1** | Contextualized | Human adds engagement context | `client`, `engagement`, basic `tags` |
| **L2** | Connected | Claude enrichment or manual curation | Full tags, relationship links, curated connections |
| **L3** | Synthesized | Human review + cross-asset linking | Part of synthesis docs, hypothesis chains, verified provenance |

---

## 8. Updated CLI Commands (Complete)

### Core Pipeline
```bash
folio convert <file>              # Convert deck/PDF to evidence markdown
folio batch <dir>                 # Batch convert
folio ingest <file>               # Ingest transcript/notes/audio as interaction
```

### Library Management
```bash
folio status [scope]              # Check library status
folio scan                        # Find new/changed sources
folio refresh                     # Re-convert stale decks
folio promote <id> <level>        # Promote curation level
```

### Intelligence Layer
```bash
folio enrich [scope]              # LLM enrichment: tags, links, entity extraction
folio digest <scope> [--date] [--week]    # Generate daily/weekly roll-up summaries
folio synthesize <doc_a> <doc_b> [options]        # Cross-asset synthesis (e.g., interview synthesis)
folio search <query>              # Semantic search across library
```

### Graph & Vocabulary
```bash
folio link <id> <id> [type]       # Manually create relationship
folio vocab                       # View/manage tag vocabulary
folio entities                    # View/manage entity registry (people, depts, systems)
folio entities import <csv>       # Import org chart
```

---

## 9. Relationship Types (Complete)

### Space → Space (Structural)
- `depends_on` — Cannot exist without this context
- `draws_from` — Uses as input or evidence
- `relates_to` — Topically connected, no dependency
- `supersedes` — Replaces a previous version
- `instantiates` — Applies a reference template

### Time → Space (Temporal Bridge)
- `impacts` — This interaction changed this document

### v1 recommendation: Start with `depends_on`, `draws_from`, and `impacts`. Add others when the need arises.

---

## 10. Companion Document

The full ontology specification with type definitions, frontmatter schemas,
example YAML for every type, tag vocabulary, and query patterns is in:

**`Folio_Ontology_Architecture.md`** (attached separately)

---

## 11. Open Design Questions

These were identified but not resolved in this session:

1. **Semantic search architecture** — Embedding model, index storage, query interface, integration with Dataview. Not yet specced.
2. **Entity resolution specifics** — How exactly does the LLM match "Jane," "the CTO," and "Jane Smith" to the same person node? Needs registry design + fuzzy matching approach.
3. **File watcher vs manual trigger** — Should `folio digest` run automatically when files change, or is end-of-day manual trigger sufficient for v1?
4. **Context as standalone type vs metadata** — Engagement context could be a separate document type or just shared frontmatter fields. Current spec has it as standalone (cleaner single source for engagement details), but this needs validation.
5. **Org chart format** — What format can Johnny actually export org charts in? CSV? What fields are available?
6. **OneNote → Markdown pathway** — Specific mechanism for getting OneNote content into Folio. Copy-paste? Export? API? Needs research.

---

*End of handoff brief*
