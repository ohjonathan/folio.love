"""LLM provider abstraction layer.

Exposes contract types and a registry for provider lookup.
"""

from .types import (
    AnalysisProvider,
    ErrorDisposition,
    ProviderInput,
    ProviderOutput,
    ResolvedLLMProfile,
    ResolvedLLMRoute,
    StageLLMMetadata,
)
from .registry import get_provider, list_providers

__all__ = [
    "AnalysisProvider",
    "ErrorDisposition",
    "ProviderInput",
    "ProviderOutput",
    "ResolvedLLMProfile",
    "ResolvedLLMRoute",
    "StageLLMMetadata",
    "get_provider",
    "list_providers",
]
