"""Stage 1½: Deterministic page inspection.

Runs after PDF normalization and before LLM analysis.  Produces a
``PageProfile`` per page that drives blank-page gating, render-DPI
metadata, and Set-of-Mark viability scoring.

All ``pypdfium2`` access is routed through ``pdfium_adapter``; this module
must NOT import ``pypdfium2`` directly.
"""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Named threshold constants ─────────────────────────────────────────

TEXT_MAX_VECTOR_COUNT = 50
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


# ── Data models ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoundedText:
    """A word with both PDF-space and pixel-space bounding boxes."""

    text: str
    bbox: tuple[float, float, float, float]         # PDF points, origin bottom-left
    pixel_bbox: tuple[float, float, float, float]    # pixel coords, origin top-left


@dataclass(frozen=True)
class PageProfile:
    """Deterministic inspection profile for a single PDF page."""

    page_number: int
    classification: str          # blank | image_blank | text | text_light | diagram | mixed | unsupported_diagram
    escalation_level: str        # simple | medium | dense
    word_count: int
    vector_count: int            # S1: renamed from vector_line_count
    char_count: int
    has_images: bool
    crop_box: tuple[float, float, float, float]
    rotation: int                # 0, 90, 180, 270
    render_dpi: int              # SF-2: metadata for downstream PRs (2+). Converter
                                 # still uses global image_dpi for rendering; per-page
                                 # DPI rendering is a PR 2 deliverable.
    bounded_texts: list[BoundedText]
    som_viable: bool             # SF-4: lexical-only viability (text overlap between
                                 # pypdfium2 and pdfplumber). Spatial bbox validation
                                 # is deferred to PR 2 rendered-overlay tests.


# ── Coordinate transforms (S7: accept primitives, not full PageProfile) ──

def pdf_to_pixel(
    pdf_x: float,
    pdf_y: float,
    crop_box: tuple[float, float, float, float],
    rotation: int,
    render_dpi: int,
) -> tuple[float, float]:
    """Convert PDF-space coordinates to pixel-space (top-left origin).

    Accepts transform primitives directly (S7 decoupling).

    MN-1 note: Transform correctness is validated algebraically via
    round-trip tests. Rendered-overlay tests (comparing pixel coordinates
    against actual Poppler-rendered images) are deferred to PR 2 when
    the image rendering infrastructure is available.

    Operation order:
    1. subtract crop-box origin
    2. apply page rotation
    3. scale from 72-DPI PDF points to render_dpi
    4. invert Y axis for top-left pixel coordinates
    """
    x = pdf_x - crop_box[0]
    y = pdf_y - crop_box[1]
    crop_width = crop_box[2] - crop_box[0]
    crop_height = crop_box[3] - crop_box[1]

    if rotation == 90:
        x, y = y, crop_width - x
    elif rotation == 180:
        x, y = crop_width - x, crop_height - y
    elif rotation == 270:
        x, y = crop_height - y, x

    scale = render_dpi / 72.0
    pixel_x = x * scale
    # After rotation, recalculate effective height for Y inversion
    if rotation in (90, 270):
        effective_height = crop_width
    else:
        effective_height = crop_height
    pixel_y = (effective_height - y) * scale
    return pixel_x, pixel_y


def pixel_to_pdf(
    pixel_x: float,
    pixel_y: float,
    crop_box: tuple[float, float, float, float],
    rotation: int,
    render_dpi: int,
) -> tuple[float, float]:
    """Convert pixel-space coordinates back to PDF-space.

    Accepts transform primitives directly (S7 decoupling).
    Exact inverse of ``pdf_to_pixel`` in reverse order.
    """
    crop_width = crop_box[2] - crop_box[0]
    crop_height = crop_box[3] - crop_box[1]
    scale = render_dpi / 72.0

    if rotation in (90, 270):
        effective_height = crop_width
    else:
        effective_height = crop_height

    # Reverse step 4 & 3: un-scale and un-invert Y
    x = pixel_x / scale
    y = effective_height - (pixel_y / scale)

    # Reverse step 2: undo rotation
    if rotation == 90:
        x, y = crop_width - y, x
    elif rotation == 180:
        x, y = crop_width - x, crop_height - y
    elif rotation == 270:
        x, y = y, crop_height - x

    # Reverse step 1: add back crop-box origin
    pdf_x = x + crop_box[0]
    pdf_y = y + crop_box[1]
    return pdf_x, pdf_y


# ── Inspection entrypoint ─────────────────────────────────────────────

def inspect_pages(pdf_path: Path) -> dict[int, PageProfile]:
    """Inspect a normalized PDF and return one ``PageProfile`` per page.

    Returns a dict keyed by 1-based page number.
    Per-page errors are caught and logged; failed pages get a degraded
    ``PageProfile`` with classification ``"text"`` so they are still
    processed by the LLM pipeline (B1 fix).

    Note (NEW-m3): document-level open failures (corrupt PDF, missing
    file, permission error) propagate uncaught.  This is intentional —
    a PDF that cannot be opened at all has no pages to degrade.  The
    caller (``FolioConverter.convert``) handles file-level exceptions.
    """
    from .pdfium_adapter import (
        open_pdfium,
        open_pdfplumber,
        page_count_pdfplumber,
        get_page_geometry_from_doc,
        get_page_word_boxes_from_doc,
        get_page_vector_image_counts_from_doc,
        get_pdfplumber_words_from_doc,
    )

    profiles: dict[int, PageProfile] = {}

    # B2 fix: open each document handle once for all pages
    with open_pdfplumber(pdf_path) as plumber_doc, \
         open_pdfium(pdf_path) as pdfium_doc:

        total_pages = page_count_pdfplumber(plumber_doc)

        for page_num in range(1, total_pages + 1):
            try:
                profiles[page_num] = _inspect_single_page(
                    pdfium_doc, plumber_doc, page_num
                )
            except Exception:
                # B1 fix: log warning and emit degraded profile
                logger.warning(
                    "Page %d inspection failed; falling back to degraded profile",
                    page_num,
                    exc_info=True,
                )
                profiles[page_num] = PageProfile(
                    page_number=page_num,
                    classification="text",       # safe fallback: LLM will still process
                    escalation_level="simple",
                    word_count=0,
                    vector_count=0,
                    char_count=0,
                    has_images=False,
                    crop_box=(0.0, 0.0, 612.0, 792.0),
                    rotation=0,
                    render_dpi=150,
                    bounded_texts=[],
                    som_viable=False,
                )

    return profiles


def _inspect_single_page(pdfium_doc, plumber_doc, page_num):
    """Inspect a single page. Raises on failure (caller catches)."""
    from .pdfium_adapter import (
        get_page_geometry_from_doc,
        get_page_word_boxes_from_doc,
        get_page_vector_image_counts_from_doc,
        get_pdfplumber_words_from_doc,
    )

    # Geometry from adapter (pypdfium2)
    crop_box, rotation = get_page_geometry_from_doc(pdfium_doc, page_num)

    # Words from adapter (pypdfium2)
    raw_words = get_page_word_boxes_from_doc(pdfium_doc, page_num)
    word_count = len(raw_words)
    char_count = sum(len(w.text) for w in raw_words)

    # Vector/image counts from pdfplumber
    vector_count, has_images = get_page_vector_image_counts_from_doc(
        plumber_doc, page_num
    )

    # BLK-3 fix: cross-validate with pdfplumber.  If pdfium returned 0
    # words but pdfplumber found text, use pdfplumber counts to prevent
    # a soft pdfium failure from misclassifying a text page as blank.
    pdfplumber_words = get_pdfplumber_words_from_doc(plumber_doc, page_num)
    if word_count == 0 and pdfplumber_words:
        logger.info(
            "Page %d: pdfium returned 0 words but pdfplumber found %d; "
            "using pdfplumber counts as fallback",
            page_num, len(pdfplumber_words),
        )
        word_count = len(pdfplumber_words)
        char_count = sum(len(w) for w in pdfplumber_words)

    # Classification
    classification = _classify_page(
        word_count, char_count, vector_count, has_images
    )

    # Escalation (m7: uses strict > thresholds; pages exactly at threshold
    # stay at the lower level — this is intentional for conservative escalation)
    escalation_level = _compute_escalation(word_count, vector_count)

    # Render DPI (S3: includes unsupported_diagram for future PR 4)
    render_dpi = 300 if classification in ("diagram", "mixed", "unsupported_diagram") else 150

    # Build bounded texts with pixel bboxes (after render_dpi is known)
    bounded_texts = _build_bounded_texts(raw_words, crop_box, rotation, render_dpi)

    # SoM viability (S2: pypdfium2-denominated coverage)
    pdfium_word_texts = [w.text for w in raw_words]
    som_viable = _compute_som_viability(pdfium_word_texts, pdfplumber_words)

    return PageProfile(
        page_number=page_num,
        classification=classification,
        escalation_level=escalation_level,
        word_count=word_count,
        vector_count=vector_count,
        char_count=char_count,
        has_images=has_images,
        crop_box=crop_box,
        rotation=rotation,
        render_dpi=render_dpi,
        bounded_texts=bounded_texts,
        som_viable=som_viable,
    )


# ── Classification ─────────────────────────────────────────────────────

def _classify_page(
    word_count: int,
    char_count: int,
    vector_count: int,
    has_images: bool,
) -> str:
    """Classify a page using the exact order from the spec.

    Order: blank → text → mixed → diagram → text_light fallback.
    (S5: short text pages fall to ``text_light`` instead of ``diagram``.)

    ``unsupported_diagram`` is not yet produced — deferred to PR 4 which
    adds the LLM-based unsupported-diagram classifier (S3).
    """
    # 1. blank — truly empty (no text, no vectors, no images)
    if (
        word_count == 0
        and char_count == 0
        and vector_count == 0
        and not has_images
    ):
        return "blank"

    # 1b. image_blank — raster-only page (BLK-2 fix).
    # Has embedded images but no text and no vectors.  Could be a
    # blank scan or a photo.  The converter combines this with histogram
    # blank detection to determine the final blank decision.
    if (
        has_images
        and word_count == 0
        and char_count == 0
        and vector_count == 0
    ):
        return "image_blank"

    # 2. text — substantial text, minimal vectors, no images
    # m8: removed redundant `char_count > 0` (always true when word_count > 50)
    if (
        vector_count < TEXT_MAX_VECTOR_COUNT
        and word_count > TEXT_MIN_WORDS
        and not has_images
    ):
        return "text"

    # 3. mixed — substantial text plus non-text structure
    if word_count > TEXT_MIN_WORDS and (vector_count > 0 or has_images):
        return "mixed"

    # 4. diagram — vector-heavy or image with low text
    if vector_count >= DIAGRAM_VECTOR_THRESHOLD:
        return "diagram"
    if (
        has_images
        and word_count < IMAGE_DIAGRAM_MAX_WORDS
        and char_count < IMAGE_DIAGRAM_MAX_CHARS
    ):
        return "diagram"
    if (
        vector_count > 0
        and word_count < IMAGE_DIAGRAM_MAX_WORDS
        and char_count < IMAGE_DIAGRAM_MAX_CHARS
    ):
        return "diagram"

    # 5. text_light — nonblank pages with some text but insufficient for
    #    "text" classification, AND no non-text structure. (SF-1 tightened)
    #    Renders at 150 DPI (not 300).
    if word_count > 0 and vector_count == 0 and not has_images:
        return "text_light"

    # 6. fallback for edge cases (e.g. has_images + moderate text below
    #    TEXT_MIN_WORDS but above IMAGE_DIAGRAM_MAX_WORDS)
    return "diagram"


# ── Escalation ─────────────────────────────────────────────────────────

def _compute_escalation(word_count: int, vector_count: int) -> str:
    """Compute escalation level from deterministic Stage 1 signals only.

    Uses strict ``>`` thresholds (m7): pages exactly at a threshold
    stay at the lower level for conservative escalation.
    """
    if word_count > DENSE_WORD_THRESHOLD or vector_count > DENSE_VECTOR_THRESHOLD:
        return "dense"
    if word_count > MEDIUM_WORD_THRESHOLD or vector_count > MEDIUM_VECTOR_THRESHOLD:
        return "medium"
    return "simple"


# ── Bounded text construction ──────────────────────────────────────────

def _build_bounded_texts(
    raw_words: list,
    crop_box: tuple[float, float, float, float],
    rotation: int,
    render_dpi: int,
) -> list[BoundedText]:
    """Build BoundedText list with pixel bboxes using the coordinate transform.

    S7 fix: passes transform primitives directly instead of constructing
    a throwaway PageProfile.
    """
    bounded: list[BoundedText] = []
    for w in raw_words:
        pixel_bbox = _transform_bbox(w.bbox, crop_box, rotation, render_dpi)
        bounded.append(BoundedText(text=w.text, bbox=w.bbox, pixel_bbox=pixel_bbox))
    return bounded


def _transform_bbox(
    pdf_bbox: tuple[float, float, float, float],
    crop_box: tuple[float, float, float, float],
    rotation: int,
    render_dpi: int,
) -> tuple[float, float, float, float]:
    """Transform a PDF-space bbox to pixel-space by converting all four corners.

    Returns (min_x, min_y, max_x, max_y) — normalized after rotation.
    """
    x0, y0, x1, y1 = pdf_bbox
    corners = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]
    pixel_corners = [
        pdf_to_pixel(cx, cy, crop_box, rotation, render_dpi)
        for cx, cy in corners
    ]

    px_xs = [pc[0] for pc in pixel_corners]
    px_ys = [pc[1] for pc in pixel_corners]

    return (min(px_xs), min(px_ys), max(px_xs), max(px_ys))


# ── Set-of-Mark viability ──────────────────────────────────────────────

def _normalize_word(word: str) -> str:
    """Normalize a word for SoM matching.

    Rules: lowercase, collapse internal whitespace, strip surrounding
    punctuation (including Unicode punctuation — m3 fix), keep
    alphanumeric content.
    """
    word = word.lower()
    word = re.sub(r"\s+", " ", word).strip()
    # Strip ASCII punctuation
    word = word.strip(".,;:!?\"'()[]{}<>/-—–")
    # Strip Unicode punctuation categories (Ps, Pe, Pi, Pf, Pd, Po) — m3
    while word and unicodedata.category(word[0]).startswith("P"):
        word = word[1:]
    while word and unicodedata.category(word[-1]).startswith("P"):
        word = word[:-1]
    return word


def _compute_som_viability(
    pdfium_words: list[str],
    pdfplumber_words: list[str],
) -> bool:
    """Compute SoM viability for a page.

    S2 fix: coverage is pypdfium2-denominated (matched / total_pypdfium2).
    When pypdfium2 over-segments, unmatched pypdfium2 words lower coverage,
    correctly signalling unreliable bboxes.

    S6 fix: uses hashed exact-match pass and early termination.

    Returns True only when coverage > SOM_MIN_COVERAGE.
    Returns False when either word list is empty (no positive evidence).
    """
    if not pdfplumber_words or not pdfium_words:
        return False

    norm_pdfium = [_normalize_word(w) for w in pdfium_words]
    norm_plumber = [_normalize_word(w) for w in pdfplumber_words]

    # S6: Build lookup set for O(1) exact matching
    plumber_counts: dict[str, int] = {}
    for w in norm_plumber:
        if w:
            plumber_counts[w] = plumber_counts.get(w, 0) + 1

    matched_count = 0
    fuzzy_candidates: list[str] = []

    # Pass 1: exact match via hash lookup (S6 optimization)
    for pf_word in norm_pdfium:
        if not pf_word:
            continue
        if plumber_counts.get(pf_word, 0) > 0:
            plumber_counts[pf_word] -= 1
            matched_count += 1
        else:
            fuzzy_candidates.append(pf_word)

    # S6: Early termination — if already above threshold, skip fuzzy
    non_empty_pdfium = sum(1 for w in norm_pdfium if w)
    if non_empty_pdfium > 0 and matched_count / non_empty_pdfium > SOM_MIN_COVERAGE:
        return True

    # Collect remaining unmatched pdfplumber words for fuzzy matching
    remaining_plumber = []
    for w, count in plumber_counts.items():
        remaining_plumber.extend([w] * count)

    # Pass 2: fuzzy match on residuals only (S6: reduced fuzzy set)
    fuzzy_matched = [False] * len(remaining_plumber)
    for pf_word in fuzzy_candidates:
        for j, pl_word in enumerate(remaining_plumber):
            if fuzzy_matched[j]:
                continue
            ratio = difflib.SequenceMatcher(None, pf_word, pl_word).ratio()
            if ratio >= SOM_MIN_FUZZY_RATIO:
                fuzzy_matched[j] = True
                matched_count += 1
                break

        # S6: Early termination check after each fuzzy match
        if non_empty_pdfium > 0 and matched_count / non_empty_pdfium > SOM_MIN_COVERAGE:
            return True

    # S2: pypdfium2-denominated coverage
    coverage = matched_count / non_empty_pdfium if non_empty_pdfium > 0 else 0.0
    return coverage > SOM_MIN_COVERAGE
