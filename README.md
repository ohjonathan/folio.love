# Folio

**Your consulting portfolio, searchable and AI-ready.**

**folio.love**

---

## What is Folio?

Folio transforms PowerPoint and PDF files into a searchable, AI-native knowledge library. Every deck you convert becomes a permanent part of your professional portfolio—organized by client and project, tracked through revisions, and ready for AI-assisted workflows.

**Core outputs:**
- **Slide images** — Visual fidelity preserved
- **Verbatim text** — Exact wording for editorial review
- **LLM analysis** — Framework detection, insights extraction
- **Source tracking** — Always find the original file
- **Version history** — Track what changed and when

The result is an Obsidian-compatible vault you can search, browse, and use with AI assistants like Claude.

---

## The Hierarchy of Value

```
1. CONVERSION QUALITY         ← Non-negotiable
   └── Slide images (every slide)
   └── Verbatim text (exact wording)
   └── LLM analysis (frameworks, insights)
   └── Source tracking (path to original)

2. VERSION INTEGRITY          ← Must be trustworthy
   └── Change detection
   └── Staleness warnings
   └── History preservation

3. ORGANIZATION               ← Makes it usable
   └── Client/Project structure
   └── Obsidian compatibility
   └── Search and discovery

4. KNOWLEDGE GRAPH            ← Amplifies value
   └── Cross-references
   └── Framework indexes
   └── Visual exploration
```

**If #1 fails, nothing else matters.**

---

## Documentation

| Document | Purpose |
|----------|---------|
| [Vision Document](01_Vision_Document.md) | Why Folio exists, design principles, success criteria |
| [Product Requirements](02_Product_Requirements_Document.md) | Detailed functional and non-functional requirements |
| [Technical Architecture](03_Technical_Architecture.md) | System design, pipeline stages, data schemas |
| [Implementation Roadmap](04_Implementation_Roadmap.md) | Phased delivery plan, quality gates, timeline |
| [User Stories](05_User_Stories.md) | Stories by epic with acceptance criteria |

---

## Quick Reference

### CLI Commands

```bash
# Convert single file
folio convert ./materials/deck.pptx --note "Initial conversion"

# Batch convert directory
folio batch ./materials --pattern "*.pptx"

# Check library status
folio status
folio status ClientA

# Find new/changed source files
folio scan

# Refresh stale conversions
folio refresh
```

### Library Structure

```
folio_library/
├── folio.yaml               # Configuration
├── registry.json            # Index of all decks
│
├── ClientA/
│   └── Project1/
│       └── market_sizing/
│           ├── market_sizing.md    # Main document
│           ├── slides/             # Slide images
│           │   ├── slide-001.png
│           │   └── ...
│           ├── version_history.json
│           └── .texts_cache.json
│
├── Internal/
│   └── Templates/
│
└── Research/
    └── Industry/
```

### Markdown Output

```markdown
---
title: Market Sizing Analysis
source: ../../../sources/ClientA/Project1/market_sizing.pptx
source_hash: abc123def456
version: 2
converted: 2026-01-10
client: ClientA
project: Project1
frameworks:
  - 2x2-matrix
tags:
  - market-sizing
---

# Market Sizing Analysis

**Source:** `../../../sources/ClientA/Project1/market_sizing.pptx`
**Version:** 2 | **Converted:** 2026-01-10

---

## Slide 1

![Slide 1](slides/slide-001.png)

### Text (Verbatim)

> Executive Summary
> 
> The total addressable market is $2.3B...

### Analysis

**Slide Type:** executive-summary
**Framework:** None
**Key Data:** $2.3B TAM, 12% CAGR
**Main Insight:** Large and growing market opportunity
```

---

## Development Status

### Phase 0: POC ✓
- Conversion pipeline validated
- Version tracking works
- Architecture proven

### Phase 1: Conversion Quality (Current)
- [ ] Bulletproof image extraction
- [ ] Verified text accuracy
- [ ] Source tracking implementation
- [ ] LLM analysis tuning

### Phase 2: Library Organization (Planned)
- CLI implementation
- Multi-project structure
- Obsidian compatibility

### Phase 3: Knowledge Graph (Planned)
- Cross-references
- Index pages
- Graph optimization

---

## Key Decisions

**Why Markdown?**
- Git-friendly (version control, diffs)
- AI-native (LLMs process it well)
- Obsidian-compatible (knowledge graph)
- Human-readable (no special tools needed)

**Why relative source paths?**
- Works across machines (OneDrive sync)
- Portable library structure
- No broken links after moving folders

**Why dual-layer (image + text)?**
- Images preserve visual meaning (frameworks, layout)
- Text enables search and AI processing
- Neither alone is sufficient

**Why Obsidian?**
- Best-in-class personal knowledge management
- Graph visualization built-in
- Markdown-native (no lock-in)
- Active ecosystem

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| CLI | Click |
| Text Extraction | MarkItDown |
| PDF Processing | pdf2image + Poppler |
| Office Conversion | LibreOffice |
| LLM | Anthropic Claude |
| Knowledge Base | Obsidian (viewer) |

---

## The Name

**Folio** — a collection of papers, a portfolio of work. Simple, literal, professional.

Your consulting folio, now searchable and AI-ready.

---

*folio.love*
