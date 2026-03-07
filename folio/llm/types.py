"""Contract types for the LLM provider abstraction.

All providers must conform to the AnalysisProvider protocol.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable


class ErrorDisposition(enum.Enum):
    """How the orchestrator should handle a provider error."""

    TRANSIENT = "transient"  # Retry / fallback eligible
    PERMANENT = "permanent"  # Do NOT retry or fall back


@dataclass(frozen=True)
class ProviderInput:
    """Input payload for a single LLM analysis call.

    Provider adapters receive this; they are responsible for
    encoding the image and building the provider-native payload.
    """

    image_path: Path
    prompt: str
    max_tokens: int = 2048


@dataclass(frozen=True)
class ProviderOutput:
    """Normalized output from a provider call."""

    raw_text: str
    truncated: bool = False
    provider_name: str = ""
    model_name: str = ""


@runtime_checkable
class AnalysisProvider(Protocol):
    """Protocol that every LLM provider adapter must satisfy."""

    provider_name: str

    def create_client(self, api_key_env: str = "") -> Any:
        """Return a provider-native SDK client instance.

        Args:
            api_key_env: Environment variable name for the API key.
                If empty, the provider uses its default env var.

        Called once per pass. SDK auto-retry MUST be disabled;
        Folio manages its own retry/fallback policy.
        """
        ...

    def analyze(
        self,
        client: Any,
        model: str,
        inp: ProviderInput,
    ) -> ProviderOutput:
        """Run a single analysis call and return normalized output."""
        ...

    def classify_error(self, exc: Exception) -> ErrorDisposition:
        """Classify an exception as transient or permanent."""
        ...


# ---------------------------------------------------------------------------
# Orchestration types (used by config, converter, analysis)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedLLMProfile:
    """A fully resolved profile ready for use."""

    name: str
    provider: str
    model: str
    api_key_env: str


@dataclass(frozen=True)
class ResolvedLLMRoute:
    """A fully resolved route with primary profile and optional fallbacks."""

    primary: ResolvedLLMProfile
    fallbacks: list[ResolvedLLMProfile] = field(default_factory=list)


@dataclass
class StageLLMMetadata:
    """Metadata collected from a single analysis stage (pass)."""

    provider: str = ""
    model: str = ""
    slide_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    fallback_activated: bool = False
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
