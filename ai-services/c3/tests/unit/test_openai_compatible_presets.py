"""Presets reuse OpenAIProvider with another host, key variable and per-host rate-limit key (no network)."""

import pytest

from services.llm import factory
from services.llm.factory import OPENAI_COMPATIBLE_PRESETS, UnknownProviderError, get_llm_provider


@pytest.fixture(autouse=True)
def _fresh_registry(monkeypatch):
    monkeypatch.setattr(factory, "_provider_registry", {})


@pytest.mark.parametrize("name", sorted(OPENAI_COMPATIBLE_PRESETS))
def test_preset_uses_its_own_host_key_and_limiter_key(name, monkeypatch):
    base_url, key_env, _ = OPENAI_COMPATIBLE_PRESETS[name]
    monkeypatch.delenv(key_env, raising=False)
    provider = get_llm_provider(name)
    assert provider.provider_name == name and provider.base_url == base_url
    assert provider.is_available() is False
    assert key_env in provider.health_check()["status"]


def test_preset_key_and_model_come_from_environment(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_" + "x" * 20)
    monkeypatch.setenv("C3_GROQ_MODEL", "some-model")
    provider = get_llm_provider("groq")
    assert provider.is_available() and provider.model == "some-model"


def test_unknown_provider_still_raises():
    with pytest.raises(UnknownProviderError):
        get_llm_provider("not-a-provider")
