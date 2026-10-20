"""
AdaptiveLearnSE Component 3 — LLM Provider Factory
Resolves the active provider from environment configuration. There is no simulated fallback:
an unknown provider name raises, and an unconfigured provider reports that it is unavailable.
"""

import os

from .base import BaseLLMProvider
from .gemini_provider import GeminiProvider
from .local_provider import LocalLLMProvider
from .openai_provider import OpenAIProvider

DEFAULT_PROVIDER = "gemini"
SUPPORTED_PROVIDERS = ("gemini", "openai", "local")

_provider_registry: dict[str, BaseLLMProvider] = {}


class UnknownProviderError(ValueError):
    """Raised when C3_LLM_PROVIDER names a provider that does not exist."""


def normalise_provider_name(provider_type: str | None = None) -> str:
    name = (provider_type or os.getenv("C3_LLM_PROVIDER", DEFAULT_PROVIDER)).lower().strip()
    if name == "ollama":
        name = "local"
    if name not in SUPPORTED_PROVIDERS:
        raise UnknownProviderError(
            f"Unsupported LLM provider '{name}'. Supported: {', '.join(SUPPORTED_PROVIDERS)} "
            "(set C3_LLM_PROVIDER)."
        )
    return name


def get_llm_provider(provider_type: str | None = None) -> BaseLLMProvider:
    """Return the singleton for the requested provider (default: C3_LLM_PROVIDER, else gemini)."""
    name = normalise_provider_name(provider_type)
    if name not in _provider_registry:
        if name == "gemini":
            _provider_registry[name] = GeminiProvider()
        elif name == "openai":
            _provider_registry[name] = OpenAIProvider()
        else:
            _provider_registry[name] = LocalLLMProvider()
    return _provider_registry[name]


def list_available_providers() -> list[dict]:
    """Configuration status of every supported provider (no network calls)."""
    providers = [GeminiProvider(), OpenAIProvider()]
    statuses = [p.health_check() for p in providers]
    local = LocalLLMProvider("local-ollama")
    statuses.append(
        {
            "provider": local.provider_name,
            "configured": bool(os.getenv("OLLAMA_BASE_URL")),
            "status": "optional (requires a running Ollama daemon)",
        }
    )
    return statuses
