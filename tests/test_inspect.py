"""Tests for folio.pipeline.inspect — page inspection, transforms, and SoM viability.

Uses reportlab to generate PDF fixtures programmatically and pypdf for
rotation/CropBox manipulation.  No checked-in binary fixtures.
"""

import math
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from folio.pipeline.inspect import (
    BoundedText,
    PageProfile,
    pdf_to_pixel,
    pixel_to_pdf,
    inspect_pages,
    _classify_page,
    _compute_escalation,
    _normalize_word,
    _compute_som_viability,
    TEXT_MAX_VECTOR_COUNT,
    TEXT_MIN_WORDS,
    IMAGE_DIAGRAM_MAX_WORDS,
    IMAGE_DIAGRAM_MAX_CHARS,
    DIAGRAM_VECTOR_THRESHOLD,
    MEDIUM_WORD_THRESHOLD,
    MEDIUM_VECTOR_THRESHOLD,
    DENSE_WORD_THRESHOLD,
    DENSE_VECTOR_THRESHOLD,
    SOM_MIN_COVERAGE,
    SOM_MIN_FUZZY_RATIO,
)


# ── Fixture helpers ────────────────────────────────────────────────────

def _make_blank_pdf(path: Path) -> None:
    """Generate a single-page blank PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)
    c.showPage()
    c.save()


def _make_text_heavy_pdf(path: Path, word_count: int = 200) -> None:
    """Generate a single-page PDF with substantial text."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)
    text = " ".join(["word"] * word_count)
    # Write text in lines
    t = c.beginText(72, 700)
    t.setFont("Helvetica", 10)
    words = text.split()
    line = ""
    for w in words:
        if len(line) + len(w) > 80:
            t.textLine(line)
            line = w
        else:
            line = f"{line} {w}" if line else w
    if line:
        t.textLine(line)
    c.drawText(t)
    c.showPage()
    c.save()


def _make_sparse_diagram_pdf(path: Path) -> None:
    """Generate a page with vector lines but very few words — sparse diagram."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)
    # A few vector lines — enough to be meaningful but sparse
    for i in range(10):
        c.line(100, 100 + i * 50, 400, 100 + i * 50)
    # Just a few words
    c.drawString(100, 750, "Figure 1")
    c.showPage()
    c.save()


def _make_dense_diagram_pdf(path: Path) -> None:
    """Generate a page with many vector primitives — dense diagram.

    Uses rect() which pdfplumber reliably counts as rects.
    Need > DENSE_VECTOR_THRESHOLD (500) total rects+lines+curves.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)
    # Many thin rectangles — pdfplumber counts these as rects
    for i in range(520):
        c.rect(50 + (i % 50) * 10, 50 + (i // 50) * 60, 8, 50)
    # Few words
    c.drawString(100, 750, "Chart")
    c.showPage()
    c.save()


def _make_mixed_pdf(path: Path) -> None:
    """Generate a page with substantial text AND vector primitives.

    Uses rect() so pdfplumber sees them as vector elements.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)
    # Substantial text (> TEXT_MIN_WORDS = 50)
    t = c.beginText(72, 700)
    t.setFont("Helvetica", 10)
    for i in range(80):
        t.textLine(f"This is line {i} with some words to make it substantial enough for text classification")
    c.drawText(t)
    # Vector elements — rects pdfplumber reliably picks up
    # Need >= TEXT_MAX_VECTOR_COUNT (50) to push past 'text' classification
    for i in range(60):
        c.rect(100, 20 + i * 2, 400, 1)
    c.showPage()
    c.save()


def _make_image_pdf(path: Path) -> None:
    """Generate a single-page PDF with an embedded raster image and few words."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from PIL import Image as PILImage
    import io

    c = canvas.Canvas(str(path), pagesize=letter)

    # Create a small in-memory image
    img = PILImage.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # Save to temp file, embed in PDF
    import tempfile as tf
    with tf.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        tmp_img.write(img_bytes.getvalue())
        tmp_img_path = tmp_img.name

    c.drawImage(tmp_img_path, 100, 400, width=200, height=200)
    c.drawString(100, 750, "Photo caption")
    c.showPage()
    c.save()

    Path(tmp_img_path).unlink(missing_ok=True)


def _make_multipage_pdf(path: Path) -> None:
    """Generate a 3-page PDF: blank, text, diagram."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=letter)

    # Page 1: blank
    c.showPage()

    # Page 2: text heavy
    t = c.beginText(72, 700)
    t.setFont("Helvetica", 10)
    for i in range(80):
        t.textLine(f"Text line {i} with enough words to classify as text content here")
    c.drawText(t)
    c.showPage()

    # Page 3: diagram (lines only)
    for i in range(60):
        c.line(50, 50 + i * 10, 550, 50 + i * 10)
    c.drawString(200, 750, "Diagram")
    c.showPage()

    c.save()


def _make_rotated_pdf(path: Path, rotation: int) -> None:
    """Generate a single-page PDF rotated by *rotation* degrees."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    base_path = path.with_suffix(".base.pdf")
    c = canvas.Canvas(str(base_path), pagesize=letter)
    c.drawString(100, 700, "Rotated text")
    c.showPage()
    c.save()

    # Apply rotation via pypdf
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(base_path))
    writer = PdfWriter()
    page = reader.pages[0]
    page.rotate(rotation)
    writer.add_page(page)
    with open(str(path), "wb") as f:
        writer.write(f)

    base_path.unlink()


def _make_cropbox_pdf(path: Path, crop_box: tuple) -> None:
    """Generate a single-page PDF with a custom CropBox."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    base_path = path.with_suffix(".base.pdf")
    c = canvas.Canvas(str(base_path), pagesize=letter)
    c.drawString(150, 500, "Cropped text")
    c.showPage()
    c.save()

    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, FloatObject, NameObject

    reader = PdfReader(str(base_path))
    writer = PdfWriter()
    page = reader.pages[0]
    page[NameObject("/CropBox")] = ArrayObject(
        [FloatObject(crop_box[0]), FloatObject(crop_box[1]),
         FloatObject(crop_box[2]), FloatObject(crop_box[3])]
    )
    writer.add_page(page)
    with open(str(path), "wb") as f:
        writer.write(f)

    base_path.unlink()


# ── Coordinate transform tests (S7: functions now accept primitives) ──

class TestPdfToPixel:
    """pdf_to_pixel for standard, rotated, and CropBox-offset pages."""

    def test_standard_origin(self):
        px, py = pdf_to_pixel(0, 0, crop_box=(0, 0, 612, 792), rotation=0, render_dpi=150)
        scale = 150 / 72.0
        assert px == pytest.approx(0.0)
        assert py == pytest.approx(792 * scale)

    def test_standard_top_right(self):
        px, py = pdf_to_pixel(612, 792, crop_box=(0, 0, 612, 792), rotation=0, render_dpi=150)
        scale = 150 / 72.0
        assert px == pytest.approx(612 * scale)
        assert py == pytest.approx(0.0)

    def test_rotation_90(self):
        # After 90° rotation: (x, y) -> (y, W - x)
        px, py = pdf_to_pixel(0, 0, crop_box=(0, 0, 612, 792), rotation=90, render_dpi=150)
        # x=0, y=0; after rotation: x'=0, y'=612-0=612
        # effective_height after 90° = crop_width = 612
        # pixel_y = (612 - 612) * scale = 0
        assert px == pytest.approx(0.0)
        assert py == pytest.approx(0.0)

    def test_rotation_180(self):
        px, py = pdf_to_pixel(0, 0, crop_box=(0, 0, 612, 792), rotation=180, render_dpi=150)
        scale = 150 / 72.0
        # x=0, y=0; after 180°: x'=612, y'=792
        # pixel_y = (792 - 792) * scale = 0
        assert px == pytest.approx(612 * scale)
        assert py == pytest.approx(0.0)

    def test_rotation_270(self):
        px, py = pdf_to_pixel(0, 0, crop_box=(0, 0, 612, 792), rotation=270, render_dpi=150)
        scale = 150 / 72.0
        # x=0, y=0; after 270°: x'=792-0=792, y'=0
        # effective_height after 270° = crop_width = 612
        # pixel_y = (612 - 0) * scale
        assert px == pytest.approx(792 * scale)
        assert py == pytest.approx(612 * scale)

    def test_cropbox_offset(self):
        px, py = pdf_to_pixel(100, 100, crop_box=(100, 100, 500, 700), rotation=0, render_dpi=150)
        scale = 150 / 72.0
        # After origin subtract: x=0, y=0
        # crop_height = 600
        # pixel_y = 600 * scale
        assert px == pytest.approx(0.0)
        assert py == pytest.approx(600 * scale)

    def test_rotated_plus_cropbox(self):
        """Combined rotation + CropBox test."""
        cb = (50, 50, 562, 742)
        pdf_x, pdf_y = 300, 400
        px, py = pdf_to_pixel(pdf_x, pdf_y, crop_box=cb, rotation=90, render_dpi=150)
        # Verify round-trip
        back_x, back_y = pixel_to_pdf(px, py, crop_box=cb, rotation=90, render_dpi=150)
        assert back_x == pytest.approx(pdf_x, abs=1e-6)
        assert back_y == pytest.approx(pdf_y, abs=1e-6)

    def test_high_dpi(self):
        px, py = pdf_to_pixel(306, 396, crop_box=(0, 0, 612, 792), rotation=0, render_dpi=300)
        scale = 300 / 72.0
        assert px == pytest.approx(306 * scale)
        assert py == pytest.approx((792 - 396) * scale)


class TestPixelToPdf:
    """pixel_to_pdf inverse tests — including direct tests (m4)."""

    @pytest.mark.parametrize("rotation", [0, 90, 180, 270])
    def test_round_trip_all_rotations(self, rotation):
        cb = (0, 0, 612, 792)
        pdf_x, pdf_y = 200.5, 400.3
        px, py = pdf_to_pixel(pdf_x, pdf_y, crop_box=cb, rotation=rotation, render_dpi=150)
        back_x, back_y = pixel_to_pdf(px, py, crop_box=cb, rotation=rotation, render_dpi=150)
        assert back_x == pytest.approx(pdf_x, abs=1e-6)
        assert back_y == pytest.approx(pdf_y, abs=1e-6)

    def test_round_trip_with_cropbox(self):
        cb = (72, 72, 540, 720)
        pdf_x, pdf_y = 300, 500
        px, py = pdf_to_pixel(pdf_x, pdf_y, crop_box=cb, rotation=0, render_dpi=150)
        back_x, back_y = pixel_to_pdf(px, py, crop_box=cb, rotation=0, render_dpi=150)
        assert back_x == pytest.approx(pdf_x, abs=1e-6)
        assert back_y == pytest.approx(pdf_y, abs=1e-6)

    def test_round_trip_rotation_and_cropbox(self):
        for rotation in [90, 180, 270]:
            cb = (50, 100, 450, 650)
            pdf_x, pdf_y = 250.7, 375.2
            px, py = pdf_to_pixel(pdf_x, pdf_y, crop_box=cb, rotation=rotation, render_dpi=300)
            back_x, back_y = pixel_to_pdf(px, py, crop_box=cb, rotation=rotation, render_dpi=300)
            assert back_x == pytest.approx(pdf_x, abs=1e-6), f"failed at rotation={rotation}"
            assert back_y == pytest.approx(pdf_y, abs=1e-6), f"failed at rotation={rotation}"

    def test_direct_pixel_origin_to_pdf(self):
        """m4: Direct pixel_to_pdf test (not round-trip) — pixel origin → PDF bottom-left."""
        cb = (0, 0, 612, 792)
        # Pixel origin (0, 0) = top-left corner = PDF (0, 792)
        pdf_x, pdf_y = pixel_to_pdf(0, 0, crop_box=cb, rotation=0, render_dpi=150)
        assert pdf_x == pytest.approx(0.0, abs=1e-6)
        assert pdf_y == pytest.approx(792.0, abs=1e-6)

    def test_direct_pixel_bottom_right_to_pdf(self):
        """m4: Direct pixel_to_pdf test — pixel bottom-right → PDF origin."""
        cb = (0, 0, 612, 792)
        scale = 150 / 72.0
        # Pixel (612*scale, 792*scale) = bottom-right corner = PDF (612, 0)
        pdf_x, pdf_y = pixel_to_pdf(612 * scale, 792 * scale, crop_box=cb, rotation=0, render_dpi=150)
        assert pdf_x == pytest.approx(612.0, abs=1e-6)
        assert pdf_y == pytest.approx(0.0, abs=1e-6)


# ── Classification tests ───────────────────────────────────────────────

class TestClassification:
    """Page classification logic."""

    def test_blank_page(self):
        assert _classify_page(0, 0, 0, False) == "blank"

    def test_blank_requires_all_zero(self):
        """Any signal makes the page nonblank."""
        assert _classify_page(1, 1, 0, False) != "blank"
        assert _classify_page(0, 0, 1, False) != "blank"
        assert _classify_page(0, 0, 0, True) != "blank"

    def test_text_page(self):
        assert _classify_page(
            word_count=100, char_count=500,
            vector_count=10, has_images=False
        ) == "text"

    def test_text_requires_no_images(self):
        assert _classify_page(
            word_count=100, char_count=500,
            vector_count=10, has_images=True
        ) != "text"

    def test_mixed_page(self):
        assert _classify_page(
            word_count=100, char_count=500,
            vector_count=60, has_images=False
        ) == "mixed"

    def test_mixed_with_images(self):
        assert _classify_page(
            word_count=100, char_count=500,
            vector_count=0, has_images=True
        ) == "mixed"

    def test_diagram_high_vectors(self):
        assert _classify_page(
            word_count=5, char_count=20,
            vector_count=100, has_images=False
        ) == "diagram"

    def test_diagram_image_low_text(self):
        assert _classify_page(
            word_count=10, char_count=50,
            vector_count=0, has_images=True
        ) == "diagram"

    def test_diagram_vectors_low_text(self):
        """Sparse vector lines with low text → diagram, not blank."""
        assert _classify_page(
            word_count=2, char_count=10,
            vector_count=5, has_images=False
        ) == "diagram"

    def test_text_light_fallback(self):
        """S5: short text pages with no vectors/images fall to text_light."""
        assert _classify_page(
            word_count=30, char_count=100,
            vector_count=0, has_images=False
        ) == "text_light"

    def test_text_light_not_with_vectors(self):
        """SF-1: text_light only applies when no vectors AND no images.
        With vectors present, fallback should be diagram."""
        assert _classify_page(
            word_count=30, char_count=100,
            vector_count=5, has_images=False
        ) == "diagram"

    def test_text_light_not_with_images(self):
        """SF-1: pages with images + moderate text → diagram, not text_light."""
        assert _classify_page(
            word_count=49, char_count=250,
            vector_count=49, has_images=True
        ) != "text_light"

    def test_image_blank_raster_only(self):
        """BLK-2: raster-only page (images, no text, no vectors) → image_blank."""
        assert _classify_page(
            word_count=0, char_count=0,
            vector_count=0, has_images=True
        ) == "image_blank"

    def test_sparse_diagram_never_blank(self):
        """Core regression: sparse diagram must never be blank."""
        # This is the exact scenario: sparse vectors, no words
        assert _classify_page(0, 0, 3, False) != "blank"


class TestThresholdEdgeBehavior:
    """Edge-case threshold behavior."""

    def test_text_at_exact_word_threshold(self):
        """word_count == TEXT_MIN_WORDS is NOT > threshold → not text."""
        result = _classify_page(
            word_count=TEXT_MIN_WORDS, char_count=200,
            vector_count=10, has_images=False
        )
        assert result != "text"  # needs > TEXT_MIN_WORDS

    def test_text_just_above_threshold(self):
        result = _classify_page(
            word_count=TEXT_MIN_WORDS + 1, char_count=200,
            vector_count=10, has_images=False
        )
        assert result == "text"

    def test_text_at_vector_boundary(self):
        """vector_count == TEXT_MAX_VECTOR_COUNT → text fails (not <)."""
        result = _classify_page(
            word_count=100, char_count=500,
            vector_count=TEXT_MAX_VECTOR_COUNT, has_images=False
        )
        assert result != "text"

    def test_diagram_at_exact_vector_threshold(self):
        """vector_count == DIAGRAM_VECTOR_THRESHOLD → diagram (>=)."""
        result = _classify_page(
            word_count=5, char_count=20,
            vector_count=DIAGRAM_VECTOR_THRESHOLD, has_images=False
        )
        assert result == "diagram"


# ── Escalation tests ──────────────────────────────────────────────────

class TestEscalation:
    """Escalation level computation."""

    def test_simple(self):
        assert _compute_escalation(10, 50) == "simple"

    def test_medium_by_words(self):
        assert _compute_escalation(MEDIUM_WORD_THRESHOLD + 1, 0) == "medium"

    def test_medium_by_vectors(self):
        assert _compute_escalation(0, MEDIUM_VECTOR_THRESHOLD + 1) == "medium"

    def test_dense_by_words(self):
        assert _compute_escalation(DENSE_WORD_THRESHOLD + 1, 0) == "dense"

    def test_dense_by_vectors(self):
        assert _compute_escalation(0, DENSE_VECTOR_THRESHOLD + 1) == "dense"

    def test_dense_overrides_medium(self):
        """Dense takes precedence when both thresholds are met."""
        assert _compute_escalation(
            DENSE_WORD_THRESHOLD + 1, MEDIUM_VECTOR_THRESHOLD + 1
        ) == "dense"


# ── SoM viability tests ───────────────────────────────────────────────

class TestSomViability:
    """Set-of-Mark viability scoring (S2: pypdfium2-denominated)."""

    def test_perfect_match(self):
        words = ["hello", "world", "test"]
        assert _compute_som_viability(words, words) is True

    def test_no_pdfplumber_words(self):
        """Zero pdfplumber words → False (no positive evidence)."""
        assert _compute_som_viability(["hello", "world"], []) is False

    def test_no_pdfium_words(self):
        """Zero pypdfium2 words → False (no positive evidence)."""
        assert _compute_som_viability([], ["hello", "world"]) is False

    def test_low_coverage_pdfium_denominated(self):
        """S2: Coverage is pypdfium2-denominated. Only 1/10 pdfium words match → low."""
        pdfium = [f"miss{i}" for i in range(9)] + ["hello"]
        plumber = ["hello", "world", "test"]
        # Only 1/10 pdfium words matched → 10% coverage
        assert _compute_som_viability(pdfium, plumber) is False

    def test_high_coverage_exact(self):
        """9 of 10 pdfium words matched → 90% coverage > 80%."""
        common = [f"word{i}" for i in range(9)]
        pdfium = common + ["unmatched"]
        plumber = common + ["extra"]
        assert _compute_som_viability(pdfium, plumber) is True

    def test_fuzzy_matching(self):
        """Slightly different spellings should match via fuzzy."""
        pdfium = ["hello", "worlds"]
        plumber = ["hello", "world"]
        # "worlds" vs "world" — SequenceMatcher ratio ≈ 0.91 > 0.85
        assert _compute_som_viability(pdfium, plumber) is True

    def test_fuzzy_ratio_boundary_just_below(self):
        """m1: Pair with ratio just below SOM_MIN_FUZZY_RATIO should not match."""
        # "ab" vs "abcdef" — ratio = 2*2/(2+6) = 0.5, well below 0.85
        pdfium = ["ab"]
        plumber = ["abcdef"]
        assert _compute_som_viability(pdfium, plumber) is False

    def test_fuzzy_ratio_boundary_just_above(self):
        """m1: Pair with ratio just above SOM_MIN_FUZZY_RATIO should match."""
        # "abcdefgh" vs "abcdefgi" — ratio = 2*7/16 = 0.875 > 0.85
        pdfium = ["abcdefgh"]
        plumber = ["abcdefgi"]
        assert _compute_som_viability(pdfium, plumber) is True

    def test_normalization(self):
        """Punctuation stripping and lowering should improve matches."""
        assert _normalize_word("Hello!") == "hello"
        assert _normalize_word("  WORLD  ") == "world"
        assert _normalize_word("(test)") == "test"

    def test_normalization_unicode_punctuation(self):
        """m3: Unicode punctuation should be stripped."""
        assert _normalize_word("«hello»") == "hello"
        assert _normalize_word("—test—") == "test"
        assert _normalize_word("\u300Ctest\u300D") == "test"  # CJK corner brackets


# ── B1: Error handling tests ─────────────────────────────────────────

class TestInspectPagesErrorHandling:
    """B1: Corrupt pages get degraded profiles instead of crashing."""

    def test_corrupt_page_gets_degraded_profile(self, tmp_path):
        """A page that raises during inspection should produce a degraded profile."""
        pdf = tmp_path / "text.pdf"
        _make_text_heavy_pdf(pdf, word_count=200)

        from folio.pipeline.inspect import _inspect_single_page
        original = _inspect_single_page

        def exploding_single(pdfium_doc, plumber_doc, page_num):
            if page_num == 1:
                raise RuntimeError("Corrupt page data")
            return original(pdfium_doc, plumber_doc, page_num)

        with patch("folio.pipeline.inspect._inspect_single_page", side_effect=exploding_single):
            profiles = inspect_pages(pdf)

        assert 1 in profiles
        assert profiles[1].classification == "text"  # degraded fallback
        assert profiles[1].word_count == 0
        assert profiles[1].render_dpi == 150

    def test_all_pages_corrupt_returns_all_degraded(self, tmp_path):
        """If all pages corrupt, all get degraded profiles — no crash."""
        pdf = tmp_path / "multi.pdf"
        _make_multipage_pdf(pdf)

        with patch("folio.pipeline.inspect._inspect_single_page", side_effect=RuntimeError("boom")):
            profiles = inspect_pages(pdf)

        assert len(profiles) == 3
        for p in profiles.values():
            assert p.classification == "text"
            assert p.word_count == 0


# ── m6: Zero-page edge case ──────────────────────────────────────────

class TestZeroPageEdge:
    """m6: 0-page PDF should return empty dict."""

    def test_zero_page_pdf(self, tmp_path):
        """A PDF with 0 pages returns an empty profiles dict."""
        # Patch at the adapter module level since inspect imports lazily
        with patch("folio.pipeline.pdfium_adapter.page_count_pdfplumber", return_value=0):
            pdf = tmp_path / "text.pdf"
            _make_blank_pdf(pdf)  # need a valid PDF to open
            profiles = inspect_pages(pdf)

        assert profiles == {}


# ── Integration tests with programmatic PDFs ──────────────────────────

class TestInspectPagesIntegration:
    """End-to-end inspection on generated PDFs."""

    def test_blank_pdf(self, tmp_path):
        pdf = tmp_path / "blank.pdf"
        _make_blank_pdf(pdf)
        profiles = inspect_pages(pdf)
        assert len(profiles) == 1
        p = profiles[1]
        assert p.classification == "blank"
        assert p.escalation_level == "simple"
        assert p.render_dpi == 150
        assert p.som_viable is False

    def test_text_heavy_pdf(self, tmp_path):
        pdf = tmp_path / "text.pdf"
        _make_text_heavy_pdf(pdf, word_count=200)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        assert p.classification == "text"
        assert p.word_count > TEXT_MIN_WORDS
        assert p.render_dpi == 150

    def test_sparse_diagram_pdf(self, tmp_path):
        pdf = tmp_path / "sparse.pdf"
        _make_sparse_diagram_pdf(pdf)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        assert p.classification != "blank", "Sparse diagrams must NOT be classified as blank"
        assert p.classification in ("diagram", "mixed")
        assert p.vector_count > 0

    def test_dense_diagram_pdf(self, tmp_path):
        pdf = tmp_path / "dense.pdf"
        _make_dense_diagram_pdf(pdf)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        assert p.classification == "diagram"
        assert p.escalation_level == "dense"
        assert p.render_dpi == 300

    def test_mixed_pdf(self, tmp_path):
        pdf = tmp_path / "mixed.pdf"
        _make_mixed_pdf(pdf)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        assert p.classification == "mixed"
        assert p.render_dpi == 300

    def test_multipage_pdf(self, tmp_path):
        pdf = tmp_path / "multi.pdf"
        _make_multipage_pdf(pdf)
        profiles = inspect_pages(pdf)
        assert len(profiles) == 3
        assert profiles[1].classification == "blank"
        assert profiles[2].classification == "text"
        assert profiles[3].classification in ("diagram", "mixed")

    def test_image_pdf(self, tmp_path):
        pdf = tmp_path / "image.pdf"
        _make_image_pdf(pdf)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        assert p.has_images is True
        # BLK-2: image-only pages may be image_blank or diagram depending
        # on whether they also have text/vectors
        assert p.classification in ("image_blank", "diagram", "mixed")

    def test_rotated_pdf(self, tmp_path):
        pdf = tmp_path / "rotated.pdf"
        _make_rotated_pdf(pdf, 90)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        assert p.rotation in (0, 90, 180, 270)  # rotation may vary by reader
        # Just verify it doesn't crash and produces valid profiles
        assert p.classification != ""

    def test_cropbox_pdf(self, tmp_path):
        pdf = tmp_path / "cropped.pdf"
        _make_cropbox_pdf(pdf, (100, 100, 500, 700))
        profiles = inspect_pages(pdf)
        p = profiles[1]
        assert p.crop_box is not None
        assert len(p.crop_box) == 4


class TestAdapterExtraction:
    """Adapter returns valid PDF-space and pixel-space boxes."""

    def test_bounded_texts_have_nonzero_bbox(self, tmp_path):
        pdf = tmp_path / "text.pdf"
        _make_text_heavy_pdf(pdf)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        for bt in p.bounded_texts:
            # PDF-space bbox should have area
            x0, y0, x1, y1 = bt.bbox
            assert x1 >= x0
            assert y1 >= y0

    def test_pixel_bboxes_within_page_bounds(self, tmp_path):
        pdf = tmp_path / "text.pdf"
        _make_text_heavy_pdf(pdf)
        profiles = inspect_pages(pdf)
        p = profiles[1]
        crop_w = p.crop_box[2] - p.crop_box[0]
        crop_h = p.crop_box[3] - p.crop_box[1]
        scale = p.render_dpi / 72.0
        max_px = crop_w * scale
        max_py = crop_h * scale

        for bt in p.bounded_texts:
            px0, py0, px1, py1 = bt.pixel_bbox
            # Allow small floating-point overshoot
            assert px0 >= -1.0, f"pixel x0={px0} out of bounds"
            assert py0 >= -1.0, f"pixel y0={py0} out of bounds"
            assert px1 <= max_px + 1.0, f"pixel x1={px1} exceeds page width {max_px}"
            assert py1 <= max_py + 1.0, f"pixel y1={py1} exceeds page height {max_py}"


# ── BLK-3: Pdfplumber fallback tests ───────────────────────────────────────

class TestPdfiumFallback:
    """BLK-3: When pdfium returns empty words but pdfplumber has text,
    use pdfplumber counts to prevent blank misclassification."""

    def test_pdfium_empty_pdfplumber_has_words(self, tmp_path):
        """A page where pdfium fails but pdfplumber has text should not be blank."""
        pdf = tmp_path / "text.pdf"
        _make_text_heavy_pdf(pdf, word_count=100)

        from folio.pipeline.inspect import _inspect_single_page
        original = _inspect_single_page

        def pdfium_empty_single(pdfium_doc, plumber_doc, page_num):
            # Patch pdfium word extraction to return empty
            with patch("folio.pipeline.pdfium_adapter.get_page_word_boxes_from_doc",
                       return_value=[]):
                return original(pdfium_doc, plumber_doc, page_num)

        with patch("folio.pipeline.inspect._inspect_single_page",
                   side_effect=pdfium_empty_single):
            profiles = inspect_pages(pdf)

        p = profiles[1]
        # BLK-3: should NOT be blank — pdfplumber fallback saves it
        assert p.classification != "blank", \
            "Soft pdfium failure should not make text page blank"
        assert p.word_count > 0
