"""Contract types for the LLM provider abstraction.

All providers must conform to the AnalysisProvider protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Image and token types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImagePart:
    """A single image payload for a provider request."""

    image_data: bytes
    role: str  # "global", "tile_q1", "tile_q2", "tile_q3", "tile_q4", "region"
    media_type: str  # "image/png", "image/jpeg"
    detail: str | None = None  # "auto", "high", or None


@dataclass(frozen=True)
class TokenUsage:
    """Normalized token usage from a provider response."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorDisposition:
    """How the orchestrator should handle a provider error.

    Replaces the former enum with a structured dataclass that can carry
    Retry-After information from provider responses.
    """

    kind: Literal["transient", "permanent"]
    retry_after_seconds: float | None = None

    def __post_init__(self):
        if self.kind not in ("transient", "permanent"):
            raise ValueError(
                f"ErrorDisposition.kind must be 'transient' or 'permanent', "
                f"got {self.kind!r}"
            )

    @classmethod
    def transient(cls, retry_after: float | None = None) -> ErrorDisposition:
        """Convenience: create a transient disposition."""
        return cls(kind="transient", retry_after_seconds=retry_after)

    @classmethod
    def permanent(cls) -> ErrorDisposition:
        """Convenience: create a permanent disposition."""
        return cls(kind="permanent")


# ---------------------------------------------------------------------------
# Provider input / output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderInput:
    """Input payload for a single LLM analysis call.

    Provider adapters receive pre-encoded image bytes via `images`.
    They format provider-native requests but do not decide which
    images to send or resize them.
    """

    prompt: str
    images: tuple[ImagePart, ...] = ()
    max_tokens: int = 4096
    temperature: float = 0.0
    require_store_false: bool = False


@dataclass(frozen=True)
class ProviderOutput:
    """Normalized output from a provider call."""

    raw_text: str
    truncated: bool = False
    provider_name: str = ""
    model_name: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)


# ---------------------------------------------------------------------------
# Provider runtime settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderRuntimeSettings:
    """Per-provider rate-limit and retry configuration."""

    rate_limit_rpm: int = 50
    rate_limit_tpm: int | None = None
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    allowed_endpoints: tuple[str, ...] = ()
    excluded_endpoints: tuple[str, ...] = ()
    require_store_false: bool = False


@dataclass(frozen=True)
class ExecutionProfile:
    """A fully resolved provider + model + settings bundle for runtime use."""

    provider: str
    model: str
    api_key_env: str
    settings: ProviderRuntimeSettings = field(
        default_factory=ProviderRuntimeSettings
    )


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AnalysisProvider(Protocol):
    """Protocol that every LLM provider adapter must satisfy."""

    provider_name: str
    endpoint_name: str  # "messages", "chat_completions", "generate_content"

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
    # PR 2: token tracking for future _extraction_metadata
    usage_total: TokenUsage = field(default_factory=TokenUsage)
    per_slide_usage: dict[int, TokenUsage] = field(default_factory=dict)
