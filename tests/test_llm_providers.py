"""Tests for LLM provider abstraction layer."""

import os
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from folio.llm import get_provider, list_providers
from folio.llm.types import (
    AnalysisProvider,
    ErrorDisposition,
    ImagePart,
    ProviderInput,
    ProviderOutput,
    ResolvedLLMProfile,
    ResolvedLLMRoute,
    StageLLMMetadata,
    TokenUsage,
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

            inp = ProviderInput(prompt="Analyze this", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=2048)
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

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=2048)
            output = provider.analyze(mock_client, "test-model", inp)

        assert output.truncated is True

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_analyze_multiple_images(self):
        """Multi-image support: provider embeds all images in request."""
        provider = AnthropicAnalysisProvider()
        mock_client = MagicMock()
        response_text = json.dumps({"slide_type": "data", "framework": "none",
                                     "evidence": [{"claim": "c", "quote": "q"}],
                                     "visual_description": "v", "key_data": "k",
                                     "main_insight": "i"})
        mock_response = make_anthropic_response(response_text)
        mock_client.messages.create.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            imgs = []
            for i in range(3):
                img_path = Path(tmpdir) / f"test_{i}.png"
                img_path.write_bytes(_make_unique_png(100 + i))
                imgs.append(ImagePart(image_data=img_path.read_bytes(), role="global", media_type="image/png"))

            inp = ProviderInput(prompt="Analyze these", images=tuple(imgs), max_tokens=2048)
            output = provider.analyze(mock_client, "test-model", inp)

        assert isinstance(output, ProviderOutput)
        # Verify all 3 images were included in the API call
        call_args = mock_client.messages.create.call_args
        content_parts = call_args.kwargs.get("messages", [{}])[0].get("content", [])
        image_parts = [p for p in content_parts if p.get("type") == "image"]
        assert len(image_parts) == 3, f"Expected 3 images, got {len(image_parts)}"

    def test_classify_error_rate_limit(self):
        provider = AnthropicAnalysisProvider()
        try:
            import anthropic
            exc = anthropic.RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body=None,
            )
            assert provider.classify_error(exc).kind == "transient"
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
            assert provider.classify_error(exc).kind == "permanent"
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_classify_error_generic(self):
        provider = AnthropicAnalysisProvider()
        assert provider.classify_error(RuntimeError("boom")).kind == "permanent"

    def test_classify_error_timeout(self):
        """B1: APITimeoutError must be transient."""
        provider = AnthropicAnalysisProvider()
        try:
            import anthropic
            exc = anthropic.APITimeoutError(request=MagicMock())
            assert provider.classify_error(exc).kind == "transient"
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_classify_error_permission_denied(self):
        """B1: PermissionDeniedError must be permanent."""
        provider = AnthropicAnalysisProvider()
        try:
            import anthropic
            exc = anthropic.PermissionDeniedError(
                message="Forbidden",
                response=MagicMock(status_code=403),
                body=None,
            )
            assert provider.classify_error(exc).kind == "permanent"
        except ImportError:
            pytest.skip("anthropic not installed")


class TestContractTypes:
    """Test data types freeze correctly."""

    def test_provider_input_frozen(self):
        inp = ProviderInput(prompt="Test", images=())
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

    @patch.dict(os.environ, {
        "MY_CUSTOM_KEY": "custom-test-key",
        "ANTHROPIC_BASE_URL": "https://gateway.example/anthropic",
    })
    def test_anthropic_base_url_env(self):
        provider = get_provider("anthropic")
        with patch("anthropic.Anthropic") as mock_cls:
            provider.create_client(
                api_key_env="MY_CUSTOM_KEY",
                base_url_env="ANTHROPIC_BASE_URL",
            )
            mock_cls.assert_called_once_with(
                api_key="custom-test-key",
                base_url="https://gateway.example/anthropic",
                max_retries=0,
            )

    @patch.dict(os.environ, {"OPENAI_API_KEY": "openai-test-key"})
    def test_openai_base_url_env_ignored_when_unset(self):
        provider = get_provider("openai")
        openai_module = MagicMock()
        openai_ctor = MagicMock()
        openai_module.OpenAI = openai_ctor
        with patch.dict(sys.modules, {"openai": openai_module}):
            provider.create_client(base_url_env="OPENAI_BASE_URL")
        openai_ctor.assert_called_once_with(
            api_key="openai-test-key",
            max_retries=0,
        )

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "openai-test-key",
        "OPENAI_BASE_URL": "https://gateway.example/openai/v1",
    })
    def test_openai_base_url_env(self):
        provider = get_provider("openai")
        openai_module = MagicMock()
        openai_ctor = MagicMock()
        openai_module.OpenAI = openai_ctor
        with patch.dict(sys.modules, {"openai": openai_module}):
            provider.create_client(base_url_env="OPENAI_BASE_URL")
        openai_ctor.assert_called_once_with(
            api_key="openai-test-key",
            base_url="https://gateway.example/openai/v1",
            max_retries=0,
        )

    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "gemini-test-key",
        "GEMINI_BASE_URL": "https://gateway.example/google",
    })
    def test_google_base_url_env(self):
        provider = get_provider("google")
        google_module = MagicMock()
        genai_module = MagicMock()
        google_module.genai = genai_module
        with patch.dict(sys.modules, {"google": google_module, "google.genai": genai_module}):
            provider.create_client(base_url_env="GEMINI_BASE_URL")
        genai_module.Client.assert_called_once_with(
            api_key="gemini-test-key",
            http_options={"base_url": "https://gateway.example/google"},
        )

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

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=2048)
            output = provider.analyze(mock_client, "gpt-4o", inp)

        assert isinstance(output, ProviderOutput)
        assert output.provider_name == "openai"
        assert output.model_name == "gpt-4o"
        assert not output.truncated
        data = json.loads(output.raw_text)
        assert data["slide_type"] == "data"

    def test_analyze_multiple_images(self):
        """Multi-image support: OpenAI embeds all images in request."""
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            imgs = []
            for i in range(3):
                img_path = Path(tmpdir) / f"test_{i}.png"
                img_path.write_bytes(_make_unique_png(200 + i))
                imgs.append(ImagePart(image_data=img_path.read_bytes(), role="global", media_type="image/png"))

            inp = ProviderInput(prompt="Analyze", images=tuple(imgs), max_tokens=2048)
            output = provider.analyze(mock_client, "gpt-4o", inp)

        assert isinstance(output, ProviderOutput)
        call_args = mock_client.chat.completions.create.call_args
        content_parts = call_args.kwargs.get("messages", [{}])[0].get("content", [])
        image_parts = [p for p in content_parts if p.get("type") == "image_url"]
        assert len(image_parts) == 3, f"Expected 3 images, got {len(image_parts)}"

    def test_analyze_detects_truncation(self):
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response(
            "partial", finish_reason="length"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(11))

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=2048)
            output = provider.analyze(mock_client, "gpt-4o", inp)

        assert output.truncated is True

    def test_classify_error_generic(self):
        provider = OpenAIAnalysisProvider()
        assert provider.classify_error(RuntimeError("boom")).kind == "permanent"

    def test_gpt5_uses_max_completion_tokens(self):
        """GPT-5 models must use max_completion_tokens instead of max_tokens."""
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(50))

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=4096)
            provider.analyze(mock_client, "gpt-5-turbo", inp)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "max_completion_tokens" in call_kwargs
        assert call_kwargs["max_completion_tokens"] == 4096
        assert "max_tokens" not in call_kwargs

    def test_gpt5_omits_temperature(self):
        """GPT-5 models must not include temperature in the request."""
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(51))

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=4096, temperature=0.0)
            provider.analyze(mock_client, "gpt-5", inp)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "temperature" not in call_kwargs

    def test_non_gpt5_preserves_max_tokens_and_temperature(self):
        """Non-GPT-5 models must use max_tokens and temperature as before."""
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(52))

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=2048, temperature=0.5)
            provider.analyze(mock_client, "gpt-4o", inp)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "max_tokens" in call_kwargs
        assert call_kwargs["max_tokens"] == 2048
        assert "max_completion_tokens" not in call_kwargs
        assert "temperature" in call_kwargs
        assert call_kwargs["temperature"] == 0.5

    def test_classify_error_timeout(self):
        """B2: APITimeoutError must be transient."""
        provider = OpenAIAnalysisProvider()
        try:
            from openai import APITimeoutError
            exc = APITimeoutError(request=MagicMock())
            assert provider.classify_error(exc).kind == "transient"
        except ImportError:
            pytest.skip("openai not installed")

    def test_classify_error_internal_server(self):
        """B2: InternalServerError must be transient."""
        provider = OpenAIAnalysisProvider()
        try:
            from openai import InternalServerError
            exc = InternalServerError(
                message="Internal error",
                response=MagicMock(status_code=500),
                body=None,
            )
            assert provider.classify_error(exc).kind == "transient"
        except ImportError:
            pytest.skip("openai not installed")

    def test_preflight_checks_lookup_and_chat_execution(self):
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = make_openai_response("ok")

        reason = provider.preflight(mock_client, "gpt-4o")

        assert reason is None
        mock_client.models.retrieve.assert_called_once_with("gpt-4o")
        mock_client.chat.completions.create.assert_called_once()

    def test_preflight_falls_back_to_chat_when_lookup_fails(self):
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.models.retrieve.side_effect = RuntimeError("models endpoint unavailable")
        mock_client.chat.completions.create.return_value = make_openai_response("ok")

        reason = provider.preflight(mock_client, "gpt-4o")

        assert reason is None
        mock_client.models.retrieve.assert_called_once_with("gpt-4o")
        mock_client.chat.completions.create.assert_called_once()

    def test_preflight_returns_warning_reason_when_lookup_and_chat_fail(self):
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.models.retrieve.side_effect = RuntimeError("lookup blocked")
        mock_client.chat.completions.create.side_effect = RuntimeError("chat blocked")

        reason = provider.preflight(mock_client, "gpt-4o")

        assert "chat blocked" in reason
        assert "lookup also failed: lookup blocked" in reason

    def test_preflight_warns_when_lookup_succeeds_but_chat_is_blocked(self):
        provider = OpenAIAnalysisProvider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("chat blocked")

        reason = provider.preflight(mock_client, "gpt-4o")

        assert reason == "chat blocked"
        mock_client.models.retrieve.assert_called_once_with("gpt-4o")
        mock_client.chat.completions.create.assert_called_once()


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

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=2048)
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

            inp = ProviderInput(prompt="Analyze", images=(ImagePart(image_data=img.read_bytes(), role="global", media_type="image/png"),), max_tokens=2048)
            with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock(), 'google.genai.types': MagicMock()}):
                import google.genai.types as mock_types
                mock_types.Part.from_bytes.return_value = MagicMock()
                mock_types.GenerateContentConfig.return_value = MagicMock()
                output = provider.analyze(mock_client, "gemini-2.5-pro", inp)

        assert output.truncated is True

    def test_analyze_multiple_images(self):
        """Multi-image support: Google embeds all images via Part.from_bytes."""
        provider = GoogleAnalysisProvider()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = make_google_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            imgs = []
            for i in range(3):
                img_path = Path(tmpdir) / f"test_{i}.png"
                img_path.write_bytes(_make_unique_png((50 + i) % 256))
                imgs.append(ImagePart(image_data=img_path.read_bytes(), role="global", media_type="image/png"))

            inp = ProviderInput(prompt="Analyze", images=tuple(imgs), max_tokens=2048)
            with patch.dict('sys.modules', {'google': MagicMock(), 'google.genai': MagicMock(), 'google.genai.types': MagicMock()}) as mocked:
                import google.genai.types as mock_types
                mock_types.Part.from_bytes.return_value = MagicMock()
                mock_types.GenerateContentConfig.return_value = MagicMock()
                output = provider.analyze(mock_client, "gemini-2.5-pro", inp)

                assert isinstance(output, ProviderOutput)
                # Verify generate_content was called with contents including image parts
                call_args = mock_client.models.generate_content.call_args
                contents = call_args.kwargs.get("contents", [])
                # Contents should have 3 image parts + 1 text part = 4 total
                assert len(contents) >= 4, f"Expected at least 4 content parts (3 images + prompt), got {len(contents)}"

    def test_classify_error_generic(self):
        provider = GoogleAnalysisProvider()
        assert provider.classify_error(RuntimeError("boom")).kind == "permanent"

    def test_classify_error_internal_server(self):
        """B3: InternalServerError must be transient."""
        provider = GoogleAnalysisProvider()
        # Simulate Google's InternalServerError exception
        class InternalServerError(Exception): pass
        assert provider.classify_error(InternalServerError("internal")).kind == "transient"

    def test_classify_error_deadline_exceeded(self):
        """B3: DeadlineExceeded must be transient."""
        provider = GoogleAnalysisProvider()
        class DeadlineExceeded(Exception): pass
        assert provider.classify_error(DeadlineExceeded("timeout")).kind == "transient"

    def test_classify_error_permission_denied(self):
        """B3: PermissionDenied must be permanent."""
        provider = GoogleAnalysisProvider()
        class PermissionDenied(Exception): pass
        assert provider.classify_error(PermissionDenied("forbidden")).kind == "permanent"

    def test_preflight_uses_model_get_when_available(self):
        provider = GoogleAnalysisProvider()
        mock_client = MagicMock()
        mock_client.models.get.return_value = {"name": "gemini-2.5-pro"}

        reason = provider.preflight(mock_client, "gemini-2.5-pro")

        assert reason is None
        mock_client.models.get.assert_called_once_with(name="gemini-2.5-pro")
        mock_client.models.generate_content.assert_not_called()

    def test_preflight_falls_back_to_generate_content_when_lookup_fails(self):
        provider = GoogleAnalysisProvider()
        mock_client = MagicMock()
        mock_client.models.get.side_effect = RuntimeError("lookup unsupported")
        mock_client.models.generate_content.return_value = make_google_response("ok")

        google_module = MagicMock()
        genai_module = MagicMock()
        types_module = MagicMock()
        google_module.genai = genai_module
        genai_module.types = types_module
        types_module.Part.from_bytes.return_value = MagicMock()
        types_module.GenerateContentConfig.return_value = MagicMock()

        with patch.dict(
            sys.modules,
            {"google": google_module, "google.genai": genai_module, "google.genai.types": types_module},
        ):
            reason = provider.preflight(mock_client, "gemini-2.5-pro")

        assert reason is None
        mock_client.models.get.assert_called_once_with(name="gemini-2.5-pro")
        mock_client.models.generate_content.assert_called_once()

    def test_preflight_without_model_get_uses_generate_content(self):
        provider = GoogleAnalysisProvider()
        mock_client = MagicMock()
        del mock_client.models.get
        mock_client.models.generate_content.return_value = make_google_response("ok")

        google_module = MagicMock()
        genai_module = MagicMock()
        types_module = MagicMock()
        google_module.genai = genai_module
        genai_module.types = types_module
        types_module.Part.from_bytes.return_value = MagicMock()
        types_module.GenerateContentConfig.return_value = MagicMock()

        with patch.dict(
            sys.modules,
            {"google": google_module, "google.genai": genai_module, "google.genai.types": types_module},
        ):
            reason = provider.preflight(mock_client, "gemini-2.5-pro")

        assert reason is None
        mock_client.models.generate_content.assert_called_once()


class TestAnthropicPreflight:
    """Test Anthropic warning-only preflight behavior."""

    def test_preflight_uses_messages_path(self):
        provider = AnthropicAnalysisProvider()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_anthropic_response("ok")

        reason = provider.preflight(mock_client, "claude-sonnet-4-20250514")

        assert reason is None
        mock_client.messages.create.assert_called_once()

    def test_preflight_returns_warning_reason(self):
        provider = AnthropicAnalysisProvider()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("model blocked")

        reason = provider.preflight(mock_client, "claude-sonnet-4-20250514")

        assert reason == "model blocked"


class TestRuntimeFallbackChain:
    """Test the _analyze_with_fallback function per spec §6.2."""

    def test_primary_success_skips_fallback(self):
        from folio.pipeline.analysis import _analyze_with_fallback
        provider = AnthropicAnalysisProvider()
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_anthropic_response(
            make_pass1_json()
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(30))

            analysis, used_provider, used_model, _ = _analyze_with_fallback(
                provider, mock_client, img, "claude-sonnet-4-20250514", "anthropic",
            )
        assert analysis.slide_type != "pending"
        assert used_provider == "anthropic"

    def test_primary_transient_failure_triggers_fallback(self):
        from folio.pipeline.analysis import _analyze_with_fallback

        # Primary always fails with transient
        primary = MagicMock()
        primary.provider_name = "anthropic"
        primary.analyze.side_effect = RuntimeError("service unavailable")
        primary.classify_error.return_value = ErrorDisposition.transient()
        primary_client = MagicMock()

        # Fallback succeeds
        fallback = MagicMock()
        fallback.provider_name = "openai"
        fallback.analyze.return_value = ProviderOutput(
            raw_text=make_pass1_json(), truncated=False,
            provider_name="openai", model_name="gpt-4o",
        )
        fallback_client = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(31))

            analysis, used_provider, used_model, _ = _analyze_with_fallback(
                primary, primary_client, img, "claude-sonnet",
                "anthropic",
                fallback_chain=[(fallback, fallback_client, "gpt-4o", "openai")],
            )
        assert analysis.slide_type != "pending"
        assert used_provider == "openai"

    def test_all_exhausted_returns_provider_aware_pending(self):
        from folio.pipeline.analysis import _analyze_with_fallback

        # Both primary and fallback fail
        primary = MagicMock()
        primary.provider_name = "anthropic"
        primary.analyze.side_effect = RuntimeError("overloaded")
        primary.classify_error.return_value = ErrorDisposition.transient()
        primary_client = MagicMock()

        fallback = MagicMock()
        fallback.provider_name = "openai"
        fallback.analyze.side_effect = RuntimeError("overloaded")
        fallback.classify_error.return_value = ErrorDisposition.transient()
        fallback_client = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(32))

            analysis, used_provider, _, _ = _analyze_with_fallback(
                primary, primary_client, img, "claude-sonnet",
                "anthropic",
                fallback_chain=[(fallback, fallback_client, "gpt-4o", "openai")],
            )
        assert analysis.slide_type == "pending"
        assert "all configured providers" in analysis.visual_description

    def test_permanent_failure_does_not_trigger_fallback(self):
        from folio.pipeline.analysis import _analyze_with_fallback

        # Primary fails permanently
        primary = MagicMock()
        primary.provider_name = "anthropic"
        primary.analyze.side_effect = RuntimeError("auth failed")
        primary.classify_error.return_value = ErrorDisposition.permanent()
        primary_client = MagicMock()

        # Fallback should NOT be called
        fallback = MagicMock()
        fallback.provider_name = "openai"
        fallback_client = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(33))

            analysis, used_provider, _, _ = _analyze_with_fallback(
                primary, primary_client, img, "claude-sonnet",
                "anthropic",
                fallback_chain=[(fallback, fallback_client, "gpt-4o", "openai")],
            )
        # Permanent error: fallback must NOT be triggered (spec §6.2)
        assert analysis.slide_type == "pending"
        assert used_provider == "anthropic"  # stayed on primary
        assert "rejected the request" in analysis.visual_description
        fallback.analyze.assert_not_called()


# ---------------------------------------------------------------------------
# Finding 5: Test coverage for new risk surfaces
# ---------------------------------------------------------------------------


class TestPerProviderFallbackSettings:
    """Finding 1+5: Verify each fallback gets its own settings and rate limiter."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "OPENAI_API_KEY": "test-key"})
    def test_fallback_uses_own_provider_settings(self, tmp_path):
        """Fallback OpenAI provider must use OpenAI endpoint allowlist, not Anthropic's."""
        from folio.pipeline.analysis import _analyze_with_fallback
        from folio.llm.types import ProviderRuntimeSettings

        # Primary fails transiently
        primary = MagicMock()
        primary.provider_name = "anthropic"
        primary.endpoint_name = "messages"
        primary.analyze.side_effect = RuntimeError("overloaded")
        primary.classify_error.return_value = ErrorDisposition.transient()
        primary_client = MagicMock()

        # Fallback succeeds
        fallback = MagicMock()
        fallback.provider_name = "openai"
        fallback.endpoint_name = "chat_completions"
        fallback.analyze.return_value = ProviderOutput(
            raw_text=make_pass1_json(), truncated=False,
            provider_name="openai", model_name="gpt-4o",
            usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        )
        fallback_client = MagicMock()

        # Provider-specific settings with different endpoint allowlists
        all_settings = {
            "anthropic": ProviderRuntimeSettings(
                allowed_endpoints=("messages",),
                rate_limit_rpm=50,
            ),
            "openai": ProviderRuntimeSettings(
                allowed_endpoints=("chat_completions",),
                rate_limit_rpm=60,
            ),
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            img = Path(tmpdir) / "test.png"
            img.write_bytes(_make_unique_png(40))

            analysis, used_provider, used_model, usage = _analyze_with_fallback(
                primary, primary_client, img, "claude-sonnet",
                "anthropic",
                fallback_chain=[(fallback, fallback_client, "gpt-4o", "openai")],
                settings=all_settings["anthropic"],
                all_provider_settings=all_settings,
            )

        assert analysis.slide_type != "pending"
        assert used_provider == "openai"
        assert used_model == "gpt-4o"
        # Verify fallback provider's analyze was actually called
        fallback.analyze.assert_called_once()


class TestRequireStoreFalsePropagation:
    """Finding 2+5: Verify require_store_false reaches ProviderInput."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_require_store_false_set_on_provider_input(self, tmp_path):
        """When settings.require_store_false=True, ProviderInput must carry the flag."""
        from folio.pipeline.analysis import _analyze_single_slide
        from folio.llm.types import ProviderRuntimeSettings
        from folio.llm.runtime import RateLimiter

        provider = MagicMock()
        provider.provider_name = "openai"
        provider.endpoint_name = "chat_completions"
        provider.analyze.return_value = ProviderOutput(
            raw_text=make_pass1_json(), truncated=False,
            provider_name="openai", model_name="gpt-4o",
            usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
        )
        client = MagicMock()

        settings = ProviderRuntimeSettings(
            require_store_false=True,
            allowed_endpoints=("chat_completions",),
        )
        limiter = RateLimiter(rpm_limit=60)

        img = tmp_path / "test.png"
        img.write_bytes(_make_unique_png(41))

        # Patch execute_with_retry to capture the ProviderInput
        captured_inputs = []
        def capture_ewr(prov, cl, mod, inp, sett, lim):
            captured_inputs.append(inp)
            return prov.analyze(cl, mod, inp)

        with patch("folio.pipeline.analysis.execute_with_retry", side_effect=capture_ewr):
            _analyze_single_slide(
                provider, client, img, "gpt-4o",
                settings=settings, limiter=limiter,
            )

        assert len(captured_inputs) == 1
        assert captured_inputs[0].require_store_false is True


class TestTokenTotalAggregation:
    """Finding 3+5: Verify total_tokens is accumulated correctly in StageLLMMetadata."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_usage_total_includes_total_tokens(self, tmp_path):
        """stage_meta.usage_total.total_tokens must equal sum of per-slide totals."""
        from folio.pipeline.analysis import analyze_slides
        from folio.pipeline.text import SlideText

        imgs = [tmp_path / f"slide-{i:03d}.png" for i in range(1, 4)]
        for i, img in enumerate(imgs):
            img.write_bytes(_make_unique_png(50 + i))

        # Each call returns 150 total tokens
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_anthropic_response(
            make_pass1_json()
        )

        with patch("anthropic.Anthropic", return_value=mock_client):
            _, stats, meta = analyze_slides(
                imgs, model="test", cache_dir=tmp_path,
            )

        assert stats.misses == 3
        # Each slide contributes 150 total tokens (100 input + 50 output)
        assert meta.usage_total.total_tokens == 450
        assert meta.usage_total.input_tokens == 300
        assert meta.usage_total.output_tokens == 150
