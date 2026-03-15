"""pypdfium2 adapter — all direct pypdfium2 imports live here.

Provides stable helpers for page geometry and bounded-text extraction.
Other pipeline modules must NOT import pypdfium2 directly.

Pin rationale (m5): pypdfium2==5.6.0 is pinned because the charbox API
and page geometry methods changed between 5.x minor versions.  The pin
ensures deterministic bbox output across CI and local environments.
Unpin only after verifying get_charbox/get_cropbox behaviour is stable
in the target release.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

try:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]
except ImportError as _exc:
    raise ImportError(
        "pypdfium2 is required for page inspection. "
        "Install with: pip install pypdfium2==5.6.0"
    ) from _exc


@dataclass(frozen=True)
class PdfiumWordBox:
    """Raw word with PDF-space bounding box from pypdfium2."""

    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1) PDF points, bottom-left origin


# ── Batch context managers (B2 fix) ───────────────────────────────────

@contextlib.contextmanager
def open_pdfium(pdf_path: Path) -> Generator:
    """Context manager for a pypdfium2 document handle.

    Keeps the document open for the duration of the block, avoiding
    repeated open/close cycles when inspecting multiple pages.
    """
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        yield doc
    finally:
        doc.close()


@contextlib.contextmanager
def open_pdfplumber(pdf_path: Path) -> Generator:
    """Context manager for a pdfplumber document handle."""
    import pdfplumber
    pdf = pdfplumber.open(str(pdf_path))
    try:
        yield pdf
    finally:
        pdf.close()


def page_count_pdfplumber(plumber_doc) -> int:
    """Return the number of pages from an already-open pdfplumber doc."""
    return len(plumber_doc.pages)


# ── Geometry ──────────────────────────────────────────────────────────

def get_page_geometry_from_doc(
    doc, page_number: int
) -> tuple[tuple[float, float, float, float], int]:
    """Return (crop_box, rotation) for a 1-based *page_number*.

    Accepts an already-open pypdfium2 document handle.
    crop_box is (x0, y0, x1, y1) in PDF points.
    rotation is one of 0, 90, 180, 270.
    """
    page = doc[page_number - 1]
    rotation = page.get_rotation()

    # Fallback chain: CropBox → BBox → MediaBox
    try:
        crop_box = page.get_cropbox(fallback_ok=True)
    except Exception:
        crop_box = None

    if crop_box is None or _is_degenerate(crop_box):
        try:
            crop_box = page.get_bbox()
        except Exception:
            crop_box = None

    if crop_box is None or _is_degenerate(crop_box):
        try:
            crop_box = page.get_mediabox(fallback_ok=True)
        except Exception:
            crop_box = (0.0, 0.0, 612.0, 792.0)  # US Letter fallback

    return tuple(float(v) for v in crop_box), rotation  # type: ignore[return-value]


# ── Word extraction ──────────────────────────────────────────────────

def get_page_word_boxes_from_doc(
    doc, page_number: int
) -> list[PdfiumWordBox]:
    """Extract words with PDF-space bounding boxes for a 1-based *page_number*.

    Accepts an already-open pypdfium2 document handle.
    Groups contiguous non-whitespace characters from the PDF text stream,
    building each word's bbox by unioning its character boxes.
    """
    page = doc[page_number - 1]
    textpage = page.get_textpage()

    n_chars = textpage.count_chars()
    if n_chars == 0:
        return []

    full_text = textpage.get_text_range(0, n_chars)

    words: list[PdfiumWordBox] = []
    current_chars: list[str] = []
    current_boxes: list[tuple[float, float, float, float]] = []

    for idx in range(n_chars):
        char = full_text[idx] if idx < len(full_text) else ""

        if char.isspace() or char == "":
            # Flush current word (S4: guard against empty boxes)
            if current_chars:
                word_text = "".join(current_chars).strip()
                if word_text and current_boxes:
                    bbox = _union_boxes(current_boxes)
                    words.append(PdfiumWordBox(text=word_text, bbox=bbox))
                current_chars = []
                current_boxes = []
            continue

        try:
            charbox = textpage.get_charbox(idx)
            box = (float(charbox[0]), float(charbox[1]),
                   float(charbox[2]), float(charbox[3]))
            current_chars.append(char)
            # NEW-m1: Skip degenerate charboxes (e.g. (0,0,0,0) from
            # broken font metrics) — accumulate text but not the bbox
            if not _is_degenerate(box):
                current_boxes.append(box)
        except Exception:
            # Character has no geometry — still accumulate text
            current_chars.append(char)

    # Flush last word
    if current_chars:
        word_text = "".join(current_chars).strip()
        if word_text and current_boxes:
            bbox = _union_boxes(current_boxes)
            words.append(PdfiumWordBox(text=word_text, bbox=bbox))

    return words


# ── pdfplumber helpers ────────────────────────────────────────────────

def get_page_vector_image_counts_from_doc(
    plumber_doc, page_number: int
) -> tuple[int, bool]:
    """Return (vector_count, has_images) from an already-open pdfplumber doc.

    vector_count = len(rects) + len(lines) + len(curves)
    has_images = bool(page.images)
    """
    if page_number < 1 or page_number > len(plumber_doc.pages):
        return 0, False
    page = plumber_doc.pages[page_number - 1]
    rects = page.rects or []
    lines = page.lines or []
    curves = page.curves or []
    images = page.images or []
    vector_count = len(rects) + len(lines) + len(curves)
    return vector_count, bool(images)


def get_pdfplumber_words_from_doc(plumber_doc, page_number: int) -> list[str]:
    """Extract words from an already-open pdfplumber doc for SoM viability."""
    if page_number < 1 or page_number > len(plumber_doc.pages):
        return []
    page = plumber_doc.pages[page_number - 1]
    raw_words = page.extract_words() or []
    return [w["text"] for w in raw_words if w.get("text", "").strip()]


# ── internal helpers ──────────────────────────────────────────────────

def _union_boxes(
    boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    """Union a list of (x0, y0, x1, y1) boxes."""
    if not boxes:
        return (0.0, 0.0, 0.0, 0.0)
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return (x0, y0, x1, y1)


def _is_degenerate(box: tuple) -> bool:
    """Check if a box has zero or negative area."""
    if box is None or len(box) < 4:
        return True
    return (box[2] - box[0]) <= 0 or (box[3] - box[1]) <= 0
