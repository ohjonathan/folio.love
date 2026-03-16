---
title: "Deep Research: Architecture Diagram Extraction from PDF"
type: prompt
target: deep-research-tool
status: ready
created: 2026-03-14
context: >
  folio.love diagram ingestion exploration. Two known gaps: blank detection
  false positives on simple diagrams, text-in-shapes lost by pdfplumber.
  Preliminary research shows vision LLMs are the only viable path for
  semantic diagram understanding. Run this prompt through Claude deep research,
  Gemini Deep Research, or similar, then bring results to LLM review board.
---

# Deep Research: Architecture Diagram Extraction from PDF for Knowledge Management

## Background

I'm building folio.love, a Python-based knowledge management system for consulting. It converts PPTX and PDF files into searchable Markdown documents stored in an Obsidian vault. The system has a working pipeline:

- **Image extraction:** pdf2image converts each PDF page to PNG at 150 DPI
- **Text extraction:** pdfplumber extracts text per page
- **LLM analysis:** Multimodal LLMs (Claude, GPT-4, Gemini) analyze page images and produce structured JSON (slide_type, frameworks, visual_description, key_data, insights)
- **Output:** Markdown with YAML frontmatter, inline images, verbatim text, and LLM analysis sections

I now need to ingest **standalone PDF files containing architecture diagrams** — system architecture, flowcharts, data flow diagrams, org charts, network topologies, and similar technical diagrams. These PDFs are a mix of:
- Simple line/box diagrams (boxes with text labels connected by arrows on white backgrounds)
- Dense, colorful diagrams (filled shapes, color coding, complex layouts)
- Multi-page documents where some pages are diagrams and others are text

## Current Gaps

1. **Text inside diagram shapes is lost.** pdfplumber's `page.extract_text()` only captures flowing text, not text rendered inside rectangles, circles, or along paths. For architecture diagrams, this means component names, labels, and annotations are missing from the searchable text.

2. **Simple diagrams are misclassified as blank pages.** A histogram-based blank detection (>95% white pixels) falsely flags line-based diagrams, and their LLM analysis gets overwritten.

## Research Questions

### 1. Text Extraction from Diagram Shapes in PDFs

**Investigate thoroughly:**

a) **pdfplumber advanced features:** Can `.extract_words()` with coordinate data + `.rects` (rectangle enumeration) + `.crop(bbox)` reliably extract text from inside diagram boxes? What are the edge cases (rotated text, text on paths, overlapping shapes)? Provide concrete Python code examples showing this approach on architecture diagrams.

b) **PyMuPDF (fitz):** How does `page.get_drawings()` + `page.get_text("dict")` compare to pdfplumber for diagram text extraction? What does `cluster_drawings()` actually do and how reliable is it? Note: AGPL license is a concern — are there MIT/Apache alternatives with similar capability?

c) **OCR approaches:** Compare Tesseract, EasyOCR, PaddleOCR, and PaddleOCR-VL 1.5 for extracting text from diagram images. Which handles:
   - Small text labels inside boxes
   - Rotated/angled text on arrows
   - Mixed text sizes (titles vs annotations)
   - Text overlapping with diagram lines
   Provide benchmark data if available.

d) **Hybrid approach:** Is there a reliable strategy that tries vector-based extraction first (pdfplumber/PyMuPDF), then falls back to OCR only for pages where vector extraction yields insufficient text? How do you detect "insufficient"?

### 2. Diagram Detection and Classification

**Investigate thoroughly:**

a) **How can we automatically distinguish diagram pages from text pages in a PDF?** Compare approaches:
   - Heuristic: ratio of vector graphics to text objects on a page
   - ML-based: DocLayout-YOLO, Detectron2 with PubLayNet/DocLayNet weights
   - Docling's built-in classification (chart/diagram/logo/picture)
   - pdfplumber metadata (number of rects, lines, curves vs text chars)

b) **Docling (IBM):** Deep dive on its diagram handling:
   - What exactly does it classify as "diagram" vs "chart" vs "picture"?
   - What structured output does it produce for diagram regions?
   - Can it be used as a classifier only (detect diagram pages) while using folio's own LLM pipeline for understanding?
   - Performance and dependency footprint (does it require GPU? How heavy?)
   - MIT license — any restrictions?

c) **Can pdfplumber alone detect diagram pages?** A page with many `.rects`, `.lines`, `.curves` but little `.extract_text()` output is likely a diagram. How reliable is this heuristic?

### 3. Diagram Understanding via Vision LLMs

**Investigate thoroughly:**

a) **Structured output approaches:** Compare:
   - Claude `tool_use` / `output_config.format` with JSON schema
   - OpenAI function calling with vision
   - Instructor library (Pydantic validation + auto-retry)
   - What JSON schema works best for representing diagram components? Research existing schemas for graph/diagram representation.

b) **Prompt engineering for diagram extraction:** What are the best practices for prompting multimodal LLMs to:
   - Identify all components (boxes, nodes, services, databases, etc.)
   - Identify all connections (arrows, lines) with direction and labels
   - Capture hierarchical groupings (containers, zones, layers)
   - Detect diagram type (flowchart, architecture, sequence, ER, network)
   - Handle multi-diagram pages
   Provide example prompts that have been validated to work well.

c) **Mermaid/PlantUML generation:** How reliably can current vision LLMs convert a diagram image to Mermaid syntax? What diagram types work well vs poorly? Any research or benchmarks on this? What about generating multiple representations (Mermaid + structured JSON + natural language description)?

d) **Accuracy and hallucination risks:** What are the known failure modes when LLMs analyze diagrams?
   - Hallucinating connections that don't exist
   - Missing elements in dense diagrams
   - Misinterpreting arrow direction
   - Confusing visual groupings
   How can these be mitigated (multi-pass, validation, confidence scoring)?

### 4. Output Format Analysis

**For each format, analyze suitability for a knowledge management system:**

a) **Searchable Markdown text:** Extract all component names, labels, relationships into prose/structured markdown sections. Pros: fully searchable in Obsidian, works with existing pipeline. Cons: loses spatial/visual structure.

b) **Mermaid diagram-as-code:** Re-render diagrams as Mermaid blocks in markdown. Pros: re-renderable in Obsidian (native Mermaid support), version-diffable, modifiable. Cons: lossy conversion, complex diagrams may not translate, Mermaid syntax limitations.

c) **Structured JSON:** `{nodes: [{id, label, type, properties}], edges: [{source, target, label, direction}], groups: [{id, label, children}]}`. Pros: machine-queryable, can power graph views, relationship extraction for knowledge graph. Cons: not human-readable in vault, needs rendering layer.

d) **Hybrid approach:** Generate all three — markdown for reading/search, Mermaid for visual rendering, JSON for querying. Is this practical? What's the cost (LLM tokens, processing time)?

e) **How do each of these integrate with Obsidian's features?** Dataview queries, graph view, search, backlinks. Which format maximizes Obsidian's capabilities?

### 5. Integration Architecture

**Given folio.love's existing pipeline (normalize → images → text → analysis → converter → frontmatter → markdown):**

a) Where should diagram handling be injected? Options:
   - New step between images and text (diagram detection + routing)
   - Enhancement to existing text.py (better extraction for diagram pages)
   - Enhancement to existing analysis.py (diagram-specific LLM prompts)
   - New parallel path for diagram-type PDFs
   - Post-processing step that enriches existing output

b) Should diagram PDFs go through the same pipeline as slide decks, or have a dedicated path? What are the tradeoffs?

c) How should diagram output be structured in the final Markdown document? Propose a template that includes: original image, extracted text, LLM-generated description, Mermaid code (if applicable), component/relationship listing.

### 6. Competitive Landscape

a) How do other knowledge management / PKM tools handle diagrams?
   - Notion AI
   - Capacities
   - Mem.ai
   - Reflect
   - Any Obsidian plugins for diagram extraction

b) Any commercial APIs specifically for diagram understanding?
   - Google Document AI
   - Azure Document Intelligence
   - Amazon Textract
   - Any startups in this space?

c) Are there any open-source projects that have solved this problem end-to-end (PDF diagram → structured output)?

## Deliverable

Produce a structured report with:
1. **Executive summary** — What's the state of the art? What's possible today vs what requires compromise?
2. **Recommended approach** for folio.love — with justification
3. **Tool comparison matrix** — feature/capability comparison across all tools investigated
4. **Implementation sketch** — high-level architecture showing how diagram extraction fits into folio's pipeline
5. **Risk register** — what can go wrong and how to mitigate
6. **Sample outputs** — show what extracted diagram data would look like in each output format
7. **Cost analysis** — LLM token costs, processing time estimates, dependency footprint
