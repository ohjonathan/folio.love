"""Tests for LLM provider abstraction layer."""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from folio.llm import get_provider, list_providers
from folio.llm.types import (
    AnalysisProvider,
    ErrorDisposition,
    ProviderInput,
    ProviderOutput,
    ResolvedLLMProfile,
    ResolvedLLMRoute,
    StageLLMMetadata,
)
from folio.llm.providers import AnthropicAnalysisProvider, OpenAIAnalysisProvider, GoogleAnalysisProvider
from tests.llm_mocks import (
    make_anthropic_response, make_openai_response, make_google_response,
    make_pass1_json,
)


def _make_unique_png(index: int) -> bytes:
    """Create unique PNG-like bytes."""
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        + bytes([index]) * 16
        + b'\x00\x00\x00\x00IEND\xaeB\x60\x82'
    )


class TestRegistry:
    """Test provider registry."""

    def test_get_anthropic(self):
        provider = get_provider("anthropic")
        assert provider.provider_name == "anthropic"
        assert isinstance(provider, AnthropicAnalysisProvider)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider 'bogus'"):
            get_provider("bogus")

    def test_list_providers(self):
        providers = list_providers()
        assert "anthropic" in providers
        assert isinstance(providers, list)

    def test_provider_satisfies_protocol(self):
        provider = get_provider("anthropic")
        assert isinstance(provider, AnalysisProvider)


class TestAnthropicProvider:
    """Test AnthropicAnalysisProvider."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_create_client(self):
        provider = AnthropicAnalysisProvider()
        with patch("anthropic.Anthropic") as mock_cls:
            client = provider.create_client()
            mock_cls.assert_called_once_with(api_key="test-key", max_retries=0)

    def test_create_client_no_key_raises(self):
        provider = AnthropicAnalysisProvider()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                provider.create_client()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_analyze_returns_provider_output(self):
        provider = AnthropicAnalysisProvider()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_anthropic_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(1))

            inp = ProviderInput(image_path=img, prompt="Analyze this", max_tokens=2048)
            output = provider.analyze(mock_client, "test-model", inp)

        assert isinstance(output, ProviderOutput)
        assert output.provider_name == "anthropic"
        assert output.model_name == "test-model"
        assert not output.truncated
        data = json.loads(output.raw_text)
        assert data["slide_type"] == "data"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_analyze_detects_truncation(self):
        provider = AnthropicAnalysisProvider()
        mock_client = MagicMock()
        mock_response = make_anthropic_response("partial", stop_reason="max_tokens")
        mock_client.messages.create.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(2))

            inp = ProviderInput(image_path=img, prompt="Analyze", max_tokens=2048)
            output = provider.analyze(mock_client, "test-model", inp)

        assert output.truncated is True

    def test_classify_error_rate_limit(self):
        provider = AnthropicAnalysisProvider()
        try:
            import anthropic
            exc = anthropic.RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
            assert provider.classify_error(exc) == ErrorDisposition.TRANSIENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_classify_error_auth(self):
        provider = AnthropicAnalysisProvider()
        try:
            import anthropic
            exc = anthropic.AuthenticationError(
                message="Unauthorized",
                response=MagicMock(status_code=401),
                body=None,
            )
            assert provider.classify_error(exc) == ErrorDisposition.PERMANENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_classify_error_generic(self):
        provider = AnthropicAnalysisProvider()
        assert provider.classify_error(RuntimeError("boom")) == ErrorDisposition.PERMANENT


class TestContractTypes:
    """Test data types freeze correctly."""

    def test_provider_input_frozen(self):
        inp = ProviderInput(image_path=Path("/tmp/test.png"), prompt="Test")
        with pytest.raises(AttributeError):
            inp.prompt = "New"  # type: ignore

    def test_provider_output_frozen(self):
        out = ProviderOutput(raw_text="test", truncated=False)
        with pytest.raises(AttributeError):
            out.raw_text = "changed"  # type: ignore

    def test_resolved_profile_frozen(self):
        profile = ResolvedLLMProfile(
            name="default", provider="anthropic",
            model="claude-sonnet-4-20250514", api_key_env="ANTHROPIC_API_KEY",
        )
        with pytest.raises(AttributeError):
            profile.name = "other"  # type: ignore

    def test_stage_metadata_mutable(self):
        meta = StageLLMMetadata()
        meta.provider = "anthropic"
        meta.model = "test"
        assert meta.provider == "anthropic"

    def test_resolved_route(self):
        primary = ResolvedLLMProfile(
            name="default", provider="anthropic",
            model="claude-sonnet-4-20250514", api_key_env="ANTHROPIC_API_KEY",
        )
        fallback = ResolvedLLMProfile(
            name="fallback", provider="openai",
            model="gpt-4o", api_key_env="OPENAI_API_KEY",
        )
        route = ResolvedLLMRoute(primary=primary, fallbacks=[fallback])
        assert route.primary.provider == "anthropic"
        assert len(route.fallbacks) == 1
        assert route.fallbacks[0].provider == "openai"


class TestProviderRegistration:
    """Test that all providers are registered and accessible."""

    def test_openai_registered(self):
        provider = get_provider("openai")
        assert provider.provider_name == "openai"

    def test_google_registered(self):
        provider = get_provider("google")
        assert provider.provider_name == "google"

    def test_list_includes_all(self):
        providers = list_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "google" in providers


class TestBYOCredentialWiring:
    """Test BYO api_key_env support across all adapters."""

    @patch.dict(os.environ, {"MY_CUSTOM_KEY": "custom-test-key"})
    def test_anthropic_custom_env_var(self):
        provider = get_provider("anthropic")
        with patch("anthropic.Anthropic") as mock_cls:
            provider.create_client(api_key_env="MY_CUSTOM_KEY")
            mock_cls.assert_called_once_with(api_key="custom-test-key", max_retries=0)

    def test_anthropic_custom_env_var_missing_raises(self):
        provider = get_provider("anthropic")
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NONEXISTENT_KEY", None)
            with pytest.raises(ValueError, match="NONEXISTENT_KEY"):
                provider.create_client(api_key_env="NONEXISTENT_KEY")

    def test_google_default_env_var_is_gemini(self):
        """Verify Google adapter defaults to GEMINI_API_KEY, not GOOGLE_API_KEY."""
        provider = get_provider("google")
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            try:
                provider.create_client()
            except ImportError:
                pytest.skip("google-genai not installed")
            except ValueError as e:
                assert "GEMINI_API_KEY" in str(e)


class TestPass1ValidationHardening:
    """Test that pass-1 normalization rejects malformed payloads."""

    def test_missing_slide_type_returns_pending(self):
        from folio.pipeline.analysis import _normalize_pass1_json
        # Missing slide_type entirely
        result = _normalize_pass1_json({"framework": "none"})
        assert result.slide_type == "pending"

    def test_empty_slide_type_returns_pending(self):
        from folio.pipeline.analysis import _normalize_pass1_json
        result = _normalize_pass1_json({"slide_type": "", "framework": "none"})
        assert result.slide_type == "pending"

    def test_valid_slide_type_accepted(self):
        from folio.pipeline.analysis import _normalize_pass1_json
        result = _normalize_pass1_json({
            "slide_type": "data", "framework": "none",
            "evidence": [{"claim": "Test", "quote": "test", "confidence": "high"}],
        })
        assert result.slide_type == "data"


class TestCacheProviderInvalidation:
    """Test that provider changes invalidate cache."""

    def test_provider_change_invalidates_pass1_cache(self, tmp_path):
        from folio.pipeline.analysis import _save_cache, _load_cache
        cache = {"some_hash": {"slide_type": "data"}}
        _save_cache(tmp_path, cache, model="test", provider="anthropic")

        # Same provider: should load
        loaded = _load_cache(tmp_path, model="test", provider="anthropic")
        assert "some_hash" in loaded

        # Different provider: should invalidate
        loaded = _load_cache(tmp_path, model="test", provider="openai")
        assert loaded == {}

    def test_provider_change_invalidates_deep_cache(self, tmp_path):
        from folio.pipeline.analysis import _save_cache_deep, _load_cache_deep
        cache = {"some_hash_deep": {"evidence": []}}
        _save_cache_deep(tmp_path, cache, model="test", provider="anthropic")

        loaded = _load_cache_deep(tmp_path, model="test", provider="anthropic")
        assert "some_hash_deep" in loaded

        loaded = _load_cache_deep(tmp_path, model="test", provider="openai")
        assert loaded == {}


class TestOpenAIAdapter:
    """Test OpenAI adapter request/response normalization."""

    def test_analyze_returns_provider_output(self):
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(10))

            inp = ProviderInput(image_path=img, prompt="Analyze", max_tokens=2048)
            output = provider.analyze(mock_client, "gpt-4o", inp)

        assert isinstance(output, ProviderOutput)
        assert output.provider_name == "openai"
        assert output.model_name == "gpt-4o"
        assert not output.truncated
        data = json.loads(output.raw_text)
        assert data["slide_type"] == "data"

    def test_analyze_detects_truncation(self):
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response(
            "partial", finish_reason="length"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(11))

            inp = ProviderInput(image_path=img, prompt="Analyze", max_tokens=2048)
            output = provider.analyze(mock_client, "gpt-4o", inp)

        assert output.truncated is True

    def test_classify_error_generic(self):
        provider = OpenAIAnalysisProvider()
        assert provider.classify_error(RuntimeError("boom")) == ErrorDisposition.PERMANENT


class TestGoogleAdapter:
    """Test Google Gemini adapter request/response normalization."""

    def test_analyze_returns_provider_output(self):
        provider = GoogleAnalysisProvider()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = make_google_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(20))

            inp = ProviderInput(image_path=img, prompt="Analyze", max_tokens=2048)
            # Google adapter imports google.genai.types internally; mock it
            with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock(), 'google.genai.types': MagicMock()}):
                import google.genai.types as mock_types
                mock_types.Part.from_bytes.return_value = MagicMock()
                mock_types.GenerateContentConfig.return_value = MagicMock()
                output = provider.analyze(mock_client, "gemini-2.5-pro", inp)

        assert isinstance(output, ProviderOutput)
        assert output.provider_name == "google"
        assert output.model_name == "gemini-2.5-pro"
        assert not output.truncated
        data = json.loads(output.raw_text)
        assert data["slide_type"] == "data"

    def test_analyze_detects_truncation(self):
        provider = GoogleAnalysisProvider()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = make_google_response(
            "partial", finish_reason="MAX_TOKENS"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(21))

            inp = ProviderInput(image_path=img, prompt="Analyze", max_tokens=2048)
            with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock(), 'google.genai.types': MagicMock()}):
                import google.genai.types as mock_types
                mock_types.Part.from_bytes.return_value = MagicMock()
                mock_types.GenerateContentConfig.return_value = MagicMock()
                output = provider.analyze(mock_client, "gemini-2.5-pro", inp)

        assert output.truncated is True

    def test_classify_error_generic(self):
        provider = GoogleAnalysisProvider()
        assert provider.classify_error(RuntimeError("boom")) == ErrorDisposition.PERMANENT
