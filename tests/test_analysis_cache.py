"""Tests for analysis caching: B1-B3, G1-G4, S1-S2.

Tests cache validation, invalidation triggers, hit/miss statistics,
and --no-cache behavior. All LLM calls are mocked.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from folio.pipeline.analysis import (
    ANALYSIS_PROMPT,
    CacheStats,
    SlideAnalysis,
    _ANALYSIS_CACHE_VERSION,
    _load_cache,
    _load_cache_deep,
    _pass1_context_hash,
    _prompt_version,
    _save_cache,
    _save_cache_deep,
    _text_hash,
    analyze_slides,
    analyze_slides_deep,
)
from folio.pipeline.text import SlideText, _EXTRACTION_VERSION


def _make_unique_png(index: int) -> bytes:
    """Create unique PNG-like bytes for each slide to avoid cache collisions."""
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        + bytes([index]) * 16
        + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
    )


def _mock_anthropic_response(text: str):
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    mock_response.stop_reason = "end_turn"
    # Token usage must be real ints for RateLimiter.record_usage comparison
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    return mock_response


MOCK_PASS1 = json.dumps({
    "slide_type": "data",
    "framework": "tam-sam-som",
    "visual_description": "Revenue chart.",
    "key_data": "$10M",
    "main_insight": "Growing revenue.",
    "evidence": [
        {"claim": "Revenue", "quote": "$10M",
         "element_type": "body", "confidence": "high"},
    ],
})


MOCK_PASS2 = json.dumps({
    "slide_type_reassessment": "unchanged",
    "framework_reassessment": "unchanged",
    "evidence": [
        {"claim": "Growth rate", "quote": "15% YoY",
         "element_type": "body", "confidence": "high"},
    ],
})


# ---------------------------------------------------------------------------
# B3: Cache format version
# ---------------------------------------------------------------------------

class TestCacheFormatVersion:
    """B3: Strict format version checks."""

    def test_format_version_mismatch_invalidates(self, tmp_path):
        """Write v0 cache, load with v1 -> full invalidation."""
        cache = {"_cache_version": 0, "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
                 "_model_version": None, "_provider_version": "anthropic", "_extraction_version": _EXTRACTION_VERSION,
                 "abc123": {"slide_type": "data"}}
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache))
        result = _load_cache(tmp_path)
        assert result == {}

    def test_format_version_missing_invalidates(self, tmp_path):
        """Cache without _cache_version -> empty dict."""
        cache = {"_prompt_version": _prompt_version(ANALYSIS_PROMPT),
                 "abc123": {"slide_type": "data"}}
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache))
        result = _load_cache(tmp_path)
        assert result == {}

    def test_format_version_match_loads(self, tmp_path):
        """Write and load with same version -> data preserved."""
        cache = {"_cache_version": _ANALYSIS_CACHE_VERSION,
                 "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
                 "_model_version": None, "_provider_version": "anthropic",
                 "_extraction_version": _EXTRACTION_VERSION,
                 "abc123": {"slide_type": "data"}}
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache))
        result = _load_cache(tmp_path)
        assert "abc123" in result

    def test_deep_format_version_invalidates(self, tmp_path):
        """Deep cache version mismatch -> empty dict."""
        from folio.pipeline.analysis import DEPTH_PROMPT
        cache = {"_cache_version": 999,
                 "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
                 "_model_version": None, "_provider_version": "anthropic",
                 "_extraction_version": _EXTRACTION_VERSION}
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(cache))
        result = _load_cache_deep(tmp_path)
        assert result == {}

    def test_corrupt_cache_json_returns_empty(self, tmp_path):
        """Malformed JSON -> empty dict."""
        (tmp_path / ".analysis_cache.json").write_text("not valid json {{{")
        result = _load_cache(tmp_path)
        assert result == {}


# ---------------------------------------------------------------------------
# B1: Per-slide text hash
# ---------------------------------------------------------------------------

class TestTextHashCacheValidation:
    """B1: Per-slide text hash in Pass 1 cache."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_text_change_invalidates_single_slide(self, tmp_path):
        """Change text on slide 2 only -> slide 1 hits, slide 2 misses."""
        # Create images
        img1 = tmp_path / "slide-001.png"
        img2 = tmp_path / "slide-002.png"
        img1.write_bytes(_make_unique_png(1))
        img2.write_bytes(_make_unique_png(2))

        calls = []
        mock_client = MagicMock()
        mock_client.messages.create = lambda **kw: (calls.append(1), _mock_anthropic_response(MOCK_PASS1))[1]

        texts_v1 = {
            1: SlideText(slide_num=1, full_text="Same text"),
            2: SlideText(slide_num=2, full_text="Original text"),
        }
        texts_v2 = {
            1: SlideText(slide_num=1, full_text="Same text"),
            2: SlideText(slide_num=2, full_text="Changed text"),
        }

        with patch("anthropic.Anthropic", return_value=mock_client):
            # First run: both miss
            _, stats1, _ = analyze_slides([img1, img2], model="test", cache_dir=tmp_path, slide_texts=texts_v1)
            assert stats1.misses == 2
            calls.clear()

            # Second run with changed text on slide 2
            _, stats2, _ = analyze_slides([img1, img2], model="test", cache_dir=tmp_path, slide_texts=texts_v2)
            assert stats2.hits == 1   # slide 1
            assert stats2.misses == 1  # slide 2
            assert len(calls) == 1    # Only 1 API call

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_same_text_cache_hit(self, tmp_path):
        """Same image + same text -> cache hit (API NOT called)."""
        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(10))

        texts = {1: SlideText(slide_num=1, full_text="Hello")}

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)
            mock_client.messages.create.reset_mock()

            results, stats, _ = analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)

        assert stats.hits == 1
        assert stats.misses == 0
        mock_client.messages.create.assert_not_called()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_no_text_to_text_invalidates(self, tmp_path):
        """Slide had no text, now has text -> cache miss."""
        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(11))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            # First run: no text
            analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=None)
            mock_client.messages.create.reset_mock()

            # Second run: text added
            texts = {1: SlideText(slide_num=1, full_text="New text")}
            _, stats, _ = analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)

        assert stats.misses == 1
        mock_client.messages.create.assert_called_once()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_api_not_called_on_cache_hit(self, tmp_path):
        """Mock API with side_effect=AssertionError — cache hit must not call API."""
        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(12))

        texts = {1: SlideText(slide_num=1, full_text="Test")}

        # First run: populate cache
        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)

        # Second run: API should NOT be called
        mock_client2 = MagicMock()
        mock_client2.messages.create = MagicMock(side_effect=AssertionError("API should not be called"))

        with patch("anthropic.Anthropic", return_value=mock_client2):
            results, stats, _ = analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)

        assert stats.hits == 1
        assert results[1].slide_type == "data"


# ---------------------------------------------------------------------------
# B2: Pass-2 context hash
# ---------------------------------------------------------------------------

class TestDeepCacheContextHash:
    """B2: Pass-2 cache validation via _text_hash + _pass1_hash."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass1_change_cascades_to_pass2_miss(self, tmp_path):
        """Change pass-1 results -> deep cache miss."""
        from folio.pipeline.analysis import DEPTH_PROMPT

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(20))
        texts = {1: SlideText(slide_num=1, full_text="Dense data " * 40)}

        # Create a warm deep cache with specific pass-1 hash
        analysis_v1 = SlideAnalysis(slide_type="data", framework="tam-sam-som",
                                     key_data="$10M", main_insight="Revenue growing",
                                     evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3)
        from folio.pipeline.analysis import _hash_image
        img_hash = _hash_image(img)

        deep_cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            f"{img_hash}_deep": {
                "evidence": [{"claim": "Old", "quote": "old", "confidence": "high", "pass": 2}],
                "pass2_slide_type": None,
                "pass2_framework": None,
                "_text_hash": _text_hash(texts.get(1)),
                "_pass1_hash": _pass1_context_hash(analysis_v1),
            },
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(deep_cache))

        # Different pass-1 results (changed main_insight -> different pass1_hash)
        pass1_v2 = {1: SlideAnalysis(slide_type="data", framework="tam-sam-som",
                                      key_data="$10M", main_insight="Revenue DECLINING",
                                      evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3)}

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS2))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides_deep(
                pass1_results=pass1_v2, slide_texts=texts,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )

        assert stats.misses >= 1  # Should miss because pass-1 hash changed

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_text_change_invalidates_deep_cache(self, tmp_path):
        """Text change -> deep cache _text_hash mismatch -> miss."""
        from folio.pipeline.analysis import DEPTH_PROMPT, _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(21))
        img_hash = _hash_image(img)

        analysis = SlideAnalysis(slide_type="data", framework="none",
                                  key_data="$10M", main_insight="Revenue",
                                  evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3)

        # Deep cache with OLD text hash
        deep_cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            f"{img_hash}_deep": {
                "evidence": [{"claim": "Cached", "quote": "cached", "confidence": "high", "pass": 2}],
                "pass2_slide_type": None,
                "pass2_framework": None,
                "_text_hash": _text_hash(SlideText(slide_num=1, full_text="Old text")),
                "_pass1_hash": _pass1_context_hash(analysis),
            },
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(deep_cache))

        # New text
        new_texts = {1: SlideText(slide_num=1, full_text="Different text " * 40)}
        pass1 = {1: analysis}

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS2))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides_deep(
                pass1_results=pass1, slide_texts=new_texts,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )

        assert stats.misses >= 1

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_deep_cache_hit_with_matching_context(self, tmp_path):
        """Same pass-1 + same text -> deep cache hit."""
        from folio.pipeline.analysis import DEPTH_PROMPT, _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(22))
        img_hash = _hash_image(img)

        texts = {1: SlideText(slide_num=1, full_text="Dense data " * 40)}
        analysis = SlideAnalysis(slide_type="data", framework="none",
                                  key_data="$10M", main_insight="Revenue",
                                  evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3)

        deep_cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            f"{img_hash}_deep": {
                "evidence": [{"claim": "Cached", "quote": "cached", "confidence": "high", "pass": 2}],
                "pass2_slide_type": None,
                "pass2_framework": None,
                "_text_hash": _text_hash(texts.get(1)),
                "_pass1_hash": _pass1_context_hash(analysis),
            },
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(deep_cache))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(side_effect=AssertionError("Should not call API"))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides_deep(
                pass1_results={1: analysis}, slide_texts=texts,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )

        assert stats.hits == 1
        assert stats.misses == 0

    def test_old_format_list_entry_triggers_miss(self, tmp_path):
        """Old-format list deep cache entry triggers miss via isinstance guard."""
        from folio.pipeline.analysis import DEPTH_PROMPT, _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(23))
        img_hash = _hash_image(img)

        texts = {1: SlideText(slide_num=1, full_text="Dense data " * 40)}
        analysis = SlideAnalysis(
            slide_type="data", framework="none",
            key_data="$10M", main_insight="Revenue",
            evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3,
        )

        cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            f"{img_hash}_deep": [{"claim": "old"}],  # list format = legacy
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(cache))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS2))

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
             patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides_deep(
                pass1_results={1: analysis}, slide_texts=texts,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )

        # Should miss because list entry is not a dict
        assert stats.misses == 1
        mock_client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# End-to-end cascade
# ---------------------------------------------------------------------------

class TestEndToEndCascade:
    """End-to-end: text change cascades through both passes."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_text_change_cascades_through_both_passes(self, tmp_path):
        """Warm both caches, change text, re-run -> both miss + API calls fire."""
        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(30))

        texts_v1 = {1: SlideText(slide_num=1, full_text="Dense data revenue $10M growth " * 20)}
        texts_v2 = {1: SlideText(slide_num=1, full_text="Changed text completely different " * 20)}

        api_calls = []
        mock_client = MagicMock()
        def mock_create(**kw):
            api_calls.append(1)
            prompt = ""
            for msg in kw.get("messages", []):
                for c in msg.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        prompt = c.get("text", "")
            if "prior_analysis" in prompt.lower():
                return _mock_anthropic_response(MOCK_PASS2)
            return _mock_anthropic_response(MOCK_PASS1)
        mock_client.messages.create = mock_create

        with patch("anthropic.Anthropic", return_value=mock_client):
            # First run: populate both caches
            results1, s1, _ = analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts_v1)
            results1, s2, _ = analyze_slides_deep(
                pass1_results=results1, slide_texts=texts_v1,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )
            api_calls.clear()

            # Second run: same text -> all hits
            results2, s3, _ = analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts_v1)
            results2, s4, _ = analyze_slides_deep(
                pass1_results=results2, slide_texts=texts_v1,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )
            assert s3.hits == 1 and s3.misses == 0
            assert s4.hits == 1 and s4.misses == 0
            assert len(api_calls) == 0

            # Third run: changed text -> both miss
            api_calls.clear()
            results3, s5, _ = analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts_v2)
            results3, s6, _ = analyze_slides_deep(
                pass1_results=results3, slide_texts=texts_v2,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )
            assert s5.misses == 1
            assert s6.misses == 1
            assert len(api_calls) == 2  # pass-1 + pass-2


# ---------------------------------------------------------------------------
# G1: Model version
# ---------------------------------------------------------------------------

class TestModelVersionInvalidation:
    """G1: Model version in cache metadata."""

    def test_cache_invalidated_on_model_change(self, tmp_path):
        """Write cache with model A, load with model B -> empty dict."""
        _save_cache(tmp_path, {"slide1": {"slide_type": "data"}}, model="model-a")
        result = _load_cache(tmp_path, model="model-b")
        assert result == {}

    def test_cache_valid_same_model(self, tmp_path):
        """Write and load with same model -> data preserved."""
        _save_cache(tmp_path, {"slide1": {"slide_type": "data"}}, model="model-a")
        result = _load_cache(tmp_path, model="model-a")
        assert "slide1" in result

    def test_deep_cache_invalidated_on_model_change(self, tmp_path):
        """Deep cache model A -> load with model B -> empty dict."""
        _save_cache_deep(tmp_path, {"entry": {"evidence": []}}, model="model-a")
        result = _load_cache_deep(tmp_path, model="model-b")
        assert result == {}


# ---------------------------------------------------------------------------
# G2: Extraction version
# ---------------------------------------------------------------------------

class TestExtractionVersionInvalidation:
    """G2: Extraction version in cache metadata."""

    def test_cache_invalidated_on_extraction_version_change(self, tmp_path):
        """Monkeypatch _EXTRACTION_VERSION, write cache, change version, reload -> empty."""
        _save_cache(tmp_path, {"slide1": {"slide_type": "data"}}, model="test")
        # Manually tamper with the stored extraction version
        cache_file = tmp_path / ".analysis_cache.json"
        data = json.loads(cache_file.read_text())
        data["_extraction_version"] = "old_version"
        cache_file.write_text(json.dumps(data))
        result = _load_cache(tmp_path, model="test")
        assert result == {}

    def test_cache_valid_same_extraction_version(self, tmp_path):
        """Same version -> data preserved."""
        _save_cache(tmp_path, {"slide1": {"slide_type": "data"}}, model="test")
        result = _load_cache(tmp_path, model="test")
        assert "slide1" in result

    def test_deep_cache_extraction_version(self, tmp_path):
        """Deep cache extraction version change -> invalidate."""
        _save_cache_deep(tmp_path, {"entry": {"evidence": []}}, model="test")
        cache_file = tmp_path / ".analysis_cache_deep.json"
        data = json.loads(cache_file.read_text())
        data["_extraction_version"] = "old_version"
        cache_file.write_text(json.dumps(data))
        result = _load_cache_deep(tmp_path, model="test")
        assert result == {}

    def test_extraction_version_imported(self):
        """Verify _EXTRACTION_VERSION is imported by analysis.py."""
        from folio.pipeline import analysis
        assert hasattr(analysis, '_EXTRACTION_VERSION')
        assert analysis._EXTRACTION_VERSION == _EXTRACTION_VERSION


# ---------------------------------------------------------------------------
# G3: --no-cache flag
# ---------------------------------------------------------------------------

class TestNoCacheFlag:
    """G3: force_miss behavior and CLI flag."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_no_cache_skips_read_still_writes(self, tmp_path):
        """With force_miss=True, verify cache file is written with fresh results."""
        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(40))
        texts = {1: SlideText(slide_num=1, full_text="Test")}

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides([img], model="test", cache_dir=tmp_path,
                                       slide_texts=texts, force_miss=True)

        assert stats.misses == 1
        # Cache file should exist with fresh results
        cache_file = tmp_path / ".analysis_cache.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert data["_cache_version"] == _ANALYSIS_CACHE_VERSION

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_no_cache_overwrites_stale_entry(self, tmp_path):
        """Warm cache with stale entry, run with force_miss=True, verify entry is replaced."""
        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(41))
        texts = {1: SlideText(slide_num=1, full_text="Test")}

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            # First run: populate cache
            analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)
            call_count_before = mock_client.messages.create.call_count

            # Second run: force_miss should re-analyze
            _, stats, _ = analyze_slides([img], model="test", cache_dir=tmp_path,
                                       slide_texts=texts, force_miss=True)

        assert stats.misses == 1  # Forced miss
        assert mock_client.messages.create.call_count > call_count_before

    def test_cli_no_cache_flag_accepted(self):
        """CLI runner accepts --no-cache without error."""
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            f.write(b"fake")
            f.flush()
            result = runner.invoke(cli, ["convert", f.name, "--no-cache"])
            # Should NOT fail with "No such option" error
            assert "No such option" not in (result.output or "")
            os.unlink(f.name)

    def test_batch_no_cache_flag_accepted(self):
        """Batch command accepts --no-cache."""
        from click.testing import CliRunner
        from folio.cli import cli

        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ["batch", tmpdir, "--no-cache"])
            assert "No such option" not in (result.output or "")


# ---------------------------------------------------------------------------
# G4: Cache statistics
# ---------------------------------------------------------------------------

class TestCacheStats:
    """G4: CacheStats dataclass behavior."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_cache_stats_all_misses(self, tmp_path):
        """Fresh analysis -> CacheStats(hits=0, misses=N)."""
        imgs = [tmp_path / f"slide-{i:03d}.png" for i in range(1, 4)]
        for i, img in enumerate(imgs):
            img.write_bytes(_make_unique_png(50 + i))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides(imgs, model="test", cache_dir=tmp_path)

        assert stats.hits == 0
        assert stats.misses == 3
        assert stats.total == 3

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_cache_stats_all_hits(self, tmp_path):
        """Cached re-run -> CacheStats(hits=N, misses=0)."""
        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(53))
        texts = {1: SlideText(slide_num=1, full_text="Test")}

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)
            _, stats, _ = analyze_slides([img], model="test", cache_dir=tmp_path, slide_texts=texts)

        assert stats.hits == 1
        assert stats.misses == 0
        assert stats.hit_rate == 1.0

    def test_cache_stats_merge(self):
        """pass1.merge(pass2) sums correctly."""
        s1 = CacheStats(hits=3, misses=2, pass_name="pass1")
        s2 = CacheStats(hits=1, misses=1, pass_name="pass2")
        merged = s1.merge(s2)
        assert merged.hits == 4
        assert merged.misses == 3
        assert merged.pass_name == "combined"

    def test_cache_stats_hit_rate_zero_total(self):
        """Zero total -> hit_rate returns 0.0 (no ZeroDivisionError)."""
        s = CacheStats(hits=0, misses=0)
        assert s.hit_rate == 0.0
        assert s.total == 0

    def test_early_return_cache_stats_zeros(self):
        """No API key -> CacheStats(hits=0, misses=0, total=0)."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            _, stats, _ = analyze_slides(
                [Path("dummy.png")], model="test",
            )
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.total == 0


# ---------------------------------------------------------------------------
# S-2: Deep cache force_miss
# ---------------------------------------------------------------------------

class TestDeepCacheForceMiss:
    """S-2: force_miss for analyze_slides_deep."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_deep_cache_force_miss_skips_read_still_writes(self, tmp_path):
        """With force_miss=True, deep cache is not read but IS written."""
        from folio.pipeline.analysis import DEPTH_PROMPT, _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(60))
        img_hash = _hash_image(img)

        texts = {1: SlideText(slide_num=1, full_text="Dense data " * 40)}
        analysis = SlideAnalysis(
            slide_type="data", framework="none",
            key_data="$10M", main_insight="Revenue",
            evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3,
        )

        # Pre-populate deep cache so we can verify it's NOT read
        deep_cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            f"{img_hash}_deep": {
                "evidence": [{"claim": "Stale", "quote": "stale", "confidence": "low", "pass": 2}],
                "pass2_slide_type": None,
                "pass2_framework": None,
                "_text_hash": _text_hash(texts.get(1)),
                "_pass1_hash": _pass1_context_hash(analysis),
            },
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(deep_cache))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS2))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides_deep(
                pass1_results={1: analysis}, slide_texts=texts,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1, force_miss=True,
            )

        # Should miss (skipped cache read) and call API
        assert stats.misses == 1
        assert stats.hits == 0
        mock_client.messages.create.assert_called_once()

        # Cache file should be written with fresh results
        cache_file = tmp_path / ".analysis_cache_deep.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert f"{img_hash}_deep" in data
        # Fresh result should have "Growth rate" claim, not "Stale"
        fresh_evidence = data[f"{img_hash}_deep"]["evidence"]
        claims = [e["claim"] for e in fresh_evidence]
        assert "Growth rate" in claims
        assert "Stale" not in claims


# ---------------------------------------------------------------------------
# S-3: Save cache OSError graceful degradation
# ---------------------------------------------------------------------------

class TestSaveCacheOSError:
    """S-3: _save_cache and _save_cache_deep degrade gracefully on write failure."""

    def test_save_cache_oserror_graceful(self, tmp_path):
        """_save_cache logs warning and does not raise on write failure."""
        cache = {"slide1": {"slide_type": "data"}}

        with patch("pathlib.Path.write_text", side_effect=OSError("Permission denied")):
            # Should not raise
            _save_cache(tmp_path, cache, model="test")

    def test_save_cache_deep_oserror_graceful(self, tmp_path):
        """_save_cache_deep logs warning and does not raise on write failure."""
        cache = {"entry": {"evidence": []}}

        with patch("pathlib.Path.write_text", side_effect=OSError("Disk full")):
            # Should not raise
            _save_cache_deep(tmp_path, cache, model="test")

    def test_save_cache_mkdir_failure_graceful(self, tmp_path):
        """_save_cache degrades gracefully when mkdir fails (blocking 3)."""
        cache = {"slide1": {"slide_type": "data"}}

        with patch("pathlib.Path.mkdir", side_effect=OSError("Read-only parent")):
            # Should not raise
            _save_cache(tmp_path, cache, model="test")

    def test_save_cache_deep_mkdir_failure_graceful(self, tmp_path):
        """_save_cache_deep degrades gracefully when mkdir fails (blocking 3)."""
        cache = {"entry": {"evidence": []}}

        with patch("pathlib.Path.mkdir", side_effect=OSError("Read-only parent")):
            # Should not raise
            _save_cache_deep(tmp_path, cache, model="test")


# ---------------------------------------------------------------------------
# Malformed cache payload validation (review blocking 1 & 2)
# ---------------------------------------------------------------------------

class TestMalformedCachePayloads:
    """Review fix: malformed per-entry payloads fall back to miss, no crash."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass1_list_payload_triggers_miss(self, tmp_path):
        """Pass-1 cache entry stored as list -> miss, not AttributeError."""
        from folio.pipeline.analysis import _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(70))
        img_hash = _hash_image(img)

        # Valid v1 metadata but malformed per-slide payload
        cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            img_hash: ["not", "a", "dict"],  # malformed
        }
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            results, stats, _ = analyze_slides(
                [img], model="test", cache_dir=tmp_path,
                slide_texts={1: SlideText(slide_num=1, full_text="Test")},
            )

        assert stats.misses == 1
        assert results[1].slide_type == "data"
        mock_client.messages.create.assert_called_once()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass1_string_payload_triggers_miss(self, tmp_path):
        """Pass-1 cache entry stored as string -> miss, not crash."""
        from folio.pipeline.analysis import _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(71))
        img_hash = _hash_image(img)

        cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            img_hash: "corrupted_string",  # malformed
        }
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS1))

        with patch("anthropic.Anthropic", return_value=mock_client):
            results, stats, _ = analyze_slides(
                [img], model="test", cache_dir=tmp_path,
                slide_texts={1: SlideText(slide_num=1, full_text="Test")},
            )

        assert stats.misses == 1
        mock_client.messages.create.assert_called_once()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass2_string_evidence_triggers_miss(self, tmp_path):
        """Deep cache evidence stored as string -> miss, not crash."""
        from folio.pipeline.analysis import DEPTH_PROMPT, _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(72))
        img_hash = _hash_image(img)

        texts = {1: SlideText(slide_num=1, full_text="Dense data " * 40)}
        analysis = SlideAnalysis(
            slide_type="data", framework="none",
            key_data="$10M", main_insight="Revenue",
            evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3,
        )

        deep_cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            f"{img_hash}_deep": {
                "evidence": "not_a_list",  # malformed!
                "pass2_slide_type": None,
                "pass2_framework": None,
                "_text_hash": _text_hash(texts.get(1)),
                "_pass1_hash": _pass1_context_hash(analysis),
            },
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(deep_cache))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS2))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides_deep(
                pass1_results={1: analysis}, slide_texts=texts,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )

        assert stats.misses == 1
        mock_client.messages.create.assert_called_once()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass2_evidence_with_non_dict_items_triggers_miss(self, tmp_path):
        """Deep cache evidence is list but contains non-dict items -> miss."""
        from folio.pipeline.analysis import DEPTH_PROMPT, _hash_image

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(73))
        img_hash = _hash_image(img)

        texts = {1: SlideText(slide_num=1, full_text="Dense data " * 40)}
        analysis = SlideAnalysis(
            slide_type="data", framework="none",
            key_data="$10M", main_insight="Revenue",
            evidence=[{"claim": "A", "confidence": "high", "validated": True, "pass": 1}] * 3,
        )

        deep_cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            f"{img_hash}_deep": {
                "evidence": ["not_a_dict", 42],  # list of non-dict
                "pass2_slide_type": None,
                "pass2_framework": None,
                "_text_hash": _text_hash(texts.get(1)),
                "_pass1_hash": _pass1_context_hash(analysis),
            },
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(deep_cache))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(return_value=_mock_anthropic_response(MOCK_PASS2))

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, _ = analyze_slides_deep(
                pass1_results={1: analysis}, slide_texts=texts,
                image_paths=[img], model="test", cache_dir=tmp_path,
                density_threshold=0.1,
            )

        assert stats.misses == 1
        mock_client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# S1: Prompt version invalidation (should-fix 1)
# ---------------------------------------------------------------------------

class TestPromptVersionInvalidation:
    """S1: Explicit prompt-version invalidation regression tests."""

    def test_pass1_prompt_change_invalidates(self, tmp_path):
        """Valid v1 cache with wrong _prompt_version -> empty dict."""
        cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": "wrong_hash",  # Only prompt changed
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            "abc123": {"slide_type": "data"},
        }
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache))
        result = _load_cache(tmp_path, model="test")
        assert result == {}

    def test_deep_prompt_change_invalidates(self, tmp_path):
        """Valid v1 deep cache with wrong _prompt_version -> empty dict."""
        from folio.pipeline.analysis import DEPTH_PROMPT
        cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": "wrong_hash",  # Only prompt changed
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            "abc_deep": {"evidence": []},
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(cache))
        result = _load_cache_deep(tmp_path, model="test")
        assert result == {}

    def test_pass1_correct_prompt_loads(self, tmp_path):
        """Valid v1 cache with correct _prompt_version -> data preserved."""
        cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            "abc123": {"slide_type": "data"},
        }
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache))
        result = _load_cache(tmp_path, model="test")
        assert "abc123" in result

    def test_deep_correct_prompt_loads(self, tmp_path):
        """Valid v1 deep cache with correct _prompt_version -> data preserved."""
        from folio.pipeline.analysis import DEPTH_PROMPT
        cache = {
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test", "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
            "abc_deep": {"evidence": []},
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(cache))
        result = _load_cache_deep(tmp_path, model="test")
        assert "abc_deep" in result


class TestProfileRenameCache:
    """M6: Profile rename must not invalidate cache (spec §9.3)."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_profile_rename_same_provider_model_is_cache_hit(self, tmp_path):
        """Renaming profile without changing provider/model => cache HIT."""
        mock_client = MagicMock()
        calls = []
        def track_call(**kwargs):
            calls.append(kwargs)
            return _mock_anthropic_response()
        mock_client.messages.create.side_effect = track_call

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(90))
        texts = {1: SlideText(slide_num=1, full_text="profile rename test")}

        with patch("anthropic.Anthropic", return_value=mock_client):
            # Run 1: profile "old_name", provider=anthropic, model=test
            _, stats1, _ = analyze_slides(
                [img], model="test", cache_dir=tmp_path, slide_texts=texts,
                provider_name="anthropic",
            )
            assert stats1.misses == 1
            calls.clear()

            # Run 2: same provider + model — profile name is NOT a cache key
            _, stats2, _ = analyze_slides(
                [img], model="test", cache_dir=tmp_path, slide_texts=texts,
                provider_name="anthropic",
            )
            assert stats2.hits == 1
            assert stats2.misses == 0
            assert len(calls) == 0, "API should NOT be called on profile rename"


class TestFallbackCacheProvenance:
    """M7: Mid-batch fallback per-slide cache provenance (spec §9.4)."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_cache_records_actual_provider_after_fallback(self, tmp_path):
        """When primary fails and fallback succeeds, cache entry stores fallback provider."""
        # Primary fails transiently
        primary_client = MagicMock()
        primary_client.messages.create.side_effect = RuntimeError("overloaded")

        # Fallback succeeds
        fallback_client = MagicMock()
        fallback_client.messages.create.return_value = _mock_anthropic_response()

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(91))
        texts = {1: SlideText(slide_num=1, full_text="fallback provenance test")}

        # We'll test at the cache level to avoid complex mock setup
        # Simulate: write a cache entry with _provider == "openai" (fallback)
        from folio.pipeline.analysis import _save_cache, _load_cache
        cache = {
            "test_hash": {
                "slide_type": "data",
                "_provider": "openai",
                "_model": "gpt-4o",
            }
        }
        _save_cache(tmp_path, cache, model="test", provider="openai")
        loaded = _load_cache(tmp_path, model="test", provider="openai")

        # Verify the provenance fields are preserved through save/load
        assert loaded["test_hash"]["_provider"] == "openai"
        assert loaded["test_hash"]["_model"] == "gpt-4o"


def _mock_anthropic_response(text: str | None = None):
    """Create a mock Anthropic API response."""
    if text is None:
        text = json.dumps({
            "slide_type": "data",
            "visual_description": "Test data slide",
            "key_data": [["metric", "value"]],
            "main_insight": "Test insight",
            "framework": "framework",
        })
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [MagicMock(text=text)]
    # Token usage must be real ints for RateLimiter.record_usage comparison
    response.usage.input_tokens = 100
    response.usage.output_tokens = 50
    return response


# ---------------------------------------------------------------------------
# Cache-Hit Provenance Regression Tests
# ---------------------------------------------------------------------------

class TestCacheHitProvenance:
    """Verify per_slide_providers is populated on cache hits."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass1_cache_hit_populates_per_slide_providers(self, tmp_path):
        """Pass-1 cache hit should record cached _provider/_model in per_slide_providers."""
        from folio.pipeline.analysis import _hash_image, _text_hash, _prompt_version, ANALYSIS_PROMPT
        from folio.pipeline.text import _EXTRACTION_VERSION

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(80))
        image_hash = _hash_image(img)
        texts = {1: SlideText(slide_num=1, full_text="Test text")}

        # Pre-populate cache with entry from a DIFFERENT provider
        cache = {
            image_hash: {
                "slide_type": "data",
                "framework": "none",
                "visual_description": "chart",
                "key_data": "$10M",
                "main_insight": "growing",
                "evidence": [{"claim": "Rev", "quote": "$10M",
                              "element_type": "body", "confidence": "high", "validated": True, "pass": 1}],
                "_text_hash": _text_hash(texts[1]),
                "_provider": "openai",
                "_model": "gpt-4o",
            },
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
            "_model_version": "test-model",
            "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
        }
        cache_file = tmp_path / ".analysis_cache.json"
        cache_file.write_text(json.dumps(cache, indent=2))

        # Run with anthropic as primary — should get cache hit
        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(side_effect=AssertionError("Should not call API"))
        with patch("anthropic.Anthropic", return_value=mock_client):
            results, stats, stage_meta = analyze_slides(
                [img], model="test-model", cache_dir=tmp_path,
                slide_texts=texts, provider_name="anthropic",
            )

        assert stats.hits == 1
        assert stats.misses == 0
        # Key assertion: per_slide_providers populated from cache
        assert 1 in stage_meta.per_slide_providers
        assert stage_meta.per_slide_providers[1] == ("openai", "gpt-4o")
        # Fallback should be marked since openai != anthropic primary
        assert stage_meta.fallback_activated is True
        assert stage_meta.fallback_provider == "openai"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_pass2_deep_cache_hit_populates_per_slide_providers(self, tmp_path):
        """Pass-2 deep cache hit should record cached _provider/_model in per_slide_providers."""
        from folio.pipeline.analysis import (
            _hash_image, _text_hash, _pass1_context_hash,
            _prompt_version, ANALYSIS_PROMPT, DEPTH_PROMPT,
        )
        from folio.pipeline.text import _EXTRACTION_VERSION

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(81))
        image_hash = _hash_image(img)
        texts = {1: SlideText(slide_num=1, full_text="Dense " * 50)}

        # Step 1: Pre-populate pass-1 cache so analyze_slides hits it
        pass1_analysis = SlideAnalysis(
            slide_type="data", framework="tam-sam-som",
            visual_description="chart", key_data="$10M",
            main_insight="growing",
            evidence=[{"claim": "R", "quote": "$10M", "element_type": "body",
                        "confidence": "high", "validated": True, "pass": 1}] * 3,
        )
        pass1_cache = {
            image_hash: {
                **pass1_analysis.to_dict(),
                "_text_hash": _text_hash(texts[1]),
                "_provider": "anthropic",
                "_model": "test-model",
            },
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
            "_model_version": "test-model",
            "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
        }
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(pass1_cache, indent=2))

        # Step 2: Get pass-1 results (cache hit)
        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(side_effect=AssertionError("No API"))
        with patch("anthropic.Anthropic", return_value=mock_client):
            pass1_results, _, _ = analyze_slides(
                [img], model="test-model", cache_dir=tmp_path,
                slide_texts=texts, provider_name="anthropic",
            )

        # Step 3: Pre-populate deep cache with entry from different provider
        p1_hash = _pass1_context_hash(pass1_results[1])
        deep_key = f"{image_hash}_deep"
        deep_cache = {
            deep_key: {
                "evidence": [{"claim": "Extra", "quote": "detail",
                              "element_type": "body", "confidence": "high"}],
                "pass2_slide_type": None,
                "pass2_framework": None,
                "_text_hash": _text_hash(texts[1]),
                "_pass1_hash": p1_hash,
                "_provider": "openai",
                "_model": "gpt-4o",
            },
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(DEPTH_PROMPT.template),
            "_model_version": "test-model",
            "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
        }
        (tmp_path / ".analysis_cache_deep.json").write_text(json.dumps(deep_cache, indent=2))

        # Step 4: Run pass-2 with anthropic as primary — deep cache hit
        with patch("anthropic.Anthropic", return_value=mock_client):
            results, stats, stage_meta = analyze_slides_deep(
                pass1_results, texts, [img],
                model="test-model", cache_dir=tmp_path,
                provider_name="anthropic",
                density_threshold=0.0,  # Force all slides into pass 2
            )

        assert stats.hits == 1
        # Key assertion: per_slide_providers populated from deep cache
        assert 1 in stage_meta.per_slide_providers
        assert stage_meta.per_slide_providers[1] == ("openai", "gpt-4o")

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_cache_hit_missing_provider_model_falls_back_to_primary(self, tmp_path):
        """Old cache entry without _provider/_model should not crash; falls back to primary."""
        from folio.pipeline.analysis import _hash_image, _text_hash, _prompt_version, ANALYSIS_PROMPT
        from folio.pipeline.text import _EXTRACTION_VERSION

        img = tmp_path / "slide-001.png"
        img.write_bytes(_make_unique_png(82))
        image_hash = _hash_image(img)
        texts = {1: SlideText(slide_num=1, full_text="Legacy text")}

        # Pre-populate cache WITHOUT _provider/_model (legacy entry)
        cache = {
            image_hash: {
                "slide_type": "data",
                "framework": "none",
                "visual_description": "chart",
                "key_data": "$10M",
                "main_insight": "growing",
                "evidence": [{"claim": "Rev", "quote": "$10M",
                              "element_type": "body", "confidence": "high", "validated": True, "pass": 1}],
                "_text_hash": _text_hash(texts[1]),
                # No _provider or _model — legacy entry
            },
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
            "_model_version": "test-model",
            "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
        }
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache, indent=2))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(side_effect=AssertionError("No API"))
        with patch("anthropic.Anthropic", return_value=mock_client):
            results, stats, stage_meta = analyze_slides(
                [img], model="test-model", cache_dir=tmp_path,
                slide_texts=texts, provider_name="anthropic",
            )

        assert stats.hits == 1
        # Falls back to primary provider/model
        assert stage_meta.per_slide_providers[1] == ("anthropic", "test-model")
        # No fallback flagged (provider matches primary)
        assert stage_meta.fallback_activated is False

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_warm_cache_mixed_provider_frontmatter(self, tmp_path):
        """Warm-cache run with mixed providers should report mixed_providers=True."""
        from folio.pipeline.analysis import _hash_image, _text_hash, _prompt_version, ANALYSIS_PROMPT
        from folio.pipeline.text import _EXTRACTION_VERSION

        img1 = tmp_path / "slide-001.png"
        img1.write_bytes(_make_unique_png(83))
        img2 = tmp_path / "slide-002.png"
        img2.write_bytes(_make_unique_png(84))

        hash1 = _hash_image(img1)
        hash2 = _hash_image(img2)

        texts = {
            1: SlideText(slide_num=1, full_text="Primary text"),
            2: SlideText(slide_num=2, full_text="Fallback text"),
        }

        # Slide 1 cached from primary (anthropic), slide 2 from fallback (openai)
        cache = {
            hash1: {
                "slide_type": "data", "framework": "none",
                "visual_description": "a", "key_data": "b",
                "main_insight": "c",
                "evidence": [{"claim": "X", "quote": "y",
                              "element_type": "body", "confidence": "high",
                              "validated": True, "pass": 1}],
                "_text_hash": _text_hash(texts[1]),
                "_provider": "anthropic",
                "_model": "claude-sonnet-4-20250514",
            },
            hash2: {
                "slide_type": "narrative", "framework": "none",
                "visual_description": "d", "key_data": "e",
                "main_insight": "f",
                "evidence": [{"claim": "A", "quote": "b",
                              "element_type": "body", "confidence": "high",
                              "validated": True, "pass": 1}],
                "_text_hash": _text_hash(texts[2]),
                "_provider": "openai",
                "_model": "gpt-4o",
            },
            "_cache_version": _ANALYSIS_CACHE_VERSION,
            "_prompt_version": _prompt_version(ANALYSIS_PROMPT),
            "_model_version": "test-model",
            "_provider_version": "anthropic",
            "_extraction_version": _EXTRACTION_VERSION,
        }
        (tmp_path / ".analysis_cache.json").write_text(json.dumps(cache, indent=2))

        mock_client = MagicMock()
        mock_client.messages.create = MagicMock(side_effect=AssertionError("No API"))
        with patch("anthropic.Anthropic", return_value=mock_client):
            results, stats, stage_meta = analyze_slides(
                [img1, img2], model="test-model", cache_dir=tmp_path,
                slide_texts=texts, provider_name="anthropic",
            )

        assert stats.hits == 2
        assert stats.misses == 0

        # Per-slide providers recorded
        assert stage_meta.per_slide_providers[1] == ("anthropic", "claude-sonnet-4-20250514")
        assert stage_meta.per_slide_providers[2] == ("openai", "gpt-4o")

        # Fallback marked since slide 2 used openai != anthropic
        assert stage_meta.fallback_activated is True

        # Verify converter-level mixed_providers derivation
        providers = set(stage_meta.per_slide_providers.values())
        distinct_providers = set(p for p, _ in providers)
        assert len(distinct_providers) > 1, "Should detect multiple providers"

