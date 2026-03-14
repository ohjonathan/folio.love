# Review: Diagram Research Consolidation Against Codebase

## 1. Factual Corrections

- The line references for blank detection are still current. `_is_mostly_blank()` is still at `folio/pipeline/images.py:184-195`, and it still does grayscale histogram blanking with `hist[241:]` and a `0.95` threshold. One nuance the consolidation misses: that heuristic is used both in `extract_with_metadata()` and `_validate_image()`, so changing it touches both call paths in `folio/pipeline/images.py:132-181`.

- The blank override is also still current at `folio/converter.py:198-201`. The consolidation understates the effect: those slides are also excluded from Pass 2 via `skip_slides=blank_slides` at `folio/converter.py:203-220`.

- `page.extract_text()` is still called with no parameters in the PDF path at `folio/pipeline/text.py:217-246`. But the consolidation's pipeline description is incomplete: `convert()` calls `text.extract_structured(source_path)` on the original source at `folio/converter.py:154-156`, so PPTX/PPT inputs go through MarkItDown `_extract_pptx()`, not pdfplumber, at `folio/pipeline/text.py:164-214`.

- `SlideAnalysis` is still the only slide-analysis dataclass at `folio/pipeline/analysis.py:48-100`. There is no existing `DiagramAnalysis`. There are other dataclasses in the stack, but they are cache/metadata types, not content-analysis models, at `folio/pipeline/analysis.py:102-123` and `folio/llm/types.py:99-110`.

- `ConversionConfig.image_dpi` is still the only DPI control point at `folio/config.py:141-149`, and `convert()` still passes it straight into image extraction at `folio/converter.py:126-129`. There is no CLI override for DPI.

- The stated pipeline order is only approximately right. The actual orchestration is normalize -> images -> text-from-original-source -> pass1 analysis -> optional pass2 -> source/version tracking -> frontmatter -> markdown -> registry in `folio/converter.py:112-340`. So the doc misses Pass 2 and the source-type branch in text extraction.

- The proposed diagram markdown template is not a drop-in fit. Current output is one markdown file per deck with per-slide sections in `folio/output/markdown.py:11-77`, and frontmatter is deck-level with hardcoded `type: evidence` in `folio/output/frontmatter.py:97-118`. A per-page note with `type: diagram`, `page`, and `![[...]]` is a storage-model change and would fail the current validator's allowed types in `tests/validation/validate_frontmatter.py:17-29`.

- Recent commits on `main` are docs-only; there is no March 13-14 code churn in these modules. The real omissions are structural: PowerPoint staging in `folio/pipeline/normalize.py:15-20`, multi-provider routing/fallback in `folio/config.py:49-138` and `folio/pipeline/analysis.py:326-453`, and Pass 2/deep cache in `folio/pipeline/analysis.py:732-924`.

## 2. Seven Open Decisions

### 1. Where does diagram classification happen in the pipeline?

Diagram classification should happen in a new PDF-page inspection step immediately after normalize and before images/text, inside the tempdir scope in `folio/converter.py:109-123`. That is cleaner than hiding it in `folio/pipeline/images.py:132-159`, because blank/diagram detection is PDF-structural, not raster-based, and `pdf_path` only exists there.

### 2. How do `DiagramAnalysis` and `SlideAnalysis` coexist?

I would not add a sibling `DiagramAnalysis` type for MVP. Extend `SlideAnalysis` in `folio/pipeline/analysis.py:48-100` with optional diagram fields and use `slide_type="diagram"` or a discriminator. I disagree with the consolidation on a separate class here because cache serialization, Pass 2, frontmatter, and markdown all already assume `dict[int, SlideAnalysis]`.

### 3. How does `frontmatter.generate()` handle the new schema?

`frontmatter.generate()` should stay a single function in `folio/output/frontmatter.py:13-157` and branch internally for deck-level aggregation only. Add optional aggregated fields like `diagram_types` or similar if needed; do not emit per-page `type: diagram` frontmatter.

### 4. How does `markdown.assemble()` handle the new output template?

`markdown.assemble()` should stay the top-level assembler in `folio/output/markdown.py:11-77`. Add a diagram-specific helper called from `_format_slide()`, not a separate assembler, unless you intentionally change the output model from one-note-per-deck to one-note-per-page.

### 5. Should the DPI decision be per-page or per-document?

The DPI decision should be per-page, not per-document. The rest of the pipeline is already slide-granular, and cache keys are per image bytes in `folio/pipeline/analysis.py:1083-1089`, so rendering an entire mixed deck at 300 DPI would create needless cache churn. But this is not a trivial tweak: `folio/pipeline/images.py:29-129` currently renders all pages in one `convert_from_path()` call, so this is a real extraction refactor.

### 6. Cache implications of different DPI rendering?

Keep the image-hash cache key, but add a per-entry prompt/schema discriminator. Different DPI already changes the hash, so affected pages miss cache automatically. The real issue is prompt variation: `folio/pipeline/analysis.py:1097-1154` only validates one file-level `ANALYSIS_PROMPT` hash, which is insufficient if some pages use a diagram prompt and others use the normal slide prompt.

### 7. Test infrastructure and fixtures needed?

Reuse the current test seams instead of inventing a new LLM-heavy harness. Add a small set of real PDF fixtures for vector sparse diagram / blank page / rasterized diagram / mixed deck, unit-test page inspection with mocked `pdfplumber` pages, and extend the existing mocked integration patterns in `tests/test_converter_integration.py:64-126`, `tests/llm_mocks.py:1-95`, and `tests/test_analysis_cache.py`. Current `.venv` collection still reports 506 tests; there are no diagram fixtures today.

## 3. What The Consolidation Misses

- The existing `SlideText` and `_build_text_context()` path is already the text-to-prompt seam in `folio/pipeline/text.py:18-37` and `folio/pipeline/analysis.py:146-156`. A diagram word inventory should plug into that, not create a second ad hoc prompt payload.

- `_collect_unique()` in `folio/output/frontmatter.py:160-179` excludes analyses whose evidence is all unvalidated. That will interact badly with diagram pages that have weak or no PDF-native text, because vision-only evidence may never validate and then diagram metadata disappears from aggregated frontmatter.

- `_generate_tags()` currently ignores `slide_types` even though it receives them in `folio/output/frontmatter.py:234-263`. So diagram tagging will need explicit new logic; it does not "just work" through the current tag generator.

- Pass 2 is consulting-slide specific. The deep prompt, density scoring, and data-heavy heuristics in `folio/pipeline/analysis.py:623-695` and `folio/pipeline/analysis.py:732-924` do not map cleanly to diagram extraction. You need an explicit decision: separate diagram depth pass, custom scoring, or skip Pass 2 for diagrams.

- Provider-specific recommendations in the consolidation do not fit the current abstraction yet. `ProviderInput` in `folio/llm/types.py:21-32` only supports one `image_path`, one `prompt`, and `max_tokens`; there is nowhere to express OpenAI `detail`, Gemini `media_resolution`, or overview-plus-crops tiling.

- Mermaid validation is not free. There is no Mermaid parser or `mmdc` integration anywhere in the repo today, so syntax validation would introduce a new dependency or optional external binary.

- The proposed schema conflicts with current ontology/use of frontmatter. `type: diagram` is invalid today, and `description`/`evidence` overlap with existing `SlideAnalysis` fields. If the goal is queryable diagram structure, extending the existing evidence-doc model fits better than inventing a parallel note type.

- Effort is understated in three places:
  - Fixing the post-LLM blank override alone is small, but doing blank/diagram detection at the right seam with pdfplumber and tests is closer to 0.5-1 day.
  - Per-page DPI is more like 1-2 days because `folio/pipeline/images.py:29-129` assumes a single-DPI render path.
  - A separate per-page diagram note model is beyond MVP. It changes frontmatter schema, markdown assembly, versioning, registry behavior, and validation rules.

## Verification Notes

- Code paths inspected on `main`.
- `/Users/jonathanoh/Dev/folio.love/.venv/bin/pytest --collect-only -q` reports 506 tests.
- The system `pytest` on this machine resolves to Python 3.9 and mis-collects this repo, so `.venv/bin/pytest` is the correct test entrypoint here.
