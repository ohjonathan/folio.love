---
id: doc_01_vision_document
type: atom
status: scaffold
ontos_schema: 2.2
curation_level: 0
generated_by: ontos_scaffold
---

# Folio: Vision Document

**Version 1.0 | January 2026**  
**folio.love**

---

## Executive Summary

Folio is a knowledge management system that transforms consulting materials into an AI-native, searchable library spanning your entire career. It converts PowerPoint and PDF files into Markdown while preserving what matters: exact wording for editorial review, visual layouts that carry meaning, and the path back to original files.

The core insight: consulting materials are trapped in binary formats that AI can't process, humans can't search, and version control can't track. Folio liberates this content while preserving fidelity—then organizes it into a career-spanning knowledge base you can search, browse, and use with AI assistants.

### Core Value Proposition

**Conversion Quality First:**
- Verbatim text extraction for editorial review and grammar checking
- Slide images preserving visual frameworks and spatial relationships
- LLM analysis explaining what humans see but text extraction misses
- Source tracking so you can always get back to the original

**Knowledge Library at Scale:**
- Multi-client, multi-project organization
- Version tracking with automatic change detection
- Semantic search across your entire consulting history
- Obsidian-compatible for visualization and linking

---

## The Hierarchy of Value

Not all features are equal. Folio must excel at the fundamentals before anything else matters:

```
1. CONVERSION QUALITY         ← if this fails, nothing else matters
   └── Verbatim text
   └── Slide images  
   └── LLM analysis
   └── Source tracking

2. VERSION INTEGRITY          ← if this fails, you can't trust the library
   └── Change detection
   └── History tracking
   └── Staleness warnings

3. ORGANIZATION               ← makes it usable at scale
   └── Folder structure
   └── Metadata/frontmatter
   └── Basic search

4. KNOWLEDGE GRAPH            ← amplifies value of the above
   └── Cross-references
   └── Framework indexes
   └── Obsidian integration
```

Each level depends on the ones below it. A beautiful knowledge graph built on poor conversions is worthless.

---

## Problem Statement

### The Format Prison

Consulting deliverables are trapped in formats hostile to modern AI workflows:

| Format | Human Readable | AI Readable | Version Controllable | Searchable |
|--------|---------------|-------------|---------------------|------------|
| PPTX | ✓ | ✗ | ✗ | Limited |
| PDF | ✓ | Partial | ✗ | Limited |
| Markdown | ✓ | ✓ | ✓ | ✓ |

PowerPoint is particularly problematic because **visual structure carries meaning**. A 2x2 matrix isn't just four boxes of text—the axes, positions, and spatial relationships communicate strategic insights that disappear in text extraction.

### What Gets Lost Today

**Without slide images:**
- Framework structures (which quadrant is which?)
- Color coding and visual emphasis
- Charts and data visualizations
- Spatial relationships that communicate priority or flow

**Without verbatim text:**
- Exact wording needed for editorial review
- Ability to check grammar and tone
- Consistency tracking across versions
- Legal/compliance precision

**Without source tracking:**
- No way back to edit the original
- Can't share the "real" file with clients
- Uncertainty about which version you're looking at
- Duplicated files across systems

### The Bigger Problem: Knowledge Fragmentation

Beyond individual documents, consultants accumulate years of materials across:
- Multiple clients
- Multiple projects per client
- Internal training and templates
- Industry research

This knowledge is scattered, unsearchable, and effectively lost. The 2x2 matrix you built for Client A in 2023 could inform Client B in 2026, but you'll never find it.

---

## Vision Statement

Folio is your professional portfolio, searchable and AI-ready. Every deck you convert becomes a permanent, queryable part of your career knowledge base—without sacrificing the fidelity needed for real consulting work.

### Design Principles

**1. Fidelity is Non-Negotiable**

Raw text is preserved exactly as written. Slide images show exactly what the deck shows. Source files are always accessible. No summarization or "cleaning" that loses precision.

**2. Dual-Layer Representation**

Every slide exists as:
- Visual layer (PNG image) for human review
- Text layer (verbatim + analysis) for AI processing

Neither replaces the other. Both are essential.

**3. Source is Sacred**

The original file is the source of truth. Folio produces derived artifacts. The path back to the original is always clear, and staleness is always detectable.

**4. Git-Native Architecture**

Markdown and JSON are text formats that version control understands. Changes are visible in diffs. History is preserved automatically.

**5. Obsidian-Compatible**

Output is valid Obsidian markdown with frontmatter. The knowledge library can be opened as an Obsidian vault for visualization, linking, and graph exploration.

---

## Target Users

### Primary: Engagement Managers

Mid-level consultants who own document quality and spend significant time on revision cycles. They need:
- Editorial precision (exact wording matters)
- Visual reference (frameworks must be visible)
- Version tracking (what changed and why)
- Historical search (what did we do before?)

### Use Cases

**Daily workflow:**
- Convert updated deck, see what changed
- Review exact wording for grammar/tone
- Reference visual frameworks during discussions
- Ask Claude about deck content with full context

**Project setup:**
- Batch convert all inherited materials
- Build searchable knowledge base for new engagement
- Establish baseline for version tracking

**Career development:**
- Build personal library of frameworks and approaches
- Search across years of work
- Reference past solutions for new problems

---

## Success Criteria

### Conversion Quality (P0)

| Metric | Target |
|--------|--------|
| Text accuracy | 99%+ character accuracy vs. source |
| Image presence | 100% of slides have visible images |
| LLM analysis | Every slide has framework/type/insight analysis |
| Source tracking | 100% of conversions have valid source path |
| Round-trip time | Original file opens within 2 clicks |

### Version Integrity (P0)

| Metric | Target |
|--------|--------|
| Change detection | 95%+ of modified slides correctly identified |
| Staleness detection | 100% of outdated conversions flagged on status check |
| History completeness | Full version history preserved for all decks |

### Usability (P1)

| Metric | Target |
|--------|--------|
| Conversion speed | <60 seconds for typical deck (excluding LLM analysis) |
| Search relevance | 80% of searches return useful results in top 5 |
| Obsidian compatibility | Opens as valid vault with no errors |

---

## Scope

### In Scope (v1.0)

**Core Conversion:**
- PPTX to Markdown with slide images
- PDF to Markdown with page images
- Verbatim text extraction
- LLM analysis for each slide
- Source path and hash tracking

**Version Management:**
- Automatic change detection
- Version history with notes
- Staleness warnings

**Organization:**
- Multi-client, multi-project folder structure
- Obsidian-compatible frontmatter
- Basic CLI (convert, batch, status, scan)

### Out of Scope (v1.0)

- Slide design or layout editing
- Client-facing document generation
- Multi-user collaboration
- Real-time sync
- Auto-generated MOCs and cross-references (Phase 2)
- Smart graph optimization (Phase 3)

---

## Strategic Context

### Why Now

**LLM Capabilities:** Current models reliably analyze visual content and understand consulting frameworks. The technical foundation works—we validated this in POC.

**Obsidian Maturity:** Obsidian has become the standard for personal knowledge management. Designing for it means tapping into a mature ecosystem.

**Personal Tooling Window:** Before firm-wide adoption of AI tools, individual practitioners can build and validate workflows. Folio is a personal productivity multiplier.

### The Name

**Folio** — a collection of papers, a portfolio of work. Simple, literal, professional. Your consulting folio, now searchable and AI-ready.

### The Bigger Picture

Folio is one component of a broader vision for agentic AI in consulting workflows. It solves the "materials" problem—getting documents into a format where AI can help. Future tools might address:
- Automated revision suggestions
- Cross-project insight synthesis
- Client communication drafting
- Model documentation

But all of that depends on having a quality knowledge base. Folio builds the foundation.
