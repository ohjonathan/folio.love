"""Provider registry.

Maps provider names to singleton adapter instances (spec §5.4).
"""

from __future__ import annotations

from .types import AnalysisProvider
from .providers import AnthropicAnalysisProvider, OpenAIAnalysisProvider, GoogleAnalysisProvider


_PROVIDERS: dict[str, AnalysisProvider] = {
    "anthropic": AnthropicAnalysisProvider(),
    "openai": OpenAIAnalysisProvider(),
    "google": GoogleAnalysisProvider(),
}


def get_provider(name: str) -> AnalysisProvider:
    """Look up a provider by name.

    Raises:
        ValueError: if the provider name is not registered.
    """
    provider = _PROVIDERS.get(name)
    if provider is None:
        available = ", ".join(sorted(_PROVIDERS.keys()))
        raise ValueError(f"Unknown LLM provider '{name}'. Available: {available}")
    return provider


def list_providers() -> list[str]:
    """Return sorted list of registered provider names."""
    return sorted(_PROVIDERS.keys())

