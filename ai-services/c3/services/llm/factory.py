"""
AdaptiveLearnSE Component 3 — LLM Provider Factory
Resolves the active provider according to environment configuration with zero-cost mock fallback.
"""

import os
from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMUsage
from .mock_provider import MockLLMProvider
from .openai_provider import OpenAIProvider
from .local_provider import LocalLLMProvider

_provider_registry: dict[str, BaseLLMProvider] = {}


def get_llm_provider(provider_type: str | None = None) -> BaseLLMProvider:
    """
    Return singleton instance of requested LLM provider.
    Supported types: 'mock', 'openai', 'local' / 'ollama'.
    Defaults to C3_LLM_PROVIDER env var, falling back to 'mock'.
    """
    p_type = (provider_type or os.getenv("C3_LLM_PROVIDER", "mock")).lower().strip()

    if p_type in _provider_registry:
        return _provider_registry[p_type]

    if p_type == "openai":
        provider = OpenAIProvider()
    elif p_type in ["local", "ollama"]:
        provider = LocalLLMProvider()
    else:
        provider = MockLLMProvider()

    _provider_registry[p_type] = provider
    return provider


def list_available_providers() -> list[dict]:
    """List operational status and configuration across all registered providers."""
    providers = [
        MockLLMProvider("calibrated-mock"),
        OpenAIProvider("openai"),
        LocalLLMProvider("local-ollama")
    ]
    return [p.health_check() for p in providers]
