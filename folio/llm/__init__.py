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

__all__ = [
    "AnalysisProvider",
    "ErrorDisposition",
    "ExecutionProfile",
    "ImagePart",
    "ProviderInput",
    "ProviderOutput",
    "ProviderRuntimeSettings",
    "ResolvedLLMProfile",
    "ResolvedLLMRoute",
    "StageLLMMetadata",
    "TokenUsage",
    "get_provider",
    "list_providers",
]
