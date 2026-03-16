# Diagram Extraction Research Consolidation

**Date:** 2026-03-14
**Purpose:** Consolidated findings from three independent deep research reports on extracting architecture diagrams from PDF into structured knowledge for folio.love. Intended audience: Claude Code session with full codebase context, for implementation planning and feedback.

**Research methodology:** The same research prompt (grounded in a codebase context brief) was run through three different deep research tools. Reports are labeled Model A, Model G, and Model O. They were reviewed blind (without knowing which LLM produced which) and weighted equally. This document synthesizes consensus, disagreements, and standout findings.

---

## Context: What the Pipeline Does Today and Why Diagrams Break

The folio.love pipeline processes PDF pages through: normalize → image extraction (pdf2image, 150 DPI) → blank detection (Pillow histogram) → text extraction (pdfplumber `page.extract_text()`) → LLM analysis (multimodal, base64 PNG + text → JSON) → Markdown output with YAML frontmatter.

Four known problems with diagrams:

1. **Lost text.** `pdfplumber`'s `page.extract_text()` with default parameters does not capture text inside shapes (rectangles, circles, paths). For a diagram with 20 labeled boxes, the extraction may return nothing or only a page title.

2. **False blank detection.** `_is_mostly_blank()` converts to grayscale, counts pixels > 240 brightness, flags as blank if > 95% are near-white. Sparse line-on-white diagrams trigger this. The blank override then replaces the LLM result with `SlideAnalysis.pending()` — the LLM analysis is discarded even if it was correct.

3. **Wrong schema.** `SlideAnalysis` has 7 slide types (title, executive-summary, framework, data, narrative, next-steps, appendix) and 13 framework options, all consulting-deck-oriented. No fields for diagram components, connections, hierarchy, or diagram type.

4. **No diagram-specific prompting.** `ANALYSIS_PROMPT` asks for consulting slide classification. Architecture diagrams don't fit these categories. The `visual_description` free-text field captures some information but it's unstructured and not queryable.

---

## Consensus: Where All Three Reports Agree

These findings are safe to treat as settled. All three reports arrived at the same conclusions independently.

### 1. Mermaid Is the Right Diagram-as-Code Target

All three reports recommend Mermaid and reject all alternatives:

- **Mermaid (MIT):** Native Obsidian rendering without plugins, highest LLM generation quality (most training data), simplest syntax, broadest diagram type coverage (12+ types), token-efficient.
- **PlantUML:** Rejected. GPL license, Java dependency, verbose syntax increases hallucination probability, requires external server or local Java for rendering.
- **D2:** Rejected. Requires Obsidian plugin (violates "no plugins beyond Dataview" constraint), MPL-2.0 license (not MIT/Apache).
- **Structurizr DSL:** Rejected. Too rigid (demands full C4 model definition), high cognitive load for LLMs, only covers C4 diagrams.

**Implementation implication:** Target Mermaid output. Obsidian ships Mermaid v10+, supporting flowcharts, sequence diagrams, class diagrams, ER diagrams, state diagrams, and mind maps. Test which Mermaid diagram types your Obsidian version renders correctly.

### 2. Blank Detection Must Be Fixed Immediately

The current pixel histogram approach is a correctness bug, not a quality issue. It actively destroys valid LLM output. All three reports propose replacing it with PDF object counting via pdfplumber.

**Current behavior (broken):**
```python
# folio/pipeline/images.py lines 184-195
def _is_mostly_blank(image: Image.Image, threshold: float = 0.95) -> bool:
    grayscale = image.convert("L")
    hist = grayscale.histogram()
    total = sum(hist)
    white_count = sum(hist[241:])  # pixels with value > 240
    return (white_count / total) > threshold
```

**Agreed replacement logic:**
A page is blank only when ALL of: (a) no extractable text chars, (b) no embedded images, and (c) near-zero vector objects (rects + lines + curves). If any of these are present, the page is not blank. The pixel histogram should become advisory at most, never a gate that overwrites LLM output.

**How to detect vector objects (all three agree):**
```
vector_count = len(page.rects) + len(page.lines) + len(page.curves)
```
Using pdfplumber, which is already in the dependency stack. This is a free, instant check that requires no image rendering.

**Critical detail from the converter code:** The blank override happens AFTER the LLM runs (converter.py lines 198-201):
```python
for slide_num in blank_slides:
    if slide_num in slide_analyses:
        slide_analyses[slide_num] = analysis.SlideAnalysis.pending()
```
This means even if the LLM correctly analyzed a sparse diagram, the blank check destroys that work. Fixing this is the single highest-value change.

### 3. Render Diagram Pages at 300 DPI

All three reports recommend increasing DPI from 150 to 300 for diagram pages.

**Why 150 DPI is insufficient for diagrams:** An 8pt text label (common in architecture diagrams) at 150 DPI is only ~15-20 pixels tall. After anti-aliasing, characters blur together. The vision LLM can't read the text cleanly and compensates by guessing from context, leading to misreads (e.g., "user_auth_service" → "user_auto_save").

**Why 300 DPI is the sweet spot:** At 300 DPI, the same 8pt label is ~30-40 pixels tall, clearly legible. Going higher (e.g., 600 DPI) wastes CPU and tokens because vision LLMs internally resize to ~1500-2000px on the longest edge anyway. 300 DPI for a letter-size page produces ~2550 × 3300 pixels, which is close to what the LLMs actually process.

**DPI is already configurable** via `ConversionConfig.image_dpi` (config.py lines 141-149). The implementation question is whether to raise the default globally or conditionally for diagram pages only. All three reports prefer conditional upscaling (leave text slides at 150, raise diagrams to 300) to save processing time.

**Model A adds:** Pre-resize the 300 DPI render to ~1568px on the longest edge before sending to the API. This aligns with Claude's documented processing resolution and reduces token cost without losing quality.

### 4. pdfplumber Is Underused — Switch to `extract_words()` for Diagrams

All three reports note that `page.extract_text()` with defaults is the minimum-effort extraction that misses text in shapes. All three recommend switching to `extract_words()` for diagram pages, which returns word-level bounding boxes.

**Current code (text.py lines 217-253):**
```python
page_text = page.extract_text()  # no parameters, defaults only
```

**Recommended change for diagram pages:**
Use `page.extract_words()` to get all words with coordinates. Then optionally use `page.rects` and `page.lines` to associate words with containing shapes via point-in-rectangle tests.

**Why this helps even if the LLM is the primary extractor:**
- Provides ground-truth text labels that the LLM can match against its visual perception
- Enables post-hoc validation (did the LLM find all the labels pdfplumber found?)
- Feeds searchable text into the Markdown output even if LLM extraction fails
- The prompt instruction becomes: "Use the exact text labels visible in the image. Here are labels extracted from the PDF text layer: [word list]"

**Edge cases all three acknowledge:**
- Text inside shapes constructed from grouped lines or curves (not rectangles) defeats simple containment checks
- Text that overflows shape boundaries fails strict containment
- Rotated/path-based text is hard to map with axis-aligned bounding boxes
- Some PDFs have outlined text (converted to vector paths, no longer text objects) — pdfplumber returns nothing

### 5. New `DiagramAnalysis` Schema Needed

All three reports propose a new schema. The structures are similar enough to synthesize into a unified recommendation.

**Agreed core fields:**

```
diagram_type: enum (system_architecture, flowchart, data_flow, sequence, erd, org_chart, network_topology, unknown)
title: string (optional, page title or inferred)
nodes: list of {
    id: string (stable per page),
    label: string (exact text from diagram),
    type/kind: string (service, datastore, queue, actor, external_system, boundary, unknown),
    group/container_id: string (optional, references a group),
    technology: string (optional, e.g., "PostgreSQL", "React")
}
edges: list of {
    source/from_id: string,
    target/to_id: string,
    label: string (optional, protocol/action/event),
    direction: enum (->, <->, undirected, unknown)
}
groups/containers: list of {
    id/name: string,
    contains: list of node ids
}
mermaid: string (valid Mermaid.js code)
description/summary: string (prose for full-text search)
confidence: float or enum
```

**Model O uniquely adds:**
- `source_text` field on each node: "pdf_native" | "ocr" | "vision" (tracks where each label came from)
- `uncertainties` list: explicit list of issues (e.g., "Queue label partially occluded; verify")
- `evidence.extracted_text_inventory`: list of all text strings found by PDF extraction, for validation

These additions are worth including — they enable quality assessment without manual review.

### 6. Source Image Must Always Be Embedded

No extraction is perfect. All three reports say the original PNG belongs in the Markdown output as the canonical visual reference. This is already how the pipeline works for slides (`![Slide N](slides/slide-NNN.png)`).

### 7. Heavyweight ML Models and GPU OCR Are Not Worth It

All three reject:
- **DocLayout-YOLO, Detectron2, etc.** for page classification: too much dependency weight for a CLI tool when pdfplumber heuristics suffice.
- **PaddleOCR, Surya, etc.** for local OCR: GPU-dependent or too slow on CPU for the 60-second constraint, when cloud vision LLMs are already available.
- **Custom diagram recognition models:** No labeled training data, engineering time exceeds value for tens-to-hundreds of documents.
- **Parsing PDF vector graphics into diagram structure:** Interpreting PDF drawing commands as semantic elements is brittle across authoring tools. Rasterize and use vision LLMs instead.

---

## Contested: Where the Reports Meaningfully Disagree

These are the decisions that need empirical testing on your actual corpus.

### 1. The Core Architecture Question: Vision-LLM-Only vs. Hybrid

This is the most consequential disagreement.

**Model A: Vision-LLM-primary is sufficient.**
- Cites Flowchart2Mermaid benchmark (December 2025): entity F1 >0.94, relationship F1 ~0.91-0.93 for GPT-4.1, GPT-4o, Gemini-2.5-Flash.
- Position: Vision LLMs have crossed a critical threshold. PDF text enrichment is a modest supplement, not a necessity.
- Recommends: "Vision-LLM-primary with lightweight PDF-native text enrichment."

**Model G: Hybrid is strictly necessary.**
- Argues vision LLMs suffer from a "binding problem": they identify elements but fail to correctly associate labels with shapes in dense diagrams.
- Claims Claude achieves 94.2% structured extraction accuracy vs GPT-4o at 91.8% and Gemini at 89.4% (sourcing unclear for diagram-specific tasks).
- Position: For complex enterprise architectures, relying on vision alone is architecturally irresponsible.
- Recommends: Deterministic spatial anchoring via pdfplumber bounding box logic before LLM inference.

**Model O: Hybrid is necessary, and even hybrid has hard limits.**
- Cites a 2025 system-maps evaluation: best observed edge+polarity F1 was 0.62 for JSON output.
- Cites VGCURE benchmark: LVLMs struggle with edge/neighbor tasks even when node counting is easier.
- Position: Vision LLMs are a "strong semantic integrator" but not a reliable perception engine. Nodes are easier than edges. Edge extraction remains fundamentally imperfect.
- Recommends: Full extract → verify → patch loop with tiling/zooming.

**Assessment:** The disagreement maps to different benchmarks. Model A's Flowchart2Mermaid numbers (F1 >0.94) likely reflect simpler, cleaner diagrams. Model O's system-maps numbers (F1 ~0.62) likely reflect messier, denser diagrams closer to real consulting work. The truth depends on YOUR diagrams.

**Empirical test needed:** Run 20 diverse diagrams from your actual corpus through the pipeline. Measure:
- Node label recall (what % of visible labels did the LLM find?)
- Edge accuracy (what % of connections are correct? what % are hallucinated?)
- Variation by diagram complexity (simple 5-component vs dense 30+ component)

If node recall >90% and edge accuracy >80% on your corpus with a single-image approach, Model A's architecture is sufficient. If edge accuracy drops below 70% on dense diagrams, Model O's verify/patch loop becomes necessary.

### 2. Image Strategy: Single Image vs. Tiling

**Model A:** Render at 300 DPI, pre-resize to 1568px longest edge, send single image. Simple and cost-effective.

**Model G:** Render at 300 DPI, send single image. Rely on CCoT prompting to compensate for perception limits.

**Model O:** Render at 300 DPI, send global overview PLUS zoomed quadrant crops (2×2, then 3×3 if needed). Cites vendor documentation that internal resizing means higher DPI doesn't translate to more effective pixels unless you tile. This is the only report that proposes tiling.

**Assessment:** Model O's tiling is the most technically grounded approach for small-text recovery, but it multiplies LLM calls by 2-5x per page. At Claude Sonnet pricing, a page with overview + 4 quadrant crops could cost $0.10-0.15 per page just for image processing, consuming the entire budget before validation passes.

**Recommendation:** Start with Model A's single-image approach. Add tiling only if empirical testing shows small-text misreads on your specific diagrams. Tiling is a good `--thorough` mode, not a default.

### 3. Validation and Repair Strategy

**Model A (lightest):** Validate Mermaid syntax (run parser or `mmdc --validate`). On failure, send error back to LLM for one repair attempt. If repair fails, fall back to prose-only output with source image. Also: compare extracted labels against pdfplumber word inventory as a coverage check, flag pages where <70% of words appear.

**Model G (medium):** Two-stage Compositional Chain-of-Thought (CCoT) in a single API call. The LLM first builds a "scene graph" in its thinking/scratchpad (enumerate all nodes, transcribe labels, note spatial coordinates), then generates the structured output. This is a prompting strategy, not a post-processing loop. No explicit post-hoc validation.

**Model O (heaviest):** Full extract → verify → patch loop. Pass A: extract structured JSON + Mermaid. Pass B: feed back the extracted data plus the PDF/OCR text inventory; ask the model to mark unsupported labels, flag edges with nonexistent endpoints, and output a patch (additions/removals/edits). Expects retries and robust error handling.

**Assessment:** These represent increasing investment in quality at increasing cost and complexity. For MVP, Model A's approach is right. For a later `--thorough` flag, Model O's verify loop is the most rigorous.

**Recommendation for implementation phasing:**
- **MVP:** Mermaid syntax validation + one retry. Coverage check against pdfplumber text. Graceful fallback to prose-only.
- **Later:** Add optional verify/patch pass (Model O) for high-value documents.

### 4. Which Vision LLM to Default To

**Model A:** No strong preference. Notes GPT-4.1 and Gemini-2.5-Flash perform well.
**Model G:** Strongly favors Claude. Claims "demonstrably superior prompt adherence" and "lower rates of architectural hallucination."
**Model O:** Says test on your corpus. No favoritism.

**Assessment:** Model G's Claude recommendation lacks clear sourcing for diagram-specific tasks. Its cited numbers may reflect general structured output tasks, not diagram extraction specifically.

**Recommendation:** Don't pick a default from desk research. Run the same 10 diagrams through Claude Sonnet, GPT-4o, and Gemini-2.5-Flash. Compare quality, cost, and latency. Use the results to set the default. The existing LLM profile routing in `folio.yaml` already supports this.

### 5. Poppler GPL Licensing

**Model O flags this; Models A and G do not mention it.**

The current pipeline depends on Poppler (GPL-2.0) via pdf2image/pdftoppm. pdf2image is MIT, but Poppler itself is GPL. If the Apache 2.0 licensing constraint means "no copyleft anywhere in the toolchain," this is already a violation.

Model O suggests pypdfium2 (Apache-2.0 or BSD-3-Clause) as an alternative renderer and text extractor. It also recommends pypdfium2 as a secondary text extraction tool (`get_text_bounded()`, `get_charbox()`) for diagrams.

**Decision needed:** Is your constraint "no copyleft Python packages" (currently satisfied) or "no copyleft in the toolchain" (currently violated by Poppler)? This isn't urgent for diagram extraction but is a real project-level question.

---

## Standout Findings (Unique to One Report)

### From Model A

**Specific cost analysis:** ~$0.02-0.03/page with Claude Sonnet, ~$0.01-0.02 with Gemini 2.5 Pro for the extraction pass. This leaves room for classification ($0.002 with Haiku) and optional validation within the $0.10-0.15 budget.

**Pre-resize to 1568px:** Aligns with Claude's documented processing resolution. Render at 300 DPI for quality, then downscale before API call to minimize token cost. Specific and actionable.

**Mermaid syntax validity scores:** Reports 0.998-1.0 for top models after a processing/repair loop, suggesting Mermaid generation is reliable enough that a single retry covers almost all failures.

**Expected quality estimate for MVP:** ">90% of components correctly identified, >85% of connections correct" for typical consulting architecture diagrams with 5-25 components.

### From Model G

**"Binding problem" framing:** The theoretical argument that VLMs process images as patch grids and lose the association between labels and shapes in dense layouts. Whether this is a real architectural limitation or an artifact of older evaluations is unclear, but it's a useful mental model for predicting where extraction will fail.

**Compositional Chain-of-Thought (CCoT) prompting:** A specific prompting technique where the model first builds a "scene graph" (enumerating all nodes, transcribing labels, noting spatial coordinates) in a thinking block before producing structured output. This forces sequential spatial reasoning and reportedly improves binding accuracy. Worth testing as a prompt design strategy.

**Markdown table vs JSON for Obsidian searchability:** Model G notes that Obsidian can't natively query deep JSON structures without plugins, and recommends rendering the component list as a Markdown table in addition to (or instead of) a JSON block. This is a practical observation about Obsidian's indexing behavior.

**Mermaid token efficiency:** Claims Mermaid consumes "up to 24 times fewer tokens" than XML/JSON diagram formats like draw.io or Excalidraw. If accurate, this reinforces Mermaid as the right choice for token-budget-constrained extraction.

### From Model O

**Tiling/cropping strategy:** The only report to propose sending multiple zoomed crops alongside the global image. Cites vendor documentation that internal resizing limits effective pixel resolution regardless of source DPI. Even if not implemented in MVP, this is the right architecture for a `--thorough` mode.

**pypdfium2 as secondary extractor:** Recommends adding pypdfium2 (Apache-2.0/BSD-3-Clause) for bounded text extraction (`get_text_bounded()`, `count_chars()`, `get_charbox()`). Claims it gives better signal than pdfplumber for determining whether a page has recoverable text objects.

**`source_text` provenance tracking:** Each node in the schema gets a `source_text` field: "pdf_native" | "ocr" | "vision". This tracks where each label came from, enabling quality assessment and debugging without manual review.

**`uncertainties` list in schema:** Explicit list of extraction issues (e.g., "Queue label partially occluded; verify", "arrowhead unclear between nodes n3 and n5"). This is honest about extraction limits and helps the user know where to focus manual review.

**Pessimistic but well-sourced edge accuracy data:** The system-maps evaluation (F1 ~0.62 for edge+polarity) and VGCURE benchmark provide the most conservative (and possibly most realistic) expectations for complex diagrams. This is valuable for setting appropriate expectations.

**Vendor-specific image handling notes:**
- Claude: scales down images above certain thresholds; oversized images increase latency without improving performance.
- GPT-4o: explicit "detail" levels and tiling behavior affect what the model sees; images are resized before analysis.
- Gemini: `media_resolution` parameter controls vision fidelity; higher resolution costs tokens/latency.

These details matter for optimizing API calls per provider.

---

## Consolidated MVP Implementation Plan

Based on consensus across all three reports, ordered by impact-per-effort.

### Day 1: Fix Blank Detection + Raise DPI

**Fix blank detection (highest priority, ~30 minutes):**
- Add a pdfplumber-based pre-check: count `len(page.rects) + len(page.lines) + len(page.curves)` and `len(page.chars)`.
- A page is blank only if: text chars near zero AND vector objects near zero AND no embedded images.
- Remove or demote the pixel histogram check to advisory status. It should NEVER overwrite LLM output.
- The blank override in converter.py lines 198-201 should use the new definition.

**Raise DPI for diagram pages:**
- Add a diagram classification flag based on the pdfplumber pre-check (see Day 2).
- For pages flagged as diagrams, render at 300 DPI instead of 150.
- Consider Model A's suggestion to pre-resize to ~1568px longest edge before API transmission.
- DPI is already configurable via `ConversionConfig.image_dpi`. The change is to make it conditional per page type.

### Day 2: Diagram Classification + New Prompt + New Schema

**Page classification heuristic:**
```
text_density = len(page.chars) / (page.width * page.height)  # or simpler: len(page.chars)
vector_count = len(page.rects) + len(page.lines) + len(page.curves)
```
Classification rule: if `text_chars < ~100 AND vector_count > ~20`, classify as diagram. Thresholds need tuning on your corpus, but optimize for recall (no missed diagrams; false positives are acceptable since they just trigger a different prompt).

**New `DiagramAnalysis` data class** alongside existing `SlideAnalysis`:
```python
@dataclass
class DiagramAnalysis:
    diagram_type: str = "unknown"  # system_architecture, flowchart, data_flow, sequence, erd, org_chart, network_topology, unknown
    title: str = ""
    confidence: float = 0.0
    nodes: list[dict] = field(default_factory=list)      # {id, label, kind, group, technology}
    edges: list[dict] = field(default_factory=list)       # {source, target, label, direction}
    groups: list[dict] = field(default_factory=list)      # {name, contains: [node_ids]}
    mermaid: str = ""
    description: str = ""
    uncertainties: list[str] = field(default_factory=list) # Model O's suggestion
    evidence: list[dict] = field(default_factory=list)
```

**Diagram-specific LLM prompt** (replaces ANALYSIS_PROMPT when diagram is detected):
The prompt should request a single JSON response containing all fields above. Key prompt instructions:
- "Use the exact text labels visible in the image. Do not paraphrase or abbreviate."
- "If a label is unclear, include your best reading and add an entry to the uncertainties list."
- "For each edge, explicitly state the direction based on arrowheads visible in the image. If direction is unclear, use 'unknown'."
- "Generate valid Mermaid.js code representing this diagram."
- Include pdfplumber-extracted text as supplementary context: "Text extracted from PDF text layer: [word list]. Use these as ground-truth labels where they match visible text."

### Day 3: Output Format + Text Enrichment

**Switch to `extract_words()` for diagram pages:**
Replace `page.extract_text()` with `page.extract_words()` for pages classified as diagrams. Concatenate words into a text inventory to pass alongside the image to the LLM. Optionally use `page.rects` to associate words with shapes.

**Markdown output template for diagrams:**
```markdown
---
type: diagram
diagram_type: {diagram_type}
title: "{title}"
source: "{source_path}"
page: {page_num}
confidence: {confidence}
components:
  - {node labels list}
tags:
  - diagram
  - {diagram_type}
  - {auto-generated tags}
---

# {title}

Extracted from [[{source_file}]], page {page_num}.

## Diagram

```mermaid
{mermaid_code}
```

## Components

{for each node: **[[{label}]]** — {kind}; {technology if present}}

## Connections

{for each edge: {source_label} → {target_label}: {label}}

## Notes

{prose description}

## Extraction Quality

{uncertainties list, if any}

![[{source_file}-p{page_num}.png]]
```

**Key Obsidian integration points:**
- YAML frontmatter enables Dataview queries: `TABLE diagram_type, title FROM #diagram WHERE contains(components, "API Gateway")`
- Wiki-linked component names (`[[API Gateway]]`) appear in Obsidian's Graph View
- Mermaid code blocks render natively in reading view
- Prose description is indexed by full-text search
- Source image is the canonical fallback

**Mermaid validation:**
After LLM generates Mermaid, validate syntax. If invalid, send the error message back to the LLM for one repair attempt. If repair fails, omit the Mermaid block and keep prose + components + image.

---

## Post-MVP: Empirical Testing Plan

All three reports agree that desk research cannot resolve these questions. They require testing on your actual diagram corpus.

### Build a Test Corpus

Select 20-30 diagram pages covering:
- Simple flowcharts (3-10 components)
- Medium architecture diagrams (10-25 components)
- Dense enterprise architectures (25+ components)
- Different authoring tools (Visio, draw.io, Lucidchart, PowerPoint, Miro exports)
- Different styles (monochrome line art, color-coded, icons, gradient fills)
- At least 2-3 scanned/rasterized diagrams if you have them

### Tests to Run

1. **Text extraction coverage:** For each diagram, count visible labels manually. Run pdfplumber `extract_words()` and measure what percentage were captured. This determines how much value PDF-native text adds to the LLM prompt. (Model O notes: also check whether `text_chars == 0` — if many of your PDFs have outlined text, pdfplumber adds no value.)

2. **DPI impact:** Process the same 10 diagrams at 150, 200, and 300 DPI. Compare LLM-extracted label completeness and Mermaid structural accuracy. If 200 DPI matches 300 DPI quality, use 200 to save rendering time.

3. **Model comparison:** Run the same 10 diagrams through Claude Sonnet, GPT-4o, and Gemini-2.5-Flash. Compare:
   - Node label recall (what % of visible labels were found?)
   - Edge accuracy (what % of connections are correct? what % hallucinated?)
   - Mermaid syntax validity
   - Cost per page
   - Latency per page

4. **Prompt comparison:** Test at least 2 prompt variants on 10 diagrams:
   - (A) Single-pass "extract everything" prompt
   - (B) Prompt with pdfplumber text enrichment included
   Measure component coverage and connection accuracy. This determines whether PDF text enrichment justifies its inclusion.

5. **Classification threshold calibration:** Run the pdfplumber heuristic (`chars < threshold AND vectors > threshold`) on your full corpus of slide decks AND diagram PDFs. Count false positives and false negatives. Adjust thresholds until false negatives hit zero.

6. **Blank detection calibration:** Collect 5 truly blank pages and 5 sparse-but-real diagrams. Run the new detection on both sets and verify zero false negatives on diagrams.

7. **Mermaid rendering in your Obsidian version:** Test which diagram types (flowchart, sequence, ER, state, etc.) render correctly. Note any syntax that Obsidian's embedded Mermaid version doesn't support.

### Based on Test Results, Decide

- **If edge accuracy > 80% on most diagrams:** Single-image approach is sufficient. Ship it.
- **If edge accuracy drops below 70% on dense diagrams:** Consider Model O's tiling strategy and/or verify/patch loop for a `--thorough` mode.
- **If pdfplumber text coverage > 70% on most diagram PDFs:** Text enrichment is clearly worth including.
- **If pdfplumber text coverage < 30%:** Your PDFs may have outlined text. pypdfium2 (Model O's suggestion) or OCR fallback may be needed, or just rely on vision LLM for text.
- **If one LLM clearly outperforms others on your corpus:** Set it as the default for diagram extraction via `folio.yaml` routing.

---

## Open Technical Decisions for Claude Code

These are implementation decisions that require codebase context to resolve. Flagging them explicitly.

1. **Where does diagram classification happen in the pipeline?** Currently, blank detection happens in `images.extract_with_metadata()` and the blank override happens in `converter.py`. The new diagram classification could happen: (a) in a new step between image extraction and text extraction, (b) as an enhancement to `images.extract_with_metadata()`, or (c) as a pre-check before LLM analysis in the converter. What's cleanest given the current orchestration?

2. **How do `DiagramAnalysis` and `SlideAnalysis` coexist?** The converter currently expects `dict[int, SlideAnalysis]`. Options: (a) make DiagramAnalysis a subclass, (b) use a Union type, (c) create a common Protocol/interface, (d) keep them separate and branch in the assembler. What fits the existing type usage?

3. **How does `frontmatter.generate()` handle the new schema?** It currently consumes `dict[int, SlideAnalysis]` and collects frameworks/slide_types. For diagram pages, it needs to emit `diagram_type`, `components`, and potentially different tag generation logic. Branch inside `generate()` or separate function?

4. **How does `markdown.assemble()` handle the new output template?** Diagram pages need a different template (Mermaid block, components section, connections section) than slide pages. Branch inside assemble or separate assembler?

5. **Should the DPI decision be per-page or per-document?** If a PDF is mostly diagrams, render everything at 300 DPI. If it's mostly text with one diagram, render only the diagram page at 300 DPI. The current pipeline renders all pages at the same DPI in one `convert_from_path()` call. Per-page DPI would require rendering pages individually, which changes the image extraction approach.

6. **Cache implications:** The analysis cache keys presumably include the image path. If the same page is re-rendered at a different DPI, does the cache key change? It should.

7. **Test infrastructure:** There are currently no diagram-specific test fixtures (506 tests, zero diagram fixtures). What test fixtures are needed, and what's the test strategy for non-deterministic LLM outputs?

---

## Risk Register (Consolidated from All Three Reports)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Blank detection destroys valid LLM output | **Certain** (currently happening) | **Critical** | Fix immediately: PDF object counting replaces pixel histogram as gate |
| LLM-generated Mermaid has syntax errors | Medium-High | Medium | Validate syntax after generation; one retry with error message; fall back to prose-only |
| Missing connections in complex diagrams (>25 components) | High | Medium-High | Always include source image; add confidence score; consider verify/patch loop for high-value docs |
| Label paraphrasing by LLM ("Database" → "Data Store") | High | Medium | Include pdfplumber text in prompt with "use exact labels" instruction; include raw text in output |
| Small text misread at 150 DPI | High | Medium | Raise to 300 DPI for diagram pages; pre-resize for token efficiency |
| Rasterized PDFs defeat pdfplumber text extraction | Medium-High in heterogeneous archives | High | Detect via `text_chars == 0` on non-blank page; vision LLM handles text from image; pdfplumber enrichment simply skipped |
| Inconsistent results across LLM sessions | Medium | Medium | Set temperature to 0; use JSON schema mode; cache results |
| AGPL dependency accidentally introduced | Medium | High | Maintain license allowlist; add CI check via `pip-licenses` or `liccheck` |
| Poppler GPL already in toolchain | Certain | Medium | Decide: is constraint "no copyleft Python deps" or "no copyleft anywhere"? If latter, evaluate pypdfium2 |
| DPI upscaling breaches 60s page limit | Low | Medium | Restrict 300 DPI to diagram pages only; pre-resize before API call |
| Mermaid rendering breaks on Obsidian update | Low | Low | Use only stable Mermaid syntax; JSON sidecar preserves data regardless |
| API cost spike on complex batch | Low | Medium | Pre-resize images; use prompt caching; set per-run cost ceiling |
