"""Provider registry.

Maps provider names to adapter classes. Thin lookup layer.
"""

from __future__ import annotations

from typing import Type

from .types import AnalysisProvider
from .providers import AnthropicAnalysisProvider, OpenAIAnalysisProvider, GoogleAnalysisProvider


_PROVIDERS: dict[str, Type] = {
    "anthropic": AnthropicAnalysisProvider,
    "openai": OpenAIAnalysisProvider,
    "google": GoogleAnalysisProvider,
}


def get_provider(name: str) -> AnalysisProvider:
    """Look up and instantiate a provider by name.

    Raises:
        ValueError: if the provider name is not registered.
    """
    cls = _PROVIDERS.get(name)
    if cls is None:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        raise ValueError(f"Unknown LLM provider '{name}'. Available: {available}")
    return cls()


def list_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(_PROVIDERS.keys())
