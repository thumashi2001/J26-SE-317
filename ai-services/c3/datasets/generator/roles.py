"""Generator / blind-verifier role configuration: which provider+model plays each role and which env vars it needs.

Only variable NAMES are ever reported here; values (API keys) are never read into messages or logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from services.llm.base import BaseLLMProvider
from services.llm.gemini_provider import GeminiProvider
from services.llm.openai_provider import DEFAULT_OPENAI_MODEL, OpenAIProvider
from services.llm.preflight import KEY_ENV, ModelRequirement

from . import C3_ROOT

ENV_FILE: Path = C3_ROOT / ".env"  # tests point this at a temp file
DEFAULT_GENERATOR_MODEL = "gemini-2.5-pro"
DEFAULT_VERIFIER_PROVIDER = "openai"
DEFAULT_VERIFIER_MODELS = {"openai": DEFAULT_OPENAI_MODEL, "gemini": "gemini-2.5-flash"}
VERIFIER_PROVIDERS = ("gemini", "openai")


class RoleConfigError(ValueError):
    pass


def load_env() -> None:
    """Load ai-services/c3/.env at CLI entry. Real environment variables win (dotenv override=False)."""
    load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Role:
    name: str  # generator | verifier
    provider: str
    model: str
    model_env: str  # env var that selects the model
    key_env: str  # env var holding the API key (NAME only)

    @property
    def requirement(self) -> ModelRequirement:
        return ModelRequirement(self.name, self.provider, self.model)

    def build(self) -> BaseLLMProvider:
        return OpenAIProvider(model=self.model) if self.provider == "openai" else GeminiProvider(model=self.model)


def model_family(provider: str, model: str) -> str:
    m = model.lower()
    if m.startswith(("gemini", "gemma", "models/gemini")):
        return "gemini"
    if m.startswith(("gpt", "o1", "o3", "o4", "chatgpt", "text-embedding")):
        return "openai"
    return provider


def resolve_roles() -> tuple[Role, Role]:
    gen_model = os.getenv("C3_GENERATOR_MODEL", "").strip() or DEFAULT_GENERATOR_MODEL
    generator = Role("generator", "gemini", gen_model, "C3_GENERATOR_MODEL", KEY_ENV["gemini"])
    vprov = (os.getenv("C3_VERIFIER_PROVIDER", "").strip() or DEFAULT_VERIFIER_PROVIDER).lower()
    if vprov not in VERIFIER_PROVIDERS:
        raise RoleConfigError(f"C3_VERIFIER_PROVIDER must be one of {', '.join(VERIFIER_PROVIDERS)} (got '{vprov}')")
    vmodel = os.getenv("C3_VERIFIER_MODEL", "").strip() or DEFAULT_VERIFIER_MODELS[vprov]
    verifier = Role("verifier", vprov, vmodel, "C3_VERIFIER_MODEL", KEY_ENV[vprov])
    return generator, verifier


def missing_key_vars(roles: tuple[Role, ...] | list[Role]) -> list[str]:
    """Names (never values) of the API-key variables the given roles need but cannot use."""
    missing: list[str] = []
    for role in roles:
        if not role.build().is_available() and role.key_env not in missing:
            missing.append(role.key_env)
    return missing


def same_family(generator: Role, verifier: Role) -> bool:
    return model_family(generator.provider, generator.model) == model_family(verifier.provider, verifier.model)


def role_meta(generator: Role, verifier: Role) -> dict:
    return {
        "generator_provider": generator.provider,
        "generator_model": generator.model,
        "verifier_provider": verifier.provider,
        "verifier_model": verifier.model,
        "verifier_same_model_family_as_generator": same_family(generator, verifier),
    }


def verifier_cache_name(verifier: Role) -> str:
    return f"verifier_{verifier.provider}.jsonl"
