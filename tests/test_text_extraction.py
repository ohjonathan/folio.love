"""Tests for text.py: boundary parsing, reconciliation, table detection, failure policy."""

from pathlib import Path
from unittest.mock import patch

import pytest

from folio.pipeline.text import (
    ReconciliationResult,
    SlideText,
    TextExtractionError,
    _detect_elements,
    _looks_like_table,
    _parse_slide_boundaries,
    extract_structured,
    reconcile_slide_count,
)


class TestHRBoundaryParsing:
    """Test horizontal-rule boundary detection (Pattern 2.5)."""

    def test_hr_splits_slides(self):
        text = "Slide one content here\n---\nSlide two content here\n---\nSlide three content here"
        result = _parse_slide_boundaries(text)
        assert len(result) == 3

    def test_equals_hr(self):
        text = "First slide\n===\nSecond slide\n===\nThird slide"
        result = _parse_slide_boundaries(text)
        assert len(result) == 3

    def test_hr_false_positive_guard_short_content(self):
        """HRs with no substantial content between them should not trigger splitting."""
        text = "---\n\n---\n\n---"
        result = _parse_slide_boundaries(text)
        assert len(result) == 0  # No content between HRs

    def test_hr_yaml_frontmatter_stripped(self):
        """YAML frontmatter delimiters (---) should not count as slide boundaries."""
        # Frontmatter stripped → only 1 HR remains → no split (needs >=2)
        text = "---\ntitle: Test\nauthor: Me\n---\nActual slide content is here\n---\nMore slide content is here"
        result = _parse_slide_boundaries(text)
        assert len(result) == 0  # Only 1 HR after stripping frontmatter

    def test_hr_yaml_frontmatter_with_enough_hrs(self):
        """With frontmatter stripped, multiple HRs still work."""
        text = "---\ntitle: Test\n---\nSlide one content here\n---\nSlide two content here\n---\nSlide three content"
        result = _parse_slide_boundaries(text)
        # After stripping frontmatter: 2 HRs with content between them
        assert len(result) >= 2

    def test_single_hr_ignored(self):
        """A single HR should not trigger splitting (needs >= 2)."""
        text = "Some content\n---\nMore content"
        result = _parse_slide_boundaries(text)
        assert len(result) == 0  # Only 1 HR in non-frontmatter zone


class TestNumberedSectionPattern:
    """Test tightened Pattern 3."""

    def test_sequential_from_one(self):
        text = "1\n\nSlide one content\n\n2\n\nSlide two content\n\n3\n\nSlide three content"
        result = _parse_slide_boundaries(text)
        assert len(result) == 3
        assert 1 in result
        assert 2 in result
        assert 3 in result

    def test_non_sequential_rejected(self):
        text = "1\n\nContent\n\n5\n\nMore content\n\n3\n\nOther content"
        result = _parse_slide_boundaries(text)
        assert len(result) == 0

    def test_not_from_one_rejected(self):
        text = "2\n\nContent\n\n3\n\nMore content\n\n4\n\nOther content"
        result = _parse_slide_boundaries(text)
        assert len(result) == 0


class TestReconcileSlideCount:
    """Test reconcile_slide_count with all edge cases."""

    def test_equal_counts(self):
        texts = {
            i: SlideText(slide_num=i, full_text=f"Slide {i}")
            for i in range(1, 6)
        }
        result = reconcile_slide_count(texts, 5)
        assert not result.was_reconciled
        assert result.action == "none"
        assert result.alignment_confidence == 1.0
        assert len(result.slide_texts) == 5
        assert result.gaps_filled == 0

    def test_pad_missing(self):
        texts = {
            i: SlideText(slide_num=i, full_text=f"Slide {i}")
            for i in range(1, 4)
        }
        result = reconcile_slide_count(texts, 5)
        assert result.was_reconciled
        assert result.action == "padded"
        assert len(result.slide_texts) == 5
        assert result.alignment_confidence == pytest.approx(0.6)
        assert result.slide_texts[4].is_empty
        assert result.slide_texts[5].is_empty

    def test_truncate_extra(self):
        texts = {
            i: SlideText(slide_num=i, full_text=f"Slide {i}")
            for i in range(1, 6)
        }
        result = reconcile_slide_count(texts, 3)
        assert result.was_reconciled
        assert result.action == "truncated"
        assert len(result.slide_texts) == 3
        assert result.alignment_confidence == pytest.approx(0.6)

    def test_no_text(self):
        result = reconcile_slide_count({}, 5)
        assert result.was_reconciled
        assert result.action == "padded"
        assert len(result.slide_texts) == 5
        assert result.alignment_confidence == 0.0
        for st in result.slide_texts.values():
            assert st.is_empty

    def test_sparse_pdf_pages_fill_gaps(self):
        """Keys {1, 3} with 5 images → key 2 filled, keys 4-5 padded."""
        texts = {
            1: SlideText(slide_num=1, full_text="Page one"),
            3: SlideText(slide_num=3, full_text="Page three"),
        }
        result = reconcile_slide_count(texts, 5)
        assert result.gaps_filled == 1  # Key 2 was missing
        assert result.was_reconciled
        assert result.action == "padded"
        assert len(result.slide_texts) == 5
        assert result.slide_texts[2].is_empty
        assert result.slide_texts[4].is_empty
        assert result.slide_texts[5].is_empty
        # Original keys preserved
        assert result.slide_texts[1].full_text == "Page one"
        assert result.slide_texts[3].full_text == "Page three"

    def test_contiguous_no_gaps(self):
        texts = {
            i: SlideText(slide_num=i, full_text=f"Slide {i}")
            for i in range(1, 4)
        }
        result = reconcile_slide_count(texts, 3)
        assert result.gaps_filled == 0

    def test_does_not_mutate_input(self):
        """B2 fix: reconcile must not mutate the caller's dict."""
        original = {
            1: SlideText(slide_num=1, full_text="One"),
            3: SlideText(slide_num=3, full_text="Three"),
        }
        original_keys = set(original.keys())
        reconcile_slide_count(original, 5)
        # Input dict should be unchanged
        assert set(original.keys()) == original_keys

    def test_reconcile_then_version_no_false_changes(self):
        """B2 integration: reconcile -> version compute -> reconvert -> has_changes=False."""
        from folio.tracking.versions import detect_changes

        texts = {
            1: SlideText(slide_num=1, full_text="One"),
            3: SlideText(slide_num=3, full_text="Three"),
        }
        result1 = reconcile_slide_count(texts, 5)

        # Simulate reconverting with same source
        texts2 = {
            1: SlideText(slide_num=1, full_text="One"),
            3: SlideText(slide_num=3, full_text="Three"),
        }
        result2 = reconcile_slide_count(texts2, 5)

        changes = detect_changes(result1.slide_texts, result2.slide_texts)
        assert not changes.has_changes

    def test_reconciliation_result_fields(self):
        texts = {1: SlideText(slide_num=1, full_text="One")}
        result = reconcile_slide_count(texts, 3)
        assert hasattr(result, "slide_texts")
        assert hasattr(result, "was_reconciled")
        assert hasattr(result, "action")
        assert hasattr(result, "gaps_filled")
        assert hasattr(result, "original_text_count")
        assert hasattr(result, "image_count")
        assert hasattr(result, "alignment_confidence")


class TestSlideTextIsEmpty:
    """Test SlideText.is_empty field."""

    def test_default_false(self):
        st = SlideText(slide_num=1, full_text="hello")
        assert st.is_empty is False

    def test_explicit_true(self):
        st = SlideText(slide_num=1, full_text="", is_empty=True)
        assert st.is_empty is True


class TestTableDetection:
    """Test table detection heuristic."""

    def test_pipe_delimited_table(self):
        text = "| Col A | Col B |\n| --- | --- |\n| val1 | val2 |\n| val3 | val4 |"
        assert _looks_like_table(text) is True

    def test_no_pipes(self):
        text = "Just regular body text\nSpanning multiple lines"
        assert _looks_like_table(text) is False

    def test_table_element_type(self):
        text = "| A | B |\n| 1 | 2 |\n| 3 | 4 |\n| 5 | 6 |"
        elements = _detect_elements(text)
        table_elems = [e for e in elements if e["type"] == "table"]
        assert len(table_elems) == 1

    def test_non_table_body_type(self):
        text = "Normal body text here"
        elements = _detect_elements(text)
        body_elems = [e for e in elements if e["type"] == "body"]
        assert len(body_elems) == 1
        table_elems = [e for e in elements if e["type"] == "table"]
        assert len(table_elems) == 0


class TestPDFFailurePolicy:
    """Test three-layer failure policy for PDF extraction."""

    def test_import_error_raises(self):
        """L1: missing pdfplumber raises TextExtractionError."""
        import importlib
        import sys
        from folio.pipeline import text as text_mod

        # Temporarily hide pdfplumber
        saved = sys.modules.get("pdfplumber")
        sys.modules["pdfplumber"] = None  # type: ignore
        try:
            # Force re-import attempt inside _extract_pdf
            with pytest.raises(TextExtractionError, match="pdfplumber"):
                text_mod._extract_pdf(Path("test.pdf"))
        finally:
            if saved is not None:
                sys.modules["pdfplumber"] = saved
            else:
                sys.modules.pop("pdfplumber", None)

    def test_extract_structured_catches_text_error(self):
        """L2: extract_structured catches TextExtractionError and returns {}."""
        with patch("folio.pipeline.text._extract_pdf", side_effect=TextExtractionError("test error")):
            result = extract_structured(Path("test.pdf"))
        assert result == {}


class TestPPTXFailurePolicy:
    """Test three-layer failure policy for PPTX extraction (S2)."""

    def test_pptx_extraction_error_caught_at_l2(self):
        """L2: extract_structured catches TextExtractionError from _extract_pptx."""
        with patch("folio.pipeline.text._extract_pptx", side_effect=TextExtractionError("markitdown failed")):
            result = extract_structured(Path("test.pptx"))
        assert result == {}

    def test_pptx_unexpected_error_wrapped(self):
        """L1: unexpected errors in _extract_pptx are wrapped in TextExtractionError."""
        from folio.pipeline import text as text_mod
        with patch("markitdown.MarkItDown") as mock_md:
            mock_md.return_value.convert.side_effect = RuntimeError("unexpected")
            with pytest.raises(TextExtractionError, match="MarkItDown extraction failed"):
                text_mod._extract_pptx(Path("test.pptx"))


class TestExtractStructuredTypeIntegrity:
    """Test return type integrity for all paths."""

    def test_returns_dict_of_slidetext(self):
        mock_slides = {
            1: SlideText(slide_num=1, full_text="Hello", elements=[]),
        }
        with patch("folio.pipeline.text._extract_pptx", return_value=mock_slides):
            result = extract_structured(Path("test.pptx"))
        assert isinstance(result, dict)
        for v in result.values():
            assert isinstance(v, SlideText)
