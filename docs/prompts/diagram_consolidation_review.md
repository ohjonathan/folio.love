# Diagram Research Consolidation Review

**Date:** 2026-03-14
**Input:** `diagram-research-consolidation.md`
**Reviewer:** Claude Code (with full codebase access)

---

## 1. Factual Corrections

The consolidation's codebase references are accurate. Specific checks:

- **Blank detection at `images.py` lines 184-195:** Correct. Code matches the pasted snippet exactly.
- **Blank override at `converter.py` lines 198-201:** Correct. The four-line loop is verbatim.
- **`page.extract_text()` with no parameters in `text.py`:** Correct. Line 238: `page_text = page.extract_text()` — no arguments.
- **`SlideAnalysis` as the only analysis dataclass:** Correct. There is also `CacheStats`, `StageLLMMetadata`, and `SlideText`, but `SlideAnalysis` is the only *analysis result* dataclass.
- **`ConversionConfig.image_dpi` as the DPI control point:** Correct. `config.py` line 144, passed through `converter.py` line 128 to `images.extract_with_metadata(pdf_path, deck_dir, dpi=self.config.conversion.image_dpi)`.
- **Pipeline sequence:** Correct.

**One inaccuracy in the consolidation:** Line 46 says `to_pdf()` returns `Path` at line 39. The actual signature at line 39 returns `Path` in the type hint but the return annotation was dropped. The actual return type is `NormalizationResult` (a dataclass with `pdf_path` and `renderer_used`). This doesn't affect the diagram work but is worth noting — the consolidation's pipeline description at line 12 correctly says "normalize" but doesn't mention the `NormalizationResult` wrapper.

**No recent changes** that the consolidation misses. The git log shows the last substantive code changes were in the Tier 2 closeout (PR #17, documentation only). The codebase is stable.

---

## 2. Answers to the Seven Open Technical Decisions

### Q1: Where does diagram classification happen?

**Recommendation: New function in `text.py`, called from `converter.py` between Stage 2 and Stage 3.**

Rationale:
- The classification needs pdfplumber access (`page.rects`, `page.lines`, `page.curves`, `page.chars`). pdfplumber is already imported in `text.py` but not in `images.py`.
- `images.extract_with_metadata()` operates on the PDF-as-rendered (via pdf2image/Poppler). It doesn't open the PDF with pdfplumber — it opens the already-extracted PNGs with Pillow. Adding pdfplumber to `images.py` would create a new dependency and blur the stage's responsibility.
- The converter already opens the PDF via `text.extract_structured(source_path)` at line 156. The classification should happen *before* text extraction so the results can inform both text extraction strategy (Q: `extract_words()` vs `extract_text()`) and DPI selection.

Concrete approach: Add `classify_pages(pdf_path) -> dict[int, PageType]` to `text.py` (or a new `folio/pipeline/classify.py` if you want separation). Call it from `converter.py` between image extraction (Stage 2) and text extraction (Stage 3). The result feeds into:
1. A re-render at 300 DPI for diagram pages (see Q5)
2. The text extraction path choice (`extract_words()` vs `extract_text()`)
3. The LLM prompt selection (diagram prompt vs slide prompt)

The blank detection fix also belongs here — replace the Pillow histogram gate with the pdfplumber object-count check as part of the same classification pass.

### Q2: How do `DiagramAnalysis` and `SlideAnalysis` coexist?

**Recommendation: Shared `Protocol` (or `Union` type alias), not inheritance.**

Rationale:
- `SlideAnalysis` and `DiagramAnalysis` have different fields. Inheritance is the wrong tool — a diagram is not a subtype of a slide.
- The converter stores results as `dict[int, SlideAnalysis]` (line 187). Downstream consumers (`frontmatter.generate()`, `markdown.assemble()`) accept this type.
- The lightest change: define `AnalysisResult = SlideAnalysis | DiagramAnalysis` and update the type annotations. Then branch in the two consumers (`frontmatter.py` and `markdown.py`) via `isinstance()` checks.
- Both classes need `.to_dict()` and `.from_dict()` for cache serialization. Add a `"_type": "diagram"` marker in the cached dict so `from_dict` can dispatch.
- Both need a `.pending()` classmethod for error handling. The pending state can be shared via a standalone function if you prefer, but a classmethod on each is simpler.

Effort note: The consolidation underestimates this. The `SlideAnalysis` type flows through the cache system (`_load_cache`, `_save_cache`, `_hash_image`), the fallback system (`_analyze_with_fallback`), and the evidence validation (`_validate_evidence`). All of these need to be aware of the new type. Count ~2 hours, not 30 minutes.

### Q3: How does `frontmatter.generate()` handle the new schema?

**Recommendation: Branch inside `generate()`, not a separate function.**

Rationale:
- `generate()` is called once per document from `converter.py` line 276. The frontmatter structure is mostly the same (identity, lifecycle, source, temporal fields are identical). The difference is:
  - `type: "evidence"` → `type: "diagram"` (or keep `"evidence"` and add `subtype: "diagram"`)
  - `frameworks` / `slide_types` fields are replaced by `diagram_type` / `components`
  - Tag generation uses different logic (diagram type tags, component names)
- The function already handles optional fields conditionally (lines 120-148). Adding a branch for diagram analyses fits the existing pattern.
- `_collect_unique()` (line 61) iterates `analyses.values()` and reads `.framework` / `.slide_type`. For diagram pages, it should skip or read the equivalent fields. An `isinstance()` check on the analysis value is sufficient.

The consolidation's proposed frontmatter (lines 346-357) uses `type: diagram` — this would break the current ontology where `type` is always `"evidence"`. Consider `subtype: "diagram"` instead, keeping `type: "evidence"` for consistency with existing Dataview queries.

### Q4: How does `markdown.assemble()` handle the new output template?

**Recommendation: Branch inside `_format_slide()` (line 100 of `markdown.py`), not a separate assembler.**

Rationale:
- `assemble()` iterates slides 1 through `slide_count` and calls `_format_slide()` per page (line 64). The diagram template only differs at the per-page level — the document header, version history, and overall structure remain the same.
- `_format_slide()` already handles conditional sections (text present/absent, analysis present/pending). Adding a diagram branch is natural:

```python
if isinstance(analysis, DiagramAnalysis):
    return _format_diagram_page(slide_num, text, analysis, ...)
```

- The consolidation's proposed template (lines 343-386) uses Obsidian wiki-links (`[[API Gateway]]`) and `![[source.png]]` syntax. The current pipeline uses standard Markdown links (`![Slide N](slides/slide-NNN.png)`). Wiki-links are Obsidian-specific and would break in other Markdown renderers. Stick with standard Markdown image syntax. Wiki-linking component names is an optional enhancement that belongs in post-MVP.

### Q5: Should DPI be per-page or per-document?

**Recommendation: Per-document, with a separate render pass for diagram pages.**

Rationale:
- `pdf2image.convert_from_path()` renders all pages at the same DPI in one call (line 76 of `images.py`). It *does* support `first_page` and `last_page` parameters, so you can render individual pages at different DPI.
- The cleanest approach: render everything at 150 DPI first (current behavior). Then, for pages classified as diagrams, re-render just those pages at 300 DPI and replace the corresponding PNGs in the slides directory.
- This avoids changing the core `extract()` function signature and keeps the atomic swap logic intact. The re-render happens after classification (which happens after the initial extract, per Q1).
- Per-page rendering within a single `convert_from_path` call is not supported by pdf2image — you'd need multiple calls. But since diagram pages are typically a small fraction, the overhead of individual re-renders is manageable.
- The consolidation's Model A suggestion to pre-resize to ~1568px before API transmission is worth implementing. Add it to the provider adapter (`providers.py`) or as a preprocessing step in `_analyze_single_slide()`.

### Q6: Cache key implications?

**Recommendation: The cache is already DPI-safe. No changes needed for keys, but use a separate cache file.**

The cache key is `_hash_image(image_path)` — a SHA256 of the **image file contents** (`analysis.py` line 1083-1089). If the same page is re-rendered at 300 DPI, the PNG file is different, producing a different hash. The cache naturally invalidates.

However: the cache *metadata* (`_prompt_version`, `_model_version`) is document-wide. If you introduce a diagram-specific prompt, you'll need either:
- A separate cache file for diagram analyses (e.g., `.analysis_cache_diagram.json`), or
- Per-entry prompt version tracking (add `"_prompt_version"` to each cached entry alongside `"_text_hash"`)

The simpler approach is a separate cache file, matching the existing pattern of `.analysis_cache.json` (Pass 1) and `.analysis_cache_deep.json` (Pass 2).

### Q7: Test infrastructure and fixtures?

**Recommendation: Three test fixtures, mock-based LLM tests.**

Needed fixtures:
1. **Simple diagram PDF** (5-10 boxes with text, arrows, white background) — tests that blank detection does NOT fire, text extraction captures some labels, classification flags it as diagram.
2. **Sparse line diagram PDF** (few thin lines on white) — tests the blank detection boundary case. This is the regression test for the false-blank bug.
3. **Dense diagram PDF** (25+ components, color, small text) — tests DPI upscaling impact and LLM prompt routing.

For LLM output tests, follow the existing pattern: the test suite mocks the provider (`_analyze_single_slide` or the provider adapter) and feeds canned JSON responses. This is how the existing 506 tests handle non-deterministic LLM output — they never call the real API.

New test files needed:
- `tests/test_classify.py` — page classification heuristics
- `tests/test_diagram_analysis.py` — `DiagramAnalysis` dataclass, serialization, pending state
- Updates to `tests/test_images.py` — blank detection with diagram fixtures
- Updates to `tests/test_frontmatter.py` and `tests/test_markdown.py` — diagram output formatting

The consolidation estimates "Day 1" for the blank detection fix. For the fix itself, that's reasonable (~1-2 hours). But the test fixtures (creating actual PDF files with known properties) will take longer. Use `reportlab` or a hand-authored PDF to create fixtures with known vector object counts.

---

## 3. What the Consolidation Misses

### 1. The text extraction path divergence (PPTX vs PDF)

The consolidation focuses on `_extract_pdf()` but doesn't mention that PPTX files use a completely different text extraction path (`_extract_pptx()` via MarkItDown, `text.py` line 164). If the source was a PPTX diagram deck (converted to PDF via PowerPoint/LibreOffice in Stage 1), the text extraction in Stage 3 operates on the **original PPTX**, not the rendered PDF:

```python
# converter.py line 156
slide_texts = text.extract_structured(source_path)  # source_path, NOT pdf_path
```

This means:
- For native PDF diagrams: pdfplumber is the text extractor (consolidation's assumption is correct)
- For PPTX-sourced diagrams: MarkItDown extracts text from the PPTX XML, which likely captures text inside shapes better than pdfplumber does on the rendered PDF

The diagram classification heuristic (pdfplumber `page.rects`/`page.chars`) must run on the **rendered PDF**, not the source PPTX. But text extraction for PPTX diagrams may not need the `extract_words()` upgrade if MarkItDown already handles shape text.

### 2. The `reconcile_slide_count()` interaction

After text extraction, the converter calls `reconcile_slide_count()` (line 174) to align text count with image count. If diagram classification changes the number of images (e.g., re-rendering at different DPI changes page count — unlikely but possible with split/merge), or if a new classification step inserts empty `SlideText` entries for diagram pages, reconciliation needs to handle it. The current reconciliation logic is purely additive (pad/truncate), so it should be fine, but the consolidation doesn't mention this step at all.

### 3. The `_validate_evidence()` function won't work for diagrams

`_validate_evidence()` (`analysis.py` line 584) checks LLM evidence quotes against `slide_text.full_text` using normalized string matching. For diagram pages where pdfplumber returned little/no text, all evidence will be marked `validated: False`. This is technically correct (the evidence can't be validated against extracted text) but it means the grounding summary in frontmatter will show 100% unvalidated for diagram pages. The consolidation's `DiagramAnalysis` schema includes an `evidence` field but doesn't address this validation gap.

Consider: for diagram pages, validate node labels against pdfplumber's `extract_words()` output instead of full-text matching. Or skip evidence validation entirely for diagram analyses and rely on the `confidence` and `uncertainties` fields.

### 4. The `_collect_unique()` filter in frontmatter will silently drop diagram data

`_collect_unique()` (`frontmatter.py` line 160) skips slides where "evidence exists but none is validated." If all diagram page evidence is unvalidated (per #3 above), the entire page's `framework` and `slide_type` will be excluded from the frontmatter's `frameworks` and `slide_types` lists. This is the existing behavior for unverifiable evidence, but it would mean diagram types never appear in frontmatter unless the validation logic is updated.

### 5. The sparse-text warning will fire on diagram pages

`converter.py` lines 160-172 emit a warning when average chars per page < 10. Diagram pages with little extractable text will trigger this warning for every diagram PDF. This is noise, not a bug, but it should be suppressed for pages classified as diagrams.

### 6. Cache file naming

The consolidation doesn't address where diagram analysis results are cached. The current system uses `.analysis_cache.json` (Pass 1) and `.analysis_cache_deep.json` (Pass 2). A diagram-specific prompt needs its own cache file (e.g., `.analysis_cache_diagram.json`) because the `_prompt_version` check would invalidate the entire cache whenever the slide prompt OR diagram prompt changes. Keeping them separate means prompt changes only invalidate the relevant cache.

### 7. CLI surface

The consolidation doesn't mention CLI changes. At minimum:
- `--passes` currently controls Pass 2 depth analysis. Diagram pages probably don't need Pass 2 (the `DEPTH_PROMPT` is consulting-slide-oriented). The converter should skip `analyze_slides_deep()` for diagram pages.
- No new CLI flags are needed for MVP (diagram handling should be automatic), but `--diagram-dpi` or `--no-diagram-detect` could be useful for debugging.

### 8. The `subtype` parameter

The current `subtype` choices are `["research", "data_extract", "external_report", "benchmark"]` (CLI line 115). If diagram documents get `type: "diagram"` in frontmatter (as the consolidation proposes), this conflicts with the CLI's `--subtype` flag which assumes `type: "evidence"`. The cleaner path is `subtype: "diagram"` under `type: "evidence"`, or auto-detecting subtype when the document is predominantly diagram pages.
