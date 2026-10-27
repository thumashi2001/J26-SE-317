"""
AdaptiveLearnSE Component 3 — LLM Provider Factory
Resolves the active provider from environment configuration. There is no simulated fallback:
an unknown provider name raises, and an unconfigured provider reports that it is unavailable.

STATUS: used by /health and by offline experiments to choose a provider (C3_LLM_PROVIDER = gemini | openai | local |
groq | openrouter | deepseek | cerebras | mistral).
The live marking path does not call get_llm_provider().
"""

import os
from collections.abc import Callable

from .base import BaseLLMProvider
from .gemini_provider import GeminiProvider
from .local_provider import LocalLLMProvider
from .openai_provider import OpenAIProvider

DEFAULT_PROVIDER = "gemini"

# OpenAI-compatible hosts (same /chat/completions protocol) served by OpenAIProvider with a different base URL and key.
# name -> (base URL, API-key env var, default model). The default models are starting points: free-tier model lists
# change often, so set C3_<NAME>_MODEL after checking the provider's current list. Free-tier limits are NOT hard-coded
# here; set C3_LLM_RPM_<NAME> to stay under whatever the provider currently allows.
OPENAI_COMPATIBLE_PRESETS: dict[str, tuple[str, str, str]] = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "xingchen-agi/xing4.0-29b-a4b:free"),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY", "deepseek-chat"),
    "cerebras": ("https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", "llama-3.3-70b"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-small-latest"),
}
SUPPORTED_PROVIDERS = ("gemini", "openai", "local", *OPENAI_COMPATIBLE_PRESETS)

# One provider object per name is created on first use and then reused (a simple singleton registry).
_provider_registry: dict[str, BaseLLMProvider] = {}


def _build_compatible(name: str) -> BaseLLMProvider:
    """An OpenAI-compatible host: same protocol as OpenAI, with its own base URL, key variable and default model."""
    base_url, key_env, default_model = OPENAI_COMPATIBLE_PRESETS[name]
    return OpenAIProvider(
        provider_name=name,
        base_url=os.getenv(f"{name.upper()}_BASE_URL", base_url),
        model=os.getenv(f"C3_{name.upper()}_MODEL", default_model),
        key_env=key_env,
    )


# How to build each provider. Adding a provider means adding one entry here (or one preset above); get_llm_provider
# itself never has to change (open for extension, closed for modification).
_BUILDERS: dict[str, Callable[[str], BaseLLMProvider]] = {
    "gemini": lambda _name: GeminiProvider(),
    "openai": lambda _name: OpenAIProvider(),
    "local": lambda _name: LocalLLMProvider(),
    **dict.fromkeys(OPENAI_COMPATIBLE_PRESETS, _build_compatible),
}


class UnknownProviderError(ValueError):
    """Raised when C3_LLM_PROVIDER names a provider that does not exist."""


def normalise_provider_name(provider_type: str | None = None) -> str:
    """Provider name from the argument or C3_LLM_PROVIDER ('ollama' = 'local'); unknown names raise."""
    # Read the provider name from the argument or from the C3_LLM_PROVIDER environment variable.
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
        _provider_registry[name] = _BUILDERS[name](name)
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
    statuses.extend(get_llm_provider(n).health_check() for n in OPENAI_COMPATIBLE_PRESETS)
    return statuses
