"""LLM provider abstraction layer.

Exposes contract types, a registry for provider lookup, and a shared
runtime for rate-limited, retried provider calls.
"""

from .types import (
    AnalysisProvider,
    ErrorDisposition,
    ExecutionProfile,
    ImagePart,
    ProviderInput,
    ProviderOutput,
    ProviderRuntimeSettings,
    ResolvedLLMProfile,
    ResolvedLLMRoute,
    StageLLMMetadata,
    TokenUsage,
)
from .registry import get_provider, list_providers
from .runtime import RateLimiter, execute_with_retry

__all__ = [
    "AnalysisProvider",
    "ErrorDisposition",
    "ExecutionProfile",
    "ImagePart",
    "ProviderInput",
    "ProviderOutput",
    "ProviderRuntimeSettings",
    "RateLimiter",
    "ResolvedLLMProfile",
    "ResolvedLLMRoute",
    "StageLLMMetadata",
    "TokenUsage",
    "execute_with_retry",
    "get_provider",
    "list_providers",
]
