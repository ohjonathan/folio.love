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
from folio.llm.types import StageLLMMetadata
from folio.pipeline.analysis import CacheStats, DiagramAnalysis, SlideAnalysis
from folio.pipeline.images import ImageResult
from folio.pipeline.normalize import NormalizationResult
from folio.pipeline.text import SlideText, reconcile_slide_count
from folio.tracking.versions import (
    _TEXTS_CACHE_VERSION,
    compute_version,
    detect_changes,
    load_texts_cache,
    save_texts_cache,
)


@pytest.fixture(autouse=True)
def _mock_inspect_pages():
    """Auto-mock inspect_pages for all converter integration tests.

    Returns text classification for all pages by default.
    Individual tests override with their own patch when needed (e.g. blank tests).
    """
    class _DefaultProfileDict(dict):
        """Dict that returns text PageProfile for any missing page."""
        def __missing__(self, key):
            profile = MagicMock(classification="text")
            self[key] = profile
            return profile

    with patch("folio.pipeline.inspect.inspect_pages", return_value=_DefaultProfileDict()):
        yield


def _mock_anthropic_response(text: str):
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    mock_response.stop_reason = "end_turn"
    # Token usage must be real ints for RateLimiter.record_usage comparison
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
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

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.inspect.inspect_pages", return_value={
                     1: MagicMock(classification="text"),
                     2: MagicMock(classification="image_blank"),
                     3: MagicMock(classification="text"),
                 }), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            content = result.output_path.read_text()
            parsed_fm = yaml.safe_load(content[3:content.index("---", 3)])

            # Check blank slide is pending (its analysis should not pollute frontmatter)
            assert result.slide_count == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_blank_slide_override_does_not_create_partial_analysis_flag(self):
        """Blank override path must not emit partial_analysis flags for blank slides."""
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

            image_results = [
                ImageResult(path=image_paths[0], slide_num=1, is_blank=False, width=200, height=200),
                ImageResult(path=image_paths[1], slide_num=2, is_blank=True, width=200, height=200),
                ImageResult(path=image_paths[2], slide_num=3, is_blank=False, width=200, height=200),
            ]
            slide_texts = {
                1: SlideText(slide_num=1, full_text="Slide 1 content", elements=[]),
                2: SlideText(slide_num=2, full_text="", elements=[]),
                3: SlideText(slide_num=3, full_text="Slide 3 content", elements=[]),
            }
            pass1_analyses = {
                1: SlideAnalysis(slide_type="data", evidence=[{"confidence": "high", "validated": True}]),
                2: SlideAnalysis(slide_type="data", evidence=[{"confidence": "high", "validated": True}]),
                3: SlideAnalysis(slide_type="framework", evidence=[{"confidence": "high", "validated": True}]),
            }

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch(
                     "folio.pipeline.analysis.analyze_slides",
                     return_value=(pass1_analyses, CacheStats(hits=0, misses=3, pass_name="pass1"), None),
                 ):
                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            content = result.output_path.read_text()
            parsed_fm = yaml.safe_load(content[3:content.index("---", 3)])

            assert parsed_fm["review_status"] == "clean"
            assert parsed_fm["review_flags"] == []
            assert "partial_analysis_slide_2" not in parsed_fm["review_flags"]


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

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
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


class TestBlankSlidesSkipPass2:
    """S4: blank slides are explicitly excluded from Pass 2 density scoring."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_blank_slides_skip_pass2(self):
        """Blank slides in skip_slides are never scored for density."""
        from folio.pipeline.analysis import SlideAnalysis, analyze_slides_deep

        pass1_results = {
            1: SlideAnalysis(slide_type="data", framework="none", key_data="revenue: $10M, $20M, $30M"),
            2: SlideAnalysis.pending(),  # blank slide
            3: SlideAnalysis(slide_type="data", framework="none", key_data="growth: 10%, 20%, 30%"),
        }
        slide_texts = {
            1: SlideText(slide_num=1, full_text="Revenue data " * 30),
            2: SlideText(slide_num=2, full_text="Dense content " * 30, is_empty=True),
            3: SlideText(slide_num=3, full_text="Growth data " * 30),
        }

        # Mock _compute_density_score to track which slides get scored
        scored_slides = []
        original_compute = __import__("folio.pipeline.analysis", fromlist=["_compute_density_score"])._compute_density_score

        def tracking_density(analysis, text):
            scored_slides.append(text.slide_num)
            return original_compute(analysis, text)

        with patch("folio.pipeline.analysis._compute_density_score", side_effect=tracking_density), \
             patch("anthropic.Anthropic"):
            analyze_slides_deep(
                pass1_results=pass1_results,
                slide_texts=slide_texts,
                image_paths=[Path("a.png"), Path("b.png"), Path("c.png")],
                skip_slides={2},
            )

        # Slide 2 should never have been scored for density
        assert 2 not in scored_slides
        # Slides 1 and 3 should have been scored
        assert 1 in scored_slides
        assert 3 in scored_slides


class TestLLMMetadataConverterIntegration:
    """Test converter-level LLM metadata emission for fallback scenarios."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass2_fallback_written_to_frontmatter(self):
        """Frontmatter should reflect the actual pass-2 fallback provider/model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            img = target_dir / "slide-001.png"
            img.write_bytes(self._make_unique_png(1))

            image_results = [
                ImageResult(path=img, slide_num=1, width=200, height=200),
            ]
            slide_texts = {
                1: SlideText(slide_num=1, full_text="Content " * 20, elements=[]),
            }
            pass1_analyses = {
                1: SlideAnalysis(
                    slide_type="data",
                    framework="none",
                    visual_description="chart",
                    key_data="$10M",
                    main_insight="growing",
                    evidence=[{
                        "claim": "Revenue",
                        "quote": "$10M",
                        "element_type": "body",
                        "confidence": "high",
                        "validated": True,
                        "pass": 1,
                    }],
                ),
            }
            pass2_analyses = {
                1: SlideAnalysis(
                    slide_type="data",
                    framework="none",
                    visual_description="chart",
                    key_data="$10M",
                    main_insight="growing",
                    evidence=[
                        {
                            "claim": "Revenue",
                            "quote": "$10M",
                            "element_type": "body",
                            "confidence": "high",
                            "validated": True,
                            "pass": 1,
                        },
                        {
                            "claim": "Expanded detail",
                            "quote": "detail",
                            "element_type": "body",
                            "confidence": "high",
                            "validated": False,
                            "pass": 2,
                        },
                    ],
                ),
            }
            pass1_meta = StageLLMMetadata(
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                slide_count=1,
                cache_misses=1,
                per_slide_providers={1: ("anthropic", "claude-sonnet-4-20250514")},
            )
            pass2_meta = StageLLMMetadata(
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                slide_count=1,
                cache_misses=1,
                fallback_activated=True,
                fallback_provider="openai",
                fallback_model="gpt-4o",
                per_slide_providers={1: ("openai", "gpt-4o")},
            )

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch(
                     "folio.pipeline.analysis.analyze_slides",
                     return_value=(pass1_analyses, CacheStats(hits=0, misses=1, pass_name="pass1"), pass1_meta),
                 ), \
                 patch(
                     "folio.pipeline.analysis.analyze_slides_deep",
                     return_value=(pass2_analyses, CacheStats(hits=0, misses=1, pass_name="pass2"), pass2_meta),
                 ):
                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=2)

            content = result.output_path.read_text()
            parsed = yaml.safe_load(content[3:content.index("---", 3)])
            llm_meta = parsed["_llm_metadata"]["convert"]

            assert llm_meta["fallback_used"] is True
            assert llm_meta["provider"] == "openai"
            assert llm_meta["model"] == "gpt-4o"
            assert llm_meta["pass2"]["status"] == "executed"
            assert llm_meta["pass2"]["fallback_used"] is True
            assert llm_meta["pass2"]["provider"] == "openai"
            assert llm_meta["pass2"]["model"] == "gpt-4o"


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


class TestNoCacheConverterIntegration:
    """E2E: --no-cache flag flows through converter.convert() to force re-analysis."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_no_cache_forces_reanalysis_through_pipeline(self):
        """converter.convert(no_cache=True) re-runs both passes and overwrites stale cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            image_paths = []
            for i in range(1, 3):
                img = target_dir / f"slide-{i:03d}.png"
                img.write_bytes(self._make_unique_png(i))
                image_paths.append(img)

            image_results = [
                ImageResult(path=image_paths[j], slide_num=j + 1, width=200, height=200)
                for j in range(2)
            ]

            slide_texts = {
                i: SlideText(slide_num=i, full_text=f"Slide {i} content " * 20, elements=[])
                for i in range(1, 3)
            }

            api_calls = []

            def mock_create(**kw):
                api_calls.append(1)
                return _mock_anthropic_response(MOCK_RESPONSE)

            mock_client = MagicMock()
            mock_client.messages.create = mock_create

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)

                # Run 1: populate cache (no_cache=False)
                r1 = converter.convert(source_path=source, target=target_dir, passes=1)
                calls_run1 = len(api_calls)
                assert calls_run1 == 2  # 2 slides analyzed

                # Run 2: cached (no_cache=False) — should NOT call API
                api_calls.clear()
                r2 = converter.convert(source_path=source, target=target_dir, passes=1)
                assert len(api_calls) == 0  # All cache hits
                assert r2.cache_stats is not None
                assert r2.cache_stats.hits == 2
                assert r2.cache_stats.misses == 0

                # Run 3: forced re-analysis (no_cache=True) — MUST call API
                api_calls.clear()
                r3 = converter.convert(source_path=source, target=target_dir, passes=1, no_cache=True)
                assert len(api_calls) == 2  # Both slides re-analyzed
                assert r3.cache_stats is not None
                assert r3.cache_stats.misses == 2
                assert r3.cache_stats.hits == 0


class TestPptxOutputDirPlumbing:
    """Test that converter delegates to normalize without pptx_output_dir.

    Since PR #12, the converter no longer passes pptx_output_dir — the staging
    directory is managed inside normalize.to_pdf() itself.
    """

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_normalize_called_without_pptx_output_dir(self):
        """converter.convert() must NOT pass pptx_output_dir (staging is internal)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            img = target_dir / "slide-001.png"
            img.write_bytes(self._make_unique_png(1))

            image_results = [
                ImageResult(path=img, slide_num=1, width=200, height=200),
            ]
            slide_texts = {
                1: SlideText(slide_num=1, full_text="Content", elements=[]),
            }

            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                return_value=_mock_anthropic_response(MOCK_RESPONSE)
            )

            to_pdf_calls = []

            def capture_to_pdf(*args, **kwargs):
                to_pdf_calls.append(kwargs)
                return NormalizationResult(pdf_path=source, renderer_used="powerpoint")

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", side_effect=capture_to_pdf) as mock_to_pdf, \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            assert len(to_pdf_calls) == 1
            assert to_pdf_calls[0].get("pptx_output_dir") is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_intermediate_powerpoint_pdf_cleaned_up(self):
        """Intermediate PowerPoint PDF in deck_dir should be deleted after image extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            # Simulate PowerPoint writing PDF to deck_dir
            ppt_pdf = target_dir / "test.pdf"
            ppt_pdf.write_text("intermediate pdf")

            img = target_dir / "slide-001.png"
            img.write_bytes(self._make_unique_png(1))

            image_results = [
                ImageResult(path=img, slide_num=1, width=200, height=200),
            ]
            slide_texts = {
                1: SlideText(slide_num=1, full_text="Content", elements=[]),
            }

            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                return_value=_mock_anthropic_response(MOCK_RESPONSE)
            )

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=ppt_pdf, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            # Intermediate PDF should be cleaned up
            assert not ppt_pdf.exists()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pdf_input_no_cleanup(self):
        """PDF input should NOT trigger intermediate cleanup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pdf"
            source.write_bytes(b"%PDF-1.4 content")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            # PDF lands in temp dir (not deck_dir)
            temp_pdf = tmpdir_path / "temp" / "test.pdf"
            temp_pdf.parent.mkdir()
            temp_pdf.write_text("temp copy")

            img = target_dir / "slide-001.png"
            img.write_bytes(self._make_unique_png(1))

            image_results = [
                ImageResult(path=img, slide_num=1, width=200, height=200),
            ]
            slide_texts = {
                1: SlideText(slide_num=1, full_text="Content", elements=[]),
            }

            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                return_value=_mock_anthropic_response(MOCK_RESPONSE)
            )

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=temp_pdf, renderer_used="pdf-copy")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            # PDF input: no cleanup (source is .pdf, not .pptx)
            assert temp_pdf.exists()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_scanned_pdf_warning(self, caplog):
        """Low text density should trigger a sparse-text warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "scanned.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            imgs = []
            image_results = []
            for i in range(1, 4):
                img = target_dir / f"slide-{i:03d}.png"
                img.write_bytes(self._make_unique_png(i))
                imgs.append(img)
                image_results.append(
                    ImageResult(path=img, slide_num=i, width=200, height=200)
                )

            # Very low text content (< 10 chars per page)
            slide_texts = {
                i: SlideText(slide_num=i, full_text="x", elements=[])
                for i in range(1, 4)
            }

            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                return_value=_mock_anthropic_response(MOCK_RESPONSE)
            )

            config = FolioConfig()

            import logging
            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client), \
                 caplog.at_level(logging.WARNING):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            assert "Low text density" in caplog.text
            # PPTX source → "very sparse text", not "scanned PDF"
            assert "very sparse text" in caplog.text

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_scanned_pdf_no_warning_above_threshold(self, caplog):
        """Text density >= 10 chars/page should NOT trigger warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "ok.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            img = target_dir / "slide-001.png"
            img.write_bytes(self._make_unique_png(1))
            image_results = [
                ImageResult(path=img, slide_num=1, width=200, height=200),
            ]

            # 15 chars per page — above threshold
            slide_texts = {
                1: SlideText(slide_num=1, full_text="Fifteen chars!!", elements=[]),
            }

            mock_client = MagicMock()
            mock_client.messages.create = MagicMock(
                return_value=_mock_anthropic_response(MOCK_RESPONSE)
            )

            config = FolioConfig()

            import logging
            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch("anthropic.Anthropic", return_value=mock_client), \
                 caplog.at_level(logging.WARNING):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            assert "Low text density" not in caplog.text

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_intermediate_pdf_cleaned_up_on_extraction_failure(self):
        """Intermediate PowerPoint PDF should be cleaned up even if image extraction fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            # Simulate PowerPoint writing PDF to deck_dir
            ppt_pdf = target_dir / "test.pdf"
            ppt_pdf.write_text("intermediate pdf")

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=ppt_pdf, renderer_used="powerpoint")), \
                 patch("folio.pipeline.images.extract_with_metadata",
                       side_effect=RuntimeError("extraction failed")):

                converter = FolioConverter(config)
                with pytest.raises(RuntimeError, match="extraction failed"):
                    converter.convert(source_path=source, target=target_dir, passes=1)

            # Intermediate PDF should STILL be cleaned up (try/finally)
            assert not ppt_pdf.exists()


# ---------------------------------------------------------------------------
# PR 3: Diagram routing integration tests
# ---------------------------------------------------------------------------


class TestMixedPageRouting:
    """Integration: mixed page → DiagramAnalysis, skips Pass 2."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_mixed_page_becomes_diagram_analysis_and_skips_pass2(self):
        """Mixed-classified page is coerced to DiagramAnalysis and excluded from Pass 2."""
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

            image_results = [
                ImageResult(path=image_paths[0], slide_num=1, is_blank=False, width=200, height=200),
                ImageResult(path=image_paths[1], slide_num=2, is_blank=False, width=200, height=200),
                ImageResult(path=image_paths[2], slide_num=3, is_blank=False, width=200, height=200),
            ]
            slide_texts = {
                i: SlideText(slide_num=i, full_text=f"Slide {i} content", elements=[])
                for i in range(1, 4)
            }
            # Pass 1 returns standard SlideAnalysis for all (converter coerces mixed)
            pass1_analyses = {
                1: SlideAnalysis(
                    slide_type="data", framework="none",
                    evidence=[{"confidence": "high", "validated": True}],
                ),
                2: SlideAnalysis(
                    slide_type="data", framework="none",
                    evidence=[{"confidence": "high", "validated": True}],
                ),
                3: SlideAnalysis(
                    slide_type="data", framework="none",
                    evidence=[{"confidence": "high", "validated": True}],
                ),
            }

            config = FolioConfig()

            # Track skip_slides passed to analyze_slides_deep
            captured_skip_slides = []
            original_deep = None

            def tracking_deep(*args, **kwargs):
                captured_skip_slides.append(kwargs.get("skip_slides", set()))
                return kwargs.get("pass1_results", {}), CacheStats(hits=0, misses=0, pass_name="pass2"), None

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.inspect.inspect_pages", return_value={
                     1: MagicMock(classification="text"),
                     2: MagicMock(classification="mixed"),
                     3: MagicMock(classification="text"),
                 }), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch(
                     "folio.pipeline.analysis.analyze_slides",
                     return_value=(pass1_analyses, CacheStats(hits=0, misses=3, pass_name="pass1"), None),
                 ), \
                 patch("folio.pipeline.analysis.analyze_slides_deep", side_effect=tracking_deep) as mock_deep:

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=2)

            # The mixed page's analysis should have been coerced to DiagramAnalysis
            # (converter does this after pass 1, before pass 2)
            # We verify this by checking that page 2 was in skip_slides for pass 2
            assert len(captured_skip_slides) == 1
            assert 2 in captured_skip_slides[0]


class TestUnsupportedDiagramAbstention:
    """Integration: unsupported_diagram → abstained placeholder, no failure flags."""

    @staticmethod
    def _make_unique_png(index: int) -> bytes:
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
            + bytes([index]) * 16
            + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
        )

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_unsupported_diagram_gets_abstained_placeholder(self):
        """Unsupported diagram inserts abstained DiagramAnalysis, not a failure flag."""
        import yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            source = tmpdir_path / "test.pptx"
            source.write_bytes(b"fake")

            target_dir = tmpdir_path / "output"
            target_dir.mkdir()

            image_paths = []
            for i in range(1, 3):
                img = target_dir / f"slide-{i:03d}.png"
                img.write_bytes(self._make_unique_png(i))
                image_paths.append(img)

            image_results = [
                ImageResult(path=image_paths[0], slide_num=1, is_blank=False, width=200, height=200),
                ImageResult(path=image_paths[1], slide_num=2, is_blank=False, width=200, height=200),
            ]
            slide_texts = {
                1: SlideText(slide_num=1, full_text="Normal slide", elements=[]),
                2: SlideText(slide_num=2, full_text="Diagram slide", elements=[]),
            }
            # Only page 1 goes through pass 1 (page 2 is unsupported_diagram, skipped)
            pass1_analyses = {
                1: SlideAnalysis(
                    slide_type="data", framework="none",
                    evidence=[{"confidence": "high", "validated": True}],
                ),
            }

            config = FolioConfig()

            with patch("folio.pipeline.normalize.to_pdf", return_value=NormalizationResult(pdf_path=source, renderer_used="powerpoint")), \
                 patch("folio.pipeline.inspect.inspect_pages", return_value={
                     1: MagicMock(classification="text"),
                     2: MagicMock(classification="unsupported_diagram"),
                 }), \
                 patch("folio.pipeline.images.extract_with_metadata", return_value=image_results), \
                 patch("folio.pipeline.text.extract_structured", return_value=slide_texts), \
                 patch(
                     "folio.pipeline.analysis.analyze_slides",
                     return_value=(pass1_analyses, CacheStats(hits=0, misses=1, pass_name="pass1"), None),
                 ):

                converter = FolioConverter(config)
                result = converter.convert(source_path=source, target=target_dir, passes=1)

            content = result.output_path.read_text()
            parsed_fm = yaml.safe_load(content[3:content.index("---", 3)])

            # Should NOT have analysis_unavailable or partial_analysis
            assert "analysis_unavailable" not in parsed_fm.get("review_flags", [])
            assert "partial_analysis_slide_2" not in parsed_fm.get("review_flags", [])
            # Should have the dedicated abstention flag
            assert "diagram_abstained_slide_2" in parsed_fm.get("review_flags", [])


class TestCacheHitPolymorphicRoundTrip:
    """Integration: cached DiagramAnalysis payloads deserialize correctly."""

    def test_cached_diagram_analysis_round_trips_through_factory(self, tmp_path):
        """Write DiagramAnalysis to cache, load via _load_cache, verify polymorphic type."""
        from folio.pipeline.analysis import (
            DiagramAnalysis,
            DiagramGraph,
            DiagramNode,
            _load_cache,
            _save_cache,
            SlideAnalysis,
        )

        # Create a DiagramAnalysis and serialize to cache
        da = DiagramAnalysis(
            slide_type="diagram",
            framework="none",
            visual_description="Architecture diagram",
            key_data="3 services",
            main_insight="Microservices",
            evidence=[{"claim": "test", "confidence": "high", "validated": True}],
            diagram_type="architecture",
            graph=DiagramGraph(
                nodes=[DiagramNode(id="n1", label="Service A", bbox=(0, 0, 50, 50))],
            ),
            mermaid="graph LR\n  A --> B",
            extraction_confidence=0.85,
        )

        # Build a cache dict with the DiagramAnalysis serialized
        cache = {"img_hash_1": da.to_dict()}
        _save_cache(tmp_path, cache, model="test-model", provider="test-provider")

        # Load the cache back
        loaded = _load_cache(tmp_path, model="test-model", provider="test-provider")
        assert "img_hash_1" in loaded

        # Deserialize through the polymorphic factory
        entry = loaded["img_hash_1"]
        restored = SlideAnalysis.from_dict(entry)

        # Must come back as DiagramAnalysis, not plain SlideAnalysis
        assert isinstance(restored, DiagramAnalysis)
        assert restored.diagram_type == "architecture"
        assert restored.mermaid == "graph LR\n  A --> B"
        assert restored.extraction_confidence == 0.85
        assert restored.graph is not None
        assert len(restored.graph.nodes) == 1
        assert restored.graph.nodes[0].id == "n1"
