"""Structure checks for the SOLID refactors: provider registry is complete, failure handling lives in one place."""

import time

import pytest

from services.llm import factory
from services.llm.base import BaseLLMProvider
from services.llm.gemini_provider import GeminiProvider
from services.llm.openai_provider import OpenAIProvider


def test_every_supported_provider_has_a_builder():
    # Open/closed: adding a provider is one registry entry, and the two lists can never drift apart.
    assert set(factory.SUPPORTED_PROVIDERS) == set(factory._BUILDERS)


@pytest.mark.parametrize("name", ["gemini", "openai", "local", "groq", "openrouter"])
def test_builders_return_providers_with_the_expected_name(name):
    provider = factory._BUILDERS[name](name)
    assert isinstance(provider, BaseLLMProvider)
    if name in factory.OPENAI_COMPATIBLE_PRESETS:
        assert provider.provider_name == name


def test_failed_response_is_built_by_the_shared_base_method():
    # Liskov/DRY: one implementation of the failure shape, inherited by every provider that needs it.
    assert "_failure" not in vars(GeminiProvider) and "_failure" not in vars(OpenAIProvider)
    response = OpenAIProvider(api_key="x")._failure("m", time.perf_counter(), "boom", finish_reason="error")
    assert response.is_success is False and response.error_message == "boom"
    assert response.model_identifier == "m" and response.finish_reason == "error"
