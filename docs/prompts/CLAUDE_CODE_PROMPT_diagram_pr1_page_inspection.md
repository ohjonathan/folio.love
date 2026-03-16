---
id: claude_code_prompt_diagram_pr1_page_inspection
type: atom
status: draft
ontos_schema: 2.2
curation_level: 0
generated_by: codex
created: 2026-03-14
---

# Implementation Prompt: Diagram Extraction PR 1 - Page Inspection, Blank Fix, Coordinates, and Set-of-Mark Validation

**For:** Developer Agent Team (CA lead + spawned developers)  
**Approved proposal:** `docs/proposals/diagram-extraction-proposal.md`  
**Roadmap:** `docs/product/04_Implementation_Roadmap.md`  
**Ontology:** `docs/architecture/Folio_Ontology_Architecture.md`  
**Strategic memo:** `docs/product/strategic_direction_memo.md`  
**Branch:** `codex/diagram-pr1-page-inspection` from `codex/grounding-reviewability`  
**Test command:** `.venv/bin/python -m pytest tests/ -v`  
**Commit format:** `feat(diagrams): description`  
**PR title:** `feat: add page inspection foundation for diagram extraction`

---

## Agent Team Activation

This requires an agent team.

1. The CA lead reads this prompt end-to-end, decomposes the work, and owns final verification.
2. Developers implement in the order defined below. Do not parallelize dependent refactors blindly; PR 1 crosses dependency management, PDF inspection, geometry, converter orchestration, and tests.
3. The CA lead verifies each slice with the targeted tests, then runs the full suite before opening the PR.

---

## Task Context

### What to Build

Build the PR 1 foundation layer for diagram extraction. This PR adds deterministic page inspection that runs **before** existing LLM analysis and fixes the active bug where sparse diagram pages are incorrectly treated as blank and overwritten with `SlideAnalysis.pending()`.

This PR does **not** change LLM prompts, LLM pass behavior, markdown rendering, frontmatter rendering, registry behavior, or per-page image extraction DPI in runtime. It adds inspection infrastructure and makes inspection authoritative for blank-page gating.

### Why This PR Matters

The current PDF path has an active destructive bug:

- `folio/converter.py` calls `images.extract_with_metadata(...)`
- it derives `blank_slides = {r.slide_num for r in image_results if r.is_blank}`
- after `analysis.analyze_slides(...)`, it loops over that set and force-replaces those analyses with `SlideAnalysis.pending()`
- the same set is also passed to `analyze_slides_deep(skip_slides=blank_slides)` and `assess_review_state(... known_blank_slides=blank_slides)`

Because `ImageResult.is_blank` comes from the histogram heuristic in `folio/pipeline/images.py`, a sparse line-on-white diagram can be destroyed even when the LLM returned a valid analysis. PR 1 fixes that by making `PageProfile.classification == "blank"` the authoritative signal instead.

### Scope Boundaries

Keep PR 1 narrow.

- Add a new deterministic inspection stage over normalized PDFs.
- Add `PageProfile`, `BoundedText`, coordinate transforms, and Set-of-Mark viability measurement.
- Make converter blank override and Pass 2 skip logic use inspection-derived blankness.
- Keep histogram blank detection in `images.py`, but downgrade it to diagnostic metadata only.
- Add tests and programmatic PDF fixtures.

### What Not to Build

- No LLM prompt changes.
- No `DiagramAnalysis` or schema expansion beyond inspection data structures.
- No new markdown, frontmatter, registry, or CLI output surfaces for diagrams.
- No runtime image-strategy changes for Set-of-Mark or tiles.
- No per-page mixed-DPI runtime rendering yet.
- No provider changes, retry changes, cache-key changes, or Mermaid work.
- No `unsupported_diagram` detector beyond reserving the classification value.

### Rollout Constraint

Do not turn this into a diagram-pipeline PR. PR 1 is a deterministic inspection and blank-fix PR. The existing slide-analysis path must remain intact except for the authoritative blank-page decision source.

---

## Read Before Writing

Read these in order before touching code:

1. `docs/proposals/diagram-extraction-proposal.md`
   - Focus on PR 1, Stage 1 page inspection, coordinate transform, and blank-fix sections.
2. `docs/product/04_Implementation_Roadmap.md`
   - Focus on the Diagram Extraction section and PR 1 summary.
3. `docs/architecture/Folio_Ontology_Architecture.md`
   - Focus on reviewability/trust sections; they explain why destructive overrides are unacceptable.
4. `docs/product/strategic_direction_memo.md`
5. `folio/converter.py`
6. `folio/pipeline/images.py`
7. `folio/pipeline/text.py`
8. `folio/pipeline/analysis.py`
9. `tests/test_converter_integration.py`
10. `tests/test_images.py`
11. `tests/test_grounding.py`
12. `pyproject.toml`

---

## Current Codebase Reality

### Current Pipeline Shape

Current runtime flow in `FolioConverter.convert()` is:

1. `normalize.to_pdf(...)`
2. `images.extract_with_metadata(...)`
3. `text.extract_structured(...)`
4. `analysis.analyze_slides(...)`
5. histogram-derived blank override to `SlideAnalysis.pending()`
6. optional `analysis.analyze_slides_deep(... skip_slides=blank_slides ...)`
7. `analysis.assess_review_state(... known_blank_slides=blank_slides ...)`

Inspection does not exist yet.

### Current Blank Detection Bug

The active bug is not in `analysis.py`. It is in the converter’s control flow.

- `folio/pipeline/images.py` computes `ImageResult.is_blank` via `_is_mostly_blank()` using a grayscale histogram.
- `folio/converter.py` treats that image-only heuristic as authoritative blankness.
- Sparse diagrams can be mostly white in pixel distribution but still contain meaningful vector content or bounded PDF text.

PR 1 must make inspection authoritative for:

- post-pass-1 pending override
- Pass 2 skip gating
- reviewability `known_blank_slides`

### Current Test Baseline

As of March 14, 2026, the repo currently collects **556 tests**, not the older 506 count mentioned in earlier planning material. Use the current suite as the regression baseline.

---

## Target Behavior and Interfaces

### New Data Models

Add these dataclasses in `folio/pipeline/inspect.py`:

```python
@dataclass(frozen=True)
class BoundedText:
    text: str
    bbox: tuple[float, float, float, float]  # PDF points, origin bottom-left
    pixel_bbox: tuple[float, float, float, float]  # pixel coords, origin top-left


@dataclass(frozen=True)
class PageProfile:
    page_number: int
    classification: str          # blank | text | diagram | mixed | unsupported_diagram
    escalation_level: str        # simple | medium | dense
    word_count: int
    vector_line_count: int
    char_count: int
    has_images: bool
    crop_box: tuple[float, float, float, float]
    rotation: int                # 0, 90, 180, 270
    render_dpi: int              # 300 for diagram/mixed, 150 for text/blank
    bounded_texts: list[BoundedText]
    som_viable: bool
```

You may add internal helper dataclasses, but preserve these public fields and semantics.

### New Inspection API

Add `inspect_pages(pdf_path: Path) -> dict[int, PageProfile]` in `folio/pipeline/inspect.py`.

The function must inspect the normalized PDF and return one profile per 1-based page number.

### Coordinate Helpers

Also in `folio/pipeline/inspect.py`, add:

```python
def pdf_to_pixel(pdf_x: float, pdf_y: float, page: PageProfile) -> tuple[float, float]: ...
def pixel_to_pdf(pixel_x: float, pixel_y: float, page: PageProfile) -> tuple[float, float]: ...
```

These must be full inverses within floating-point tolerance.

### Adapter Boundary

Add `folio/pipeline/pdfium_adapter.py`.

All direct `pypdfium2` imports and API calls must stay in this module.

Required stable helper:

```python
get_page_text_with_boxes(pdf_path, page_number) -> list[BoundedText]
```

To make the implementation practical, you may extend this with optional keyword-only parameters and internal helpers, but:

- the zero-extra-args form above must remain valid
- `inspect.py` must not import `pypdfium2` directly
- `inspect.py` may lazy-import adapter helpers to avoid circular imports

Add internal helpers as needed, for example:

- `get_page_geometry(...) -> tuple[crop_box, rotation]`
- `get_page_word_boxes_pdf(...) -> list[PdfiumWordBox]`

Use those internal helpers from `inspect_pages()` so final `pixel_bbox` values are computed after classification determines `render_dpi`.

---

## Classification and Escalation Rules

### Named Constants

Define named constants in `inspect.py`. Do not inline thresholds.

Minimum required constants:

```python
TEXT_MAX_VECTOR_LINES = 50
TEXT_MIN_WORDS = 50
IMAGE_DIAGRAM_MAX_WORDS = 50
IMAGE_DIAGRAM_MAX_CHARS = 200
DIAGRAM_VECTOR_THRESHOLD = 50
MEDIUM_WORD_THRESHOLD = 30
MEDIUM_VECTOR_THRESHOLD = 200
DENSE_WORD_THRESHOLD = 80
DENSE_VECTOR_THRESHOLD = 500
SOM_MIN_COVERAGE = 0.80
SOM_MIN_FUZZY_RATIO = 0.85
```

### Resolve the Sparse-Diagram Contradiction Explicitly

The brief’s original `blank` threshold (`vector_line_count < 5`) would still destroy sparse diagrams. Do **not** implement that literally.

For PR 1, use this corrected logic:

- `blank`: no bounded words, no chars, no images, and **no vector primitives**
- any vector primitive or bounded text makes the page **nonblank**
- a low-text page with vector primitives classifies as `diagram`, not `blank`

### Classification Order

Use this exact order to avoid edge-case drift:

1. `blank`
   - `word_count == 0`
   - `char_count == 0`
   - `vector_line_count == 0`
   - `has_images is False`
2. `text`
   - `char_count > 0`
   - `vector_line_count < TEXT_MAX_VECTOR_LINES`
   - `word_count > TEXT_MIN_WORDS`
   - `has_images is False`
3. `mixed`
   - substantial text plus non-text structure
   - implement as: `word_count > TEXT_MIN_WORDS` and `(vector_line_count > 0 or has_images)`
4. `diagram`
   - `vector_line_count >= DIAGRAM_VECTOR_THRESHOLD`
   - or `(has_images and word_count < IMAGE_DIAGRAM_MAX_WORDS and char_count < IMAGE_DIAGRAM_MAX_CHARS)`
   - or `(vector_line_count > 0 and word_count < IMAGE_DIAGRAM_MAX_WORDS and char_count < IMAGE_DIAGRAM_MAX_CHARS)`
5. fallback nonblank pages
   - classify as `diagram`

Reserve `unsupported_diagram` as a valid enum value, but do not auto-detect it in PR 1. No page should be reclassified into `unsupported_diagram` yet.

### Escalation

Escalation must come only from Stage 1 deterministic signals:

- `dense` if `word_count > DENSE_WORD_THRESHOLD` or `vector_line_count > DENSE_VECTOR_THRESHOLD`
- `medium` if `word_count > MEDIUM_WORD_THRESHOLD` or `vector_line_count > MEDIUM_VECTOR_THRESHOLD`
- otherwise `simple`

Do not use any LLM output for escalation decisions.

### Render DPI

Set `PageProfile.render_dpi` as:

- `300` for `diagram` and `mixed`
- `150` for `text` and `blank`

This is future-facing metadata only in PR 1. Do **not** change the converter’s actual image extraction behavior yet.

---

## Geometry and Text Extraction Rules

### Single Geometry Authority

All coordinate extraction comes from `pypdfium2`, adapter-wrapped. `pdfplumber` is only for counts and comparison signals.

### pypdfium2 Word Grouping

Implement bounded-word extraction in the adapter by grouping contiguous non-whitespace characters from:

- `PdfTextPage.get_text_range()`
- `PdfTextPage.get_charbox()`

Rules:

- split on whitespace characters only
- preserve reading order from the PDF text stream
- build each word bbox by unioning its character boxes
- discard empty/whitespace-only words
- do not use `pdfplumber` geometry as the source of truth

### Crop Box and Rotation

Read page geometry from the adapter:

- `crop_box` from PDF metadata, using fallback behavior if CropBox is unset
- `rotation` as one of `0`, `90`, `180`, `270`

Recommended fallback order:

1. `page.get_cropbox(fallback_ok=True)`
2. if unavailable or degenerate, `page.get_bbox()`
3. if still needed, `page.get_mediabox(fallback_ok=True)`

### Coordinate Transform

Implement `pdf_to_pixel()` with this exact operation order:

1. subtract crop-box origin
2. apply page rotation
3. scale from 72-DPI PDF points to `render_dpi`
4. invert Y axis for top-left pixel coordinates

Reference implementation:

```python
def pdf_to_pixel(pdf_x: float, pdf_y: float, page: PageProfile) -> tuple[float, float]:
    x = pdf_x - page.crop_box[0]
    y = pdf_y - page.crop_box[1]
    crop_width = page.crop_box[2] - page.crop_box[0]
    crop_height = page.crop_box[3] - page.crop_box[1]

    if page.rotation == 90:
        x, y = y, crop_width - x
    elif page.rotation == 180:
        x, y = crop_width - x, crop_height - y
    elif page.rotation == 270:
        x, y = crop_height - y, x

    scale = page.render_dpi / 72.0
    pixel_x = x * scale
    pixel_y = (crop_height - y) * scale
    return pixel_x, pixel_y
```

`pixel_to_pdf()` must be the exact inverse in reverse order.

### Bounding Boxes

For each `BoundedText`:

- `bbox` is in PDF points
- `pixel_bbox` is computed by transforming **all four** PDF-space corners and then normalizing `(min_x, min_y, max_x, max_y)`

Do not assume transformed lower-left and upper-right remain ordered after rotation.

---

## Set-of-Mark Viability

### Comparison Sources

Per page, compare:

- `pypdfium2` bounded words from the adapter
- `pdfplumber page.extract_words()`

### Matching Algorithm

Use normalized greedy matching.

Normalization rules:

- lowercase
- collapse internal whitespace
- strip surrounding punctuation
- keep alphanumeric content

Matching rules:

1. exact normalized match first
2. if no exact match, allow `difflib.SequenceMatcher(...).ratio() >= SOM_MIN_FUZZY_RATIO`
3. each `pypdfium2` word can match at most one `pdfplumber` word

Coverage:

```python
matched_pdfplumber_words / total_pdfplumber_words
```

Set:

- `som_viable = True` only when coverage is strictly greater than `SOM_MIN_COVERAGE`
- `som_viable = False` when `pdfplumber` yields zero words, because there is no positive evidence that box coverage is reliable on that page

This is a per-page signal only. The corpus-wide verdict remains a manual PR 1 validation output.

---

## File-by-File Instructions

### 1. `pyproject.toml`

Update dependencies:

- add runtime dependency `pypdfium2==5.6.0`
- add `reportlab>=4.4`
- add `pypdf>=6.8`

Placement:

- `pypdfium2==5.6.0` in `[project.dependencies]`
- `reportlab` and `pypdf` in `[project.optional-dependencies].dev`

Do not add new heavyweight PDF/image libraries.

### 2. `folio/pipeline/pdfium_adapter.py`

Create this module.

Requirements:

- all `pypdfium2` imports live here
- raise a clear actionable error if `pypdfium2` is unavailable
- support 1-based page numbers
- implement word grouping from `get_text_range()` + `get_charbox()`
- expose the stable `get_page_text_with_boxes(...)` entrypoint
- expose whatever internal geometry/text helpers `inspect.py` needs

Implementation guidance:

- keep the module thin
- do not put classification logic here
- do not import `pdfplumber` here
- avoid circular imports by importing `BoundedText` lazily or by keeping `inspect.py`’s adapter import function-local

### 3. `folio/pipeline/inspect.py`

Create this module.

Required contents:

- `BoundedText`
- `PageProfile`
- named constants
- `pdf_to_pixel()`
- `pixel_to_pdf()`
- `inspect_pages()`
- internal helpers for:
  - classification
  - escalation
  - SoM viability
  - word normalization/matching
  - bbox corner transformation

Implementation guidance:

- use `pdfplumber` only for `chars`, `extract_words()`, `rects`, `lines`, `curves`, and `images`
- `vector_line_count = len(rects) + len(lines) + len(curves)`
- `has_images = bool(page.images)`
- `word_count` must come from adapter-produced bounded words
- build `PageProfile.bounded_texts` only after `render_dpi` is known

### 4. `folio/converter.py`

Integrate inspection immediately after normalization and before image extraction.

Required control-flow change:

1. call `page_profiles = inspect.inspect_pages(pdf_path)`
2. derive:

```python
blank_slides = {
    page_num for page_num, profile in page_profiles.items()
    if profile.classification == "blank"
}
```

3. keep image extraction unchanged for PR 1
4. after `analysis.analyze_slides(...)`, override with `pending()` only for that inspection-derived blank set
5. pass that same set into:
   - `analysis.analyze_slides_deep(... skip_slides=blank_slides ...)`
   - `analysis.assess_review_state(... known_blank_slides=blank_slides ...)`

Do **not** use `ImageResult.is_blank` as authoritative control flow anymore.

Optional but acceptable:

- keep histogram blank metadata for logging/debug only
- log disagreements between image heuristic blankness and inspection blankness at `DEBUG` level

Not acceptable:

- deleting `ImageResult.is_blank`
- changing actual image extraction DPI
- threading `PageProfile` into frontmatter/markdown in PR 1

### 5. `folio/pipeline/images.py`

Do not change runtime blank-detection math unless absolutely necessary for comments/docstrings/tests.

Allowed:

- a short docstring/comment clarifying that histogram blankness is diagnostic and not authoritative for converter override decisions

Do not remove `_is_mostly_blank()` or the current metadata shape.

### 6. `tests/test_inspect.py`

Create this new test module.

Use generated PDF fixtures, not checked-in binary fixtures.

Use:

- `reportlab` to draw text, lines, rectangles, curves, and optional embedded raster images
- `pypdf` to apply rotation and CropBox changes after generation

Cover:

- `pdf_to_pixel` for standard, 90, 180, 270, cropbox-offset, and rotated+cropbox pages
- `pixel_to_pdf` round-trip within tolerance
- blank page classification
- text-heavy page classification
- sparse diagram classification
- dense diagram classification
- mixed page classification
- threshold edge behavior
- escalation `simple`, `medium`, `dense`
- adapter extraction returning non-empty PDF-space boxes
- pixel bboxes falling within rendered page bounds
- SoM viability true and false cases

Implementation guidance:

- keep fixture generators local to this file or in small local helper functions
- use temporary directories
- generate at least one embedded-image PDF to cover `has_images`
- keep expectations robust to minor float differences using `pytest.approx`

### 7. `tests/test_converter_integration.py`

Update existing blank-path tests to patch inspection rather than image blankness.

Specifically:

- patch `folio.converter.inspect.inspect_pages`
- keep `ImageResult.is_blank` out of the authoritative assertions

Required test updates:

1. genuine blank page still becomes `pending()`
   - `inspect_pages()` marks it `blank`
2. blank pages do not create partial-analysis review flags
   - same semantics as today, but inspection-driven
3. new regression test: sparse diagram page survives
   - set `ImageResult.is_blank=True` for the sparse page to simulate histogram false positive
   - set `inspect_pages()` classification for that page to `diagram`
   - mock pass-1 analysis for that page as a valid non-pending analysis
   - assert converter does **not** replace it with `pending()`
   - assert the page is not excluded via blank gating in reviewability

### 8. Existing Tests

Keep existing image-blank tests unless a comment needs clarification.

Do not weaken or delete:

- `tests/test_images.py`
- `tests/test_grounding.py` blank/reviewability expectations

If any tests need updates, they should reflect the new source of truth for blankness, not remove coverage.

---

## Implementation Order

Follow this order:

1. Update `pyproject.toml` dependencies.
2. Create `pdfium_adapter.py`.
3. Create `inspect.py` with transforms, classification, escalation, and SoM viability.
4. Integrate inspection into `converter.py`.
5. Add `tests/test_inspect.py`.
6. Update `tests/test_converter_integration.py`.
7. Run targeted tests after each major slice.
8. Run the full suite before final review.

Do not start with converter wiring. The transform and adapter must exist first.

---

## Smoke Test Commands

Run these before opening the PR:

```bash
.venv/bin/python -m pytest tests/test_inspect.py -v
.venv/bin/python -m pytest tests/test_converter_integration.py -v -k "blank or inspect"
.venv/bin/python -m pytest tests/ -v
```

If any dependency installation is needed after `pyproject.toml` changes, do that before running tests.

---

## Manual Validation Output

After code is complete, perform a manual post-implementation validation on 5-10 real corpus PDFs supplied outside the automated suite.

Use `inspect_pages()` directly. No new CLI is needed in PR 1.

For each PDF, record:

- total pages
- pages classified as `diagram` or `mixed`
- average `som_viable` rate on those pages
- notable failure modes

Final output to the orchestrator:

- `SoM viable for PR 2`
- or `SoM not viable - PR 2 uses tiles fallback`

This verdict is a required PR 1 outcome even though it is not a new runtime feature.

---

## Verification Checklist

Do not open the PR until all are true:

- `pypdfium2` is adapter-wrapped and pinned
- `inspect_pages()` returns profiles for every page
- sparse vector diagrams are never classified `blank`
- converter blank override uses inspection-derived blankness only
- genuine blank pages still become `pending()`
- Pass 2 skip set uses inspection-derived blankness
- reviewability known-blank semantics still hold
- transform tests cover rotation and CropBox together
- SoM viability tests cover both pass and fail cases
- full test suite passes

---

## What Not to Do

- Do not change `ANALYSIS_PROMPT`, `DEPTH_PROMPT`, or any provider adapter behavior.
- Do not add diagram-specific frontmatter or markdown output.
- Do not add new CLI commands.
- Do not make `unsupported_diagram` active in runtime classification.
- Do not replace `images.extract_with_metadata()` with per-page rendering.
- Do not rework registry or version tracking in this PR.
- Do not silently change the current slide-analysis contract for non-diagram pages.

The only intended behavior change in current runtime is that inspection, not histogram blankness, decides which pages are truly blank.
