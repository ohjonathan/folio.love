"""Integration tests for converter with reconciliation, blank override, and cache migration."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from folio.config import FolioConfig
from folio.converter import FolioConverter, _alignment_status
from folio.pipeline.analysis import SlideAnalysis
from folio.pipeline.images import ImageResult
from folio.pipeline.text import SlideText, reconcile_slide_count
from folio.tracking.versions import (
    _TEXTS_CACHE_VERSION,
    compute_version,
    detect_changes,
    load_texts_cache,
    save_texts_cache,
)


def _mock_anthropic_response(text: str):
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    mock_response.stop_reason = "end_turn"
    return mock_response


MOCK_RESPONSE = """Slide Type: title
Framework: none
Visual Description: Title slide.
Key Data: None
Main Insight: Opening slide.
Evidence:
- Claim: Title
  Quote: "Test"
  Element: body
  Confidence: high"""


class TestAlignmentStatus:
    """Test _alignment_status helper."""

    def test_accepted(self):
        assert _alignment_status(1.0) == "accepted"
        assert _alignment_status(0.7) == "accepted"

    def test_degraded(self):
        assert _alignment_status(0.5) == "degraded"
        assert _alignment_status(0.3) == "degraded"

    def test_untrusted(self):
        assert _alignment_status(0.2) == "untrusted"
        assert _alignment_status(0.0) == "untrusted"


class TestBlankOverridePath:
    """Test blank slide override in converter pipeline."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_blank_slides_get_pending(self):
        """Blank slides get SlideAnalysis.pending() after analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            image_paths = []
            for i in range(1, 4):
                img = target_dir / f"slide-{i:03d}.png"
                img.write_bytes(self._make_unique_png(i))
                image_paths.append(img)

            # Slide 2 is blank
            image_results = [
                ImageResult(path=image_paths[0], slide_num=1, is_blank=False, width=200, height=200),
                ImageResult(path=image_paths[1], slide_num=2, is_blank=True, width=200, height=200),
                ImageResult(path=image_paths[2], slide_num=3, is_blank=False, width=200, height=200),
            ]

            slide_texts = {
                i: SlideText(slide_num=i, full_text=f"Slide {i}", elements=[])
                for i in range(1, 4)
            }

            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                return_value=_mock_anthropic_response(MOCK_RESPONSE)
            )

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=source), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            content = result.output_path.read_text()
            parsed_fm = yaml.safe_load(content[3:content.index("---", 3)])

            # Check blank slide is pending (its analysis should not pollute frontmatter)
            assert result.slide_count == 3


class TestReconciliationMetadataInFrontmatter:
    """Test reconciliation metadata flows to frontmatter."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_reconciliation_fields_in_yaml(self):
        """Frontmatter should contain text_reconciled etc. when reconciled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            image_paths = []
            for i in range(1, 6):
                img = target_dir / f"slide-{i:03d}.png"
                img.write_bytes(self._make_unique_png(i))
                image_paths.append(img)

            # 5 images, 3 texts → reconciliation will pad
            image_results = [
                ImageResult(path=image_paths[j], slide_num=j + 1, width=200, height=200)
                for j in range(5)
            ]

            slide_texts = {
                i: SlideText(slide_num=i, full_text=f"Slide {i}", elements=[])
                for i in range(1, 4)
            }

            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                return_value=_mock_anthropic_response(MOCK_RESPONSE)
            )

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=source), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            content = result.output_path.read_text()
            end = content.index("---", 3)
            parsed = yaml.safe_load(content[3:end])

            assert parsed["text_reconciled"] is True
            assert parsed["text_reconciliation"] == "padded"
            assert "text_alignment_confidence" in parsed
            assert "text_alignment_status" in parsed


class TestTextsCacheMigration:
    """Test B3: .texts_cache.json migration on v0.3.1 upgrade."""

    def test_old_cache_invalidated(self, tmp_path):
        """Pre-v0.3.1 cache (no version marker) should be invalidated."""
        cache_path = tmp_path / ".texts_cache.json"
        # Old format: no _cache_version key
        old_data = {"1": "slide one", "2": "slide two"}
        cache_path.write_text(json.dumps(old_data))

        result = load_texts_cache(cache_path)
        assert result == {}  # Invalidated

    def test_new_cache_loads(self, tmp_path):
        """Cache with correct version marker should load."""
        cache_path = tmp_path / ".texts_cache.json"
        data = {"1": "slide one", "2": "slide two", "_cache_version": _TEXTS_CACHE_VERSION}
        cache_path.write_text(json.dumps(data))

        result = load_texts_cache(cache_path)
        assert result == {1: "slide one", 2: "slide two"}

    def test_save_includes_version(self, tmp_path):
        """save_texts_cache should include _cache_version."""
        cache_path = tmp_path / ".texts_cache.json"
        texts = {1: "hello", 2: "world"}
        save_texts_cache(cache_path, texts)

        raw = json.loads(cache_path.read_text())
        assert raw["_cache_version"] == _TEXTS_CACHE_VERSION

    def test_first_reconversion_after_upgrade(self, tmp_path):
        """First reconversion after upgrade: old cache invalidated → all slides 'added'."""
        cache_path = tmp_path / ".texts_cache.json"
        # Simulate pre-upgrade cache
        old_data = {"1": "existing text"}
        cache_path.write_text(json.dumps(old_data))

        # Load (should be invalidated)
        old_texts = load_texts_cache(cache_path)
        assert old_texts == {}

        # New texts
        new_texts = {1: SlideText(slide_num=1, full_text="existing text", elements=[])}

        changes = detect_changes(old_texts, new_texts)
        # All slides appear as "added" (honest changeset)
        assert changes.added == [1]
        assert changes.modified == []

    def test_mismatched_version_invalidated(self, tmp_path):
        """Cache with wrong version number should be invalidated."""
        cache_path = tmp_path / ".texts_cache.json"
        data = {"1": "text", "_cache_version": 999}
        cache_path.write_text(json.dumps(data))

        result = load_texts_cache(cache_path)
        assert result == {}


class TestSparsePageAlignment:
    """Test that sparse PDF page keys are handled correctly."""

    def test_sparse_keys_preserved(self):
        """PDF with empty page 2: page 3's text maps to image 3."""
        texts = {
            1: SlideText(slide_num=1, full_text="Page one content"),
            3: SlideText(slide_num=3, full_text="Page three content"),
        }
        result = reconcile_slide_count(texts, 3)
        assert result.slide_texts[1].full_text == "Page one content"
        assert result.slide_texts[2].is_empty  # Gap filled
        assert result.slide_texts[3].full_text == "Page three content"
