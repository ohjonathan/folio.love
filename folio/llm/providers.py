"""LLM provider adapters.

Each adapter encapsulates provider-specific SDK logic behind the
AnalysisProvider protocol.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

from .types import AnalysisProvider, ErrorDisposition, ProviderInput, ProviderOutput

logger = logging.getLogger(__name__)


class AnthropicAnalysisProvider:
    """Anthropic Claude provider adapter."""

    provider_name: str = "anthropic"

    def create_client(self, api_key_env: str = "") -> Any:
        """Create an Anthropic client with SDK auto-retry disabled."""
        import anthropic

        env_var = api_key_env or "ANTHROPIC_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable not set")

        return anthropic.Anthropic(
            api_key=api_key,
            max_retries=0,  # Folio manages retries
        )

    def analyze(
        self,
        client: Any,
        model: str,
        inp: ProviderInput,
    ) -> ProviderOutput:
        """Run analysis via Anthropic Messages API."""
        image_data = base64.b64encode(inp.image_path.read_bytes()).decode("utf-8")
        media_type = "image/png"

        response = client.messages.create(
            model=model,
            max_tokens=inp.max_tokens,
            timeout=120.0,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": inp.prompt,
                    },
                ],
            }],
        )

        truncated = getattr(response, "stop_reason", None) == "max_tokens"
        raw_text = response.content[0].text

        return ProviderOutput(
            raw_text=raw_text,
            truncated=truncated,
            provider_name=self.provider_name,
            model_name=model,
        )

    def classify_error(self, exc: Exception) -> ErrorDisposition:
        """Classify Anthropic exceptions per spec §6.3."""
        try:
            import anthropic
        except ImportError:
            return ErrorDisposition.PERMANENT

        # Transient: retry / fallback eligible
        if isinstance(exc, anthropic.RateLimitError):
            return ErrorDisposition.TRANSIENT
        if isinstance(exc, anthropic.InternalServerError):
            return ErrorDisposition.TRANSIENT
        if isinstance(exc, anthropic.APIConnectionError):
            return ErrorDisposition.TRANSIENT
        if isinstance(exc, anthropic.APITimeoutError):
            return ErrorDisposition.TRANSIENT
        # Permanent: do NOT retry or fall back
        if isinstance(exc, anthropic.AuthenticationError):
            return ErrorDisposition.PERMANENT
        if isinstance(exc, anthropic.PermissionDeniedError):
            return ErrorDisposition.PERMANENT
        if isinstance(exc, anthropic.BadRequestError):
            return ErrorDisposition.PERMANENT
        # Default: treat unknown as permanent
        return ErrorDisposition.PERMANENT


class OpenAIAnalysisProvider:
    """OpenAI GPT provider adapter."""

    provider_name: str = "openai"

    def create_client(self, api_key_env: str = "") -> Any:
        """Create an OpenAI client."""
        from openai import OpenAI

        env_var = api_key_env or "OPENAI_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable not set")

        return OpenAI(
            api_key=api_key,
            max_retries=0,
        )

    def analyze(
        self,
        client: Any,
        model: str,
        inp: ProviderInput,
    ) -> ProviderOutput:
        """Run analysis via OpenAI Chat Completions API with vision."""
        image_data = base64.b64encode(inp.image_path.read_bytes()).decode("utf-8")

        response = client.chat.completions.create(
            model=model,
            max_tokens=inp.max_tokens,
            timeout=120.0,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}",
                        },
                    },
                    {
                        "type": "text",
                        "text": inp.prompt,
                    },
                ],
            }],
        )

        choice = response.choices[0]
        truncated = getattr(choice, "finish_reason", None) == "length"
        raw_text = choice.message.content or ""

        return ProviderOutput(
            raw_text=raw_text,
            truncated=truncated,
            provider_name=self.provider_name,
            model_name=model,
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
            return ErrorDisposition.PERMANENT

        # Transient: retry / fallback eligible
        if isinstance(exc, RateLimitError):
            return ErrorDisposition.TRANSIENT
        if isinstance(exc, APIConnectionError):
            return ErrorDisposition.TRANSIENT
        if isinstance(exc, APITimeoutError):
            return ErrorDisposition.TRANSIENT
        if isinstance(exc, InternalServerError):
            return ErrorDisposition.TRANSIENT
        # Permanent: do NOT retry or fall back
        if isinstance(exc, AuthenticationError):
            return ErrorDisposition.PERMANENT
        if isinstance(exc, PermissionDeniedError):
            return ErrorDisposition.PERMANENT
        if isinstance(exc, BadRequestError):
            return ErrorDisposition.PERMANENT
        # Default: treat unknown as permanent
        return ErrorDisposition.PERMANENT


class GoogleAnalysisProvider:
    """Google Gemini provider adapter."""

    provider_name: str = "google"

    def create_client(self, api_key_env: str = "") -> Any:
        """Create a Google GenAI client."""
        from google import genai

        env_var = api_key_env or "GEMINI_API_KEY"
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"{env_var} environment variable not set")

        return genai.Client(api_key=api_key)

    def analyze(
        self,
        client: Any,
        model: str,
        inp: ProviderInput,
    ) -> ProviderOutput:
        """Run analysis via Google GenAI API."""
        from google.genai import types

        image_bytes = inp.image_path.read_bytes()
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

        response = client.models.generate_content(
            model=model,
            contents=[image_part, inp.prompt],
            config=types.GenerateContentConfig(
                max_output_tokens=inp.max_tokens,
                http_options={"timeout": 120_000},  # 120s, same as Anthropic/OpenAI
            ),
        )

        raw_text = response.text or ""
        # Gemini uses finish_reason STOP for normal, MAX_TOKENS for truncated
        truncated = False
        if response.candidates:
            finish = getattr(response.candidates[0], "finish_reason", None)
            if finish and str(finish).upper() == "MAX_TOKENS":
                truncated = True

        return ProviderOutput(
            raw_text=raw_text,
            truncated=truncated,
            provider_name=self.provider_name,
            model_name=model,
        )

    def classify_error(self, exc: Exception) -> ErrorDisposition:
        """Classify Google GenAI exceptions per spec §6.3."""
        exc_name = type(exc).__name__
        # Transient: retry / fallback eligible
        if "ResourceExhausted" in exc_name or "429" in str(exc):
            return ErrorDisposition.TRANSIENT
        if "ServiceUnavailable" in exc_name:
            return ErrorDisposition.TRANSIENT
        if "InternalServerError" in exc_name or "InternalError" in exc_name:
            return ErrorDisposition.TRANSIENT
        if "DeadlineExceeded" in exc_name:
            return ErrorDisposition.TRANSIENT
        # Permanent
        if "PermissionDenied" in exc_name:
            return ErrorDisposition.PERMANENT
        return ErrorDisposition.PERMANENT
