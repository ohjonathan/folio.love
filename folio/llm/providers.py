"""LLM provider adapters.

Each adapter encapsulates provider-specific SDK logic behind the
AnalysisProvider protocol.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any
from urllib.parse import urlparse

from .runtime import RateLimiter, execute_with_retry
from .types import (
    AnalysisProvider,
    ErrorDisposition,
    ImagePart,
    ProviderInput,
    ProviderOutput,
    ProviderRuntimeSettings,
    TokenUsage,
)

logger = logging.getLogger(__name__)
_PREFLIGHT_TIMEOUT_SECONDS = 5.0


def _parse_retry_after(headers) -> float | None:
    """Extract Retry-After seconds from response headers."""
    if headers is None:
        return None
    val = None
    if hasattr(headers, "get"):
        val = headers.get("retry-after") or headers.get("Retry-After")
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _resolve_base_url(base_url_env: str) -> str | None:
    """Resolve an optional custom gateway base URL from the environment."""
    if not base_url_env:
        return None
    value = os.environ.get(base_url_env, "").strip()
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.hostname:
        logger.warning(
            "Environment variable %s does not look like a URL; ignoring it: %s",
            base_url_env,
            _truncate_message(value, max_chars=120),
        )
        return None
    return value


def _preflight_input(*, require_store_false: bool) -> ProviderInput:
    """Build a minimal text-only request for warning-only preflight probes."""
    return ProviderInput(
        prompt="Respond with OK.",
        images=(),
        max_tokens=1,
        temperature=0.0,
        require_store_false=require_store_false,
        timeout_seconds=_PREFLIGHT_TIMEOUT_SECONDS,
    )


def _format_preflight_error(exc: Exception) -> str:
    """Render a compact warning reason for model preflight failures."""
    message = str(exc).strip()
    return _truncate_message(message or type(exc).__name__)


def _truncate_message(message: str, max_chars: int = 200) -> str:
    """Clamp long warning text to keep logs readable."""
    text = message.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _uses_custom_openai_base_url(client: Any) -> bool:
    """Detect whether an OpenAI client targets a non-default base URL."""
    base_url = getattr(client, "base_url", None)
    if base_url is None:
        return False
    text = str(base_url).strip()
    if not text:
        return False
    parsed = urlparse(text)
    hostname = parsed.hostname
    if not hostname:
        return False
    return hostname != "api.openai.com"


def _preflight_settings(
    settings: ProviderRuntimeSettings | None,
) -> ProviderRuntimeSettings:
    """Build a bounded runtime profile for warning-only preflight probes."""
    base = settings or ProviderRuntimeSettings()
    return ProviderRuntimeSettings(
        rate_limit_rpm=base.rate_limit_rpm,
        rate_limit_tpm=base.rate_limit_tpm,
        max_attempts=1,
        base_delay_seconds=base.base_delay_seconds,
        max_delay_seconds=min(base.max_delay_seconds, 1.0),
        allowed_endpoints=base.allowed_endpoints,
        excluded_endpoints=base.excluded_endpoints,
        require_store_false=base.require_store_false,
    )


def _openai_lookup_client(client: Any, timeout_seconds: float) -> Any | None:
    """Build a per-request timeout-scoped OpenAI client when supported."""
    with_options = getattr(client, "with_options", None)
    if not callable(with_options):
        return None
    configured = with_options(timeout=timeout_seconds)
    return configured if configured is not None else None


def _run_runtime_preflight(
    provider: AnalysisProvider,
    client: Any,
    model: str,
    settings: ProviderRuntimeSettings | None,
) -> str | None:
    """Run a bounded text-only probe through the normal runtime guardrails."""
    runtime_settings = _preflight_settings(settings)
    limiter = RateLimiter(
        rpm_limit=runtime_settings.rate_limit_rpm,
        tpm_limit=runtime_settings.rate_limit_tpm,
    )
    inp = _preflight_input(
        require_store_false=runtime_settings.require_store_false,
    )
    try:
        execute_with_retry(provider, client, model, inp, runtime_settings, limiter)
        return None
    except Exception as exc:
        return _format_preflight_error(exc)


class AnthropicAnalysisProvider:
    """Anthropic Claude provider adapter."""

    provider_name: str = "anthropic"
    endpoint_name: str = "messages"

    def create_client(
        self,
        api_key_env: str = "",
        base_url_env: str = "",
    ) -> Any:
        """Create an Anthropic client with SDK auto-retry disabled."""
        import anthropic

        env_var = api_key_env or "ANTHROPIC_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable not set")

        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "max_retries": 0,  # Folio manages retries
        }
        resolved_base_url = _resolve_base_url(base_url_env)
        if resolved_base_url:
            kwargs["base_url"] = resolved_base_url

        return anthropic.Anthropic(**kwargs)

    def preflight(
        self,
        client: Any,
        model: str,
        settings: ProviderRuntimeSettings | None = None,
    ) -> str | None:
        """Probe Anthropic model availability with a minimal text-only call."""
        return _run_runtime_preflight(self, client, model, settings)

    def analyze(
        self,
        client: Any,
        model: str,
        inp: ProviderInput,
    ) -> ProviderOutput:
        """Run analysis via Anthropic Messages API.

        Formats one user message with one text block and one image block
        per ImagePart. Ignores ImagePart.detail (Anthropic does not expose
        per-image detail tuning).
        """
        content: list[dict] = []

        # Image blocks first
        for image_part in inp.images:
            image_data = base64.b64encode(image_part.image_data).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_part.media_type,
                    "data": image_data,
                },
            })

        # Text block
        content.append({
            "type": "text",
            "text": inp.prompt,
        })

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": inp.max_tokens,
            "timeout": inp.timeout_seconds or 120.0,
            "messages": [{"role": "user", "content": content}],
            "temperature": inp.temperature,
        }
        if inp.system_prompt:
            kwargs["system"] = inp.system_prompt

        response = client.messages.create(**kwargs)

        truncated = getattr(response, "stop_reason", None) == "max_tokens"
        raw_text = response.content[0].text

        # Extract token usage
        usage = TokenUsage()
        resp_usage = getattr(response, "usage", None)
        if resp_usage:
            input_tokens = getattr(resp_usage, "input_tokens", 0) or 0
            output_tokens = getattr(resp_usage, "output_tokens", 0) or 0
            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            )

        return ProviderOutput(
            raw_text=raw_text,
            truncated=truncated,
            provider_name=self.provider_name,
            model_name=model,
            usage=usage,
        )

    def classify_error(self, exc: Exception) -> ErrorDisposition:
        """Classify Anthropic exceptions per spec §6.3."""
        try:
            import anthropic
        except ImportError:
            return ErrorDisposition.permanent()

        retry_after = None
        if hasattr(exc, "response") and hasattr(exc.response, "headers"):
            retry_after = _parse_retry_after(exc.response.headers)

        # Transient: retry / fallback eligible
        if isinstance(exc, anthropic.RateLimitError):
            return ErrorDisposition.transient(retry_after)
        if isinstance(exc, anthropic.InternalServerError):
            return ErrorDisposition.transient(retry_after)
        if isinstance(exc, anthropic.APIConnectionError):
            return ErrorDisposition.transient()
        if isinstance(exc, anthropic.APITimeoutError):
            return ErrorDisposition.transient()
        # Permanent: do NOT retry or fall back
        if isinstance(exc, anthropic.AuthenticationError):
            return ErrorDisposition.permanent()
        if isinstance(exc, anthropic.PermissionDeniedError):
            return ErrorDisposition.permanent()
        if isinstance(exc, anthropic.BadRequestError):
            return ErrorDisposition.permanent()
        # Default: treat unknown as permanent
        return ErrorDisposition.permanent()


class OpenAIAnalysisProvider:
    """OpenAI GPT provider adapter."""

    provider_name: str = "openai"
    endpoint_name: str = "chat_completions"

    def create_client(
        self,
        api_key_env: str = "",
        base_url_env: str = "",
    ) -> Any:
        """Create an OpenAI client."""
        from openai import OpenAI

        env_var = api_key_env or "OPENAI_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable not set")

        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "max_retries": 0,
        }
        resolved_base_url = _resolve_base_url(base_url_env)
        if resolved_base_url:
            kwargs["base_url"] = resolved_base_url

        return OpenAI(**kwargs)

    def preflight(
        self,
        client: Any,
        model: str,
        settings: ProviderRuntimeSettings | None = None,
    ) -> str | None:
        """Probe OpenAI model availability and execution capability."""
        lookup_error: Exception | None = None
        lookup_client = _openai_lookup_client(client, _PREFLIGHT_TIMEOUT_SECONDS)
        if lookup_client is not None:
            try:
                lookup_client.models.retrieve(model)
                if not _uses_custom_openai_base_url(client):
                    return None
            except Exception as exc:
                lookup_error = exc

        reason = _run_runtime_preflight(self, client, model, settings)
        if reason is None:
            return None
        if lookup_error is not None:
            return f"{reason} (lookup also failed: {_format_preflight_error(lookup_error)})"
        return reason

    def analyze(
        self,
        client: Any,
        model: str,
        inp: ProviderInput,
    ) -> ProviderOutput:
        """Run analysis via OpenAI Chat Completions API with vision.

        Builds one user message with one text content part and one
        image_url part per ImagePart. Uses data URI base64 encoding.
        """
        content: list[dict] = []

        # Image parts
        for image_part in inp.images:
            image_data = base64.b64encode(image_part.image_data).decode("utf-8")
            detail = image_part.detail or "auto"
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_part.media_type};base64,{image_data}",
                    "detail": detail,
                },
            })

        # Text part
        content.append({
            "type": "text",
            "text": inp.prompt,
        })

        messages: list[dict[str, Any]] = []
        if inp.system_prompt:
            messages.append({"role": "system", "content": inp.system_prompt})
        messages.append({"role": "user", "content": content})

        kwargs: dict[str, Any] = {
            "model": model,
            "timeout": inp.timeout_seconds or 120.0,
            "messages": messages,
        }
        # GPT-5.x: uses max_completion_tokens, does not accept temperature
        if model.startswith("gpt-5"):
            kwargs["max_completion_tokens"] = inp.max_tokens
        else:
            kwargs["max_tokens"] = inp.max_tokens
            kwargs["temperature"] = inp.temperature
        if inp.require_store_false:
            kwargs["store"] = False

        response = client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        truncated = getattr(choice, "finish_reason", None) == "length"
        raw_text = choice.message.content or ""

        # Extract token usage
        usage = TokenUsage()
        resp_usage = getattr(response, "usage", None)
        if resp_usage:
            input_tokens = getattr(resp_usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(resp_usage, "completion_tokens", 0) or 0
            total_tokens = getattr(resp_usage, "total_tokens", 0) or 0
            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens or (input_tokens + output_tokens),
            )

        return ProviderOutput(
            raw_text=raw_text,
            truncated=truncated,
            provider_name=self.provider_name,
            model_name=model,
            usage=usage,
        )

    def classify_error(self, exc: Exception) -> ErrorDisposition:
        """Classify OpenAI exceptions per spec §6.3."""
        try:
            from openai import (
                RateLimitError, APIConnectionError, APITimeoutError,
                InternalServerError, AuthenticationError,
                PermissionDeniedError, BadRequestError,
            )
        except ImportError:
            return ErrorDisposition.permanent()

        retry_after = None
        if hasattr(exc, "response") and hasattr(exc.response, "headers"):
            retry_after = _parse_retry_after(exc.response.headers)

        # Transient: retry / fallback eligible
        if isinstance(exc, RateLimitError):
            return ErrorDisposition.transient(retry_after)
        if isinstance(exc, APIConnectionError):
            return ErrorDisposition.transient()
        if isinstance(exc, APITimeoutError):
            return ErrorDisposition.transient()
        if isinstance(exc, InternalServerError):
            return ErrorDisposition.transient(retry_after)
        # Permanent: do NOT retry or fall back
        if isinstance(exc, AuthenticationError):
            return ErrorDisposition.permanent()
        if isinstance(exc, PermissionDeniedError):
            return ErrorDisposition.permanent()
        if isinstance(exc, BadRequestError):
            return ErrorDisposition.permanent()
        # Default: treat unknown as permanent
        return ErrorDisposition.permanent()


class GoogleAnalysisProvider:
    """Google Gemini provider adapter."""

    provider_name: str = "google"
    endpoint_name: str = "generate_content"

    def create_client(
        self,
        api_key_env: str = "",
        base_url_env: str = "",
    ) -> Any:
        """Create a Google GenAI client."""
        from google import genai

        env_var = api_key_env or "GEMINI_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable not set")

        kwargs: dict[str, Any] = {
            "api_key": api_key,
        }
        resolved_base_url = _resolve_base_url(base_url_env)
        if resolved_base_url:
            kwargs["http_options"] = {"base_url": resolved_base_url}

        return genai.Client(**kwargs)

    def preflight(
        self,
        client: Any,
        model: str,
        settings: ProviderRuntimeSettings | None = None,
    ) -> str | None:
        """Probe Google model availability with lookup when supported."""
        lookup_error: Exception | None = None
        models_api = getattr(client, "models", None)
        model_getter = getattr(models_api, "get", None)
        if callable(model_getter):
            try:
                model_getter(
                    name=model,
                    config={"http_options": {"timeout": _PREFLIGHT_TIMEOUT_SECONDS}},
                )
                return None
            except Exception as exc:
                lookup_error = exc

        reason = _run_runtime_preflight(self, client, model, settings)
        if reason is None:
            return None
        if lookup_error is not None:
            return f"{reason} (lookup also failed: {_format_preflight_error(lookup_error)})"
        return reason

    def analyze(
        self,
        client: Any,
        model: str,
        inp: ProviderInput,
    ) -> ProviderOutput:
        """Run analysis via Google GenAI API.

        Uses one text part and one inline image part per ImagePart.
        When any image has detail="high", sets request-level high media
        resolution on GenerateContentConfig.
        """
        from google.genai import types

        contents = []

        # Image parts
        for image_part in inp.images:
            contents.append(
                types.Part.from_bytes(
                    data=image_part.image_data,
                    mime_type=image_part.media_type,
                )
            )

        # Text part
        contents.append(inp.prompt)

        # Config
        config_kwargs: dict[str, Any] = {
            "max_output_tokens": inp.max_tokens,
            "http_options": {"timeout": int((inp.timeout_seconds or 120.0) * 1000)},
            "temperature": inp.temperature,
        }
        if inp.system_prompt:
            config_kwargs["system_instruction"] = inp.system_prompt

        # High media resolution when any image requests it
        any_high = any(
            img.detail == "high" for img in inp.images
        )
        if any_high:
            # Use SDK enum per Gemini API docs; string fallback for older SDK versions
            try:
                config_kwargs["media_resolution"] = types.MediaResolution.MEDIA_RESOLUTION_HIGH
            except AttributeError:
                config_kwargs["media_resolution"] = "MEDIA_RESOLUTION_HIGH"

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        raw_text = response.text or ""
        # Gemini uses finish_reason STOP for normal, MAX_TOKENS for truncated
        truncated = False
        if response.candidates:
            finish = getattr(response.candidates[0], "finish_reason", None)
            if finish and str(finish).upper() == "MAX_TOKENS":
                truncated = True

        # Extract token usage
        usage = TokenUsage()
        usage_meta = getattr(response, "usage_metadata", None)
        if usage_meta:
            input_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0
            total_tokens = getattr(usage_meta, "total_token_count", 0) or 0
            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens or (input_tokens + output_tokens),
            )

        return ProviderOutput(
            raw_text=raw_text,
            truncated=truncated,
            provider_name=self.provider_name,
            model_name=model,
            usage=usage,
        )

    def classify_error(self, exc: Exception) -> ErrorDisposition:
        """Classify Google GenAI exceptions per spec §6.3."""
        exc_name = type(exc).__name__
        # Transient: retry / fallback eligible
        # Google does not consistently expose Retry-After
        if "ResourceExhausted" in exc_name or "429" in str(exc):
            return ErrorDisposition.transient()
        if "ServiceUnavailable" in exc_name:
            return ErrorDisposition.transient()
        if "InternalServerError" in exc_name or "InternalError" in exc_name:
            return ErrorDisposition.transient()
        if "DeadlineExceeded" in exc_name:
            return ErrorDisposition.transient()
        # Permanent
        if "PermissionDenied" in exc_name:
            return ErrorDisposition.permanent()
        return ErrorDisposition.permanent()
