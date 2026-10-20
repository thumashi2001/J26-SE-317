"""
Unit tests for the real LLM provider layer: request/response contracts, Gemini and OpenAI providers
(HTTP layer stubbed so tests run offline and free), Ollama provider, retry helper, response cache
and the provider factory. Live calls are covered by the `live_llm` tests in test_live_providers.py.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from services.llm.base import LLMRequest, LLMResponse, LLMUsage
from services.llm.cache import CachedLLMProvider
from services.llm.factory import UnknownProviderError, get_llm_provider, list_available_providers
from services.llm.gemini_provider import GeminiProvider, strip_json_fence
from services.llm.http_utils import post_json_with_retry
from services.llm.local_provider import LocalLLMProvider
from services.llm.openai_provider import OpenAIProvider


def gemini_body(text, finish="STOP", model="gemini-test-001"):
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15},
        "modelVersion": model,
    }


class TestContracts:
    def test_llm_request_defaults(self):
        req = LLMRequest(prompt="hi")
        assert req.model == "default"
        assert req.response_format == "json"

    def test_llm_request_rejects_bad_temperature(self):
        with pytest.raises(ValueError):
            LLMRequest(prompt="x", temperature=5.0)

    def test_llm_response_real_flag_defaults_false(self):
        res = LLMResponse(raw_content="x", model_identifier="m", provider_name="p", usage=LLMUsage())
        assert res.is_real_execution is False
        assert res.cached is False


class TestGeminiProvider:
    def test_unconfigured_provider_fails_explicitly(self):
        res = GeminiProvider(api_key="").generate(LLMRequest(prompt="x"))
        assert res.is_success is False
        assert res.is_real_execution is False
        assert "GEMINI_API_KEY" in res.error_message

    def test_success_parses_json_and_usage(self):
        provider = GeminiProvider(api_key="test-key", model="gemini-test-001")
        body = gemini_body('{"total_awarded_mark": 7.5}')
        with patch("services.llm.gemini_provider.post_json_with_retry", return_value=(body, 0)) as post:
            res = provider.generate(LLMRequest(prompt="grade"))
        assert res.is_success is True
        assert res.is_real_execution is True
        assert res.parsed_json == {"total_awarded_mark": 7.5}
        assert res.usage.total_tokens == 15
        assert res.model_identifier == "gemini-test-001"
        payload = post.call_args.kwargs["payload"]
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["maxOutputTokens"] >= 2048
        assert post.call_args.args[0].endswith("/models/gemini-test-001:generateContent")

    def test_code_fenced_json_is_accepted(self):
        provider = GeminiProvider(api_key="test-key")
        body = gemini_body('```json\n{"a": 1}\n```')
        with patch("services.llm.gemini_provider.post_json_with_retry", return_value=(body, 0)):
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.parsed_json == {"a": 1}

    def test_invalid_json_is_a_failure_not_a_silent_pass(self):
        provider = GeminiProvider(api_key="test-key")
        with patch("services.llm.gemini_provider.post_json_with_retry", return_value=(gemini_body("nope"), 0)):
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.is_success is False
        assert res.parsed_json is None
        assert "not valid JSON" in res.error_message

    def test_empty_candidates_reports_block_reason(self):
        provider = GeminiProvider(api_key="test-key")
        body = {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
        with patch("services.llm.gemini_provider.post_json_with_retry", return_value=(body, 0)):
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.is_success is False
        assert "SAFETY" in res.error_message

    def test_truncated_output_is_not_success(self):
        provider = GeminiProvider(api_key="test-key")
        body = gemini_body('{"a": 1}', finish="MAX_TOKENS")
        with patch("services.llm.gemini_provider.post_json_with_retry", return_value=(body, 0)):
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.is_success is False
        assert "MAX_TOKENS" in res.error_message

    def test_http_error_returns_failure(self):
        provider = GeminiProvider(api_key="test-key")
        with patch("services.llm.gemini_provider.post_json_with_retry", side_effect=httpx.ConnectError("down")):
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.is_success is False
        assert res.is_real_execution is False
        assert "ConnectError" in res.error_message

    def test_verify_model(self):
        provider = GeminiProvider(api_key="test-key", model="gemini-a")
        models = [
            {"name": "models/gemini-a", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embed-b", "supportedGenerationMethods": ["embedContent"]},
        ]
        with patch.object(provider, "list_models", return_value=models):
            assert provider.verify_model() == (True, "ok")
            assert provider.verify_model("embed-b")[0] is False
            assert "not found" in provider.verify_model("nope")[1]

    def test_strip_json_fence(self):
        assert strip_json_fence('```json\n{"x":1}\n```') == '{"x":1}'
        assert strip_json_fence('{"x":1}') == '{"x":1}'


class TestOpenAIProvider:
    def test_unconfigured_provider_fails_explicitly(self):
        res = OpenAIProvider(api_key="").generate(LLMRequest(prompt="x"))
        assert res.is_success is False
        assert "OPENAI_API_KEY" in res.error_message

    def test_success(self):
        provider = OpenAIProvider(api_key="sk-test-1234567890", model="gpt-test")
        body = {
            "choices": [{"message": {"content": '{"m": 3}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            "model": "gpt-test-2026",
        }
        with patch("services.llm.openai_provider.post_json_with_retry", return_value=(body, 1)) as post:
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.is_success and res.is_real_execution
        assert res.parsed_json == {"m": 3}
        assert res.retries == 1
        assert res.usage.total_tokens == 6
        assert post.call_args.kwargs["payload"]["model"] == "gpt-test"

    def test_unparseable_json_is_a_failure(self):
        provider = OpenAIProvider(api_key="sk-test-1234567890")
        body = {"choices": [{"message": {"content": "plain prose"}, "finish_reason": "stop"}]}
        with patch("services.llm.openai_provider.post_json_with_retry", return_value=(body, 0)):
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.is_success is False
        assert "not valid JSON" in res.error_message

    def test_malformed_response_shape_is_failure(self):
        provider = OpenAIProvider(api_key="sk-test-1234567890")
        with patch("services.llm.openai_provider.post_json_with_retry", return_value=({"choices": []}, 0)):
            res = provider.generate(LLMRequest(prompt="x"))
        assert res.is_success is False


class TestRetryHelper:
    def test_retries_on_429_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("services.llm.http_utils.time.sleep", lambda s: None)
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            if calls["n"] < 3:
                return httpx.Response(429, headers={"retry-after": "0"})
            return httpx.Response(200, json={"ok": True})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        body, retries = post_json_with_retry("http://x", headers={}, payload={}, timeout=1, client=client)
        assert body == {"ok": True}
        assert retries == 2

    def test_gives_up_after_max_retries(self, monkeypatch):
        monkeypatch.setattr("services.llm.http_utils.time.sleep", lambda s: None)
        client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
        with pytest.raises(httpx.HTTPStatusError):
            post_json_with_retry("http://x", headers={}, payload={}, timeout=1, max_retries=2, client=client)

    def test_non_retryable_error_raises_immediately(self):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return httpx.Response(400)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(httpx.HTTPStatusError):
            post_json_with_retry("http://x", headers={}, payload={}, timeout=1, client=client)
        assert calls["n"] == 1


class _CountingProvider(GeminiProvider):
    def __init__(self, succeed=True):
        super().__init__(api_key="k", model="m")
        self.calls = 0
        self.succeed = succeed

    def generate(self, request):
        self.calls += 1
        return LLMResponse(
            raw_content="{}",
            parsed_json={},
            model_identifier="m",
            provider_name="gemini",
            is_success=self.succeed,
            is_real_execution=self.succeed,
        )


class TestResponseCache:
    def test_second_identical_request_is_served_from_cache(self, tmp_path):
        inner = _CountingProvider()
        cached = CachedLLMProvider(inner, tmp_path / "c.jsonl")
        first = cached.generate(LLMRequest(prompt="same"))
        second = cached.generate(LLMRequest(prompt="same"))
        assert inner.calls == 1
        assert first.cached is False and second.cached is True
        again = CachedLLMProvider(_CountingProvider(), tmp_path / "c.jsonl")
        assert again.generate(LLMRequest(prompt="same")).cached is True

    def test_different_prompt_misses(self, tmp_path):
        inner = _CountingProvider()
        cached = CachedLLMProvider(inner, tmp_path / "c.jsonl")
        cached.generate(LLMRequest(prompt="a"))
        cached.generate(LLMRequest(prompt="b"))
        assert inner.calls == 2

    def test_failures_are_never_cached(self, tmp_path):
        inner = _CountingProvider(succeed=False)
        cached = CachedLLMProvider(inner, tmp_path / "c.jsonl")
        cached.generate(LLMRequest(prompt="x"))
        cached.generate(LLMRequest(prompt="x"))
        assert inner.calls == 2


class TestLocalOllamaProvider:
    def test_ollama_daemon_offline_returns_explicit_failure(self):
        provider = LocalLLMProvider(base_url="http://127.0.0.1:99999", default_model="llama3.2")
        res = provider.generate(LLMRequest(prompt="Test assessment", model="llama3.2"))
        assert res.is_success is False
        assert res.is_real_execution is False
        assert "offline or unreachable" in res.error_message

    def test_ollama_missing_model_returns_explicit_failure(self):
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", default_model="llama3.2")
        with (
            patch.object(provider, "is_available", return_value=True),
            patch.object(provider, "get_installed_models", return_value=["qwen2.5:7b"]),
        ):
            res = provider.generate(LLMRequest(prompt="Test assessment", model="llama3.2"))
        assert res.is_success is False
        assert res.is_real_execution is False
        assert "not installed in local Ollama daemon" in res.error_message
        assert "ollama pull llama3.2" in res.error_message

    def test_ollama_successful_inference_sets_real_flag(self):
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", default_model="llama3.2")
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "response": '{"total_awarded_mark": 9.0}',
            "prompt_eval_count": 80,
            "eval_count": 40,
        }
        response.raise_for_status = MagicMock()
        with (
            patch.object(provider, "is_available", return_value=True),
            patch.object(provider, "is_model_installed", return_value=True),
            patch("httpx.Client.post", return_value=response),
        ):
            res = provider.generate(LLMRequest(prompt="Assess answer", model="llama3.2", response_format="json"))
        assert res.is_success is True
        assert res.is_real_execution is True
        assert res.parsed_json == {"total_awarded_mark": 9.0}
        assert res.usage.total_tokens == 120


class TestFactory:
    def test_default_provider_is_gemini(self, monkeypatch):
        monkeypatch.delenv("C3_LLM_PROVIDER", raising=False)
        assert isinstance(get_llm_provider(), GeminiProvider)

    def test_env_selects_openai(self, monkeypatch):
        monkeypatch.setenv("C3_LLM_PROVIDER", "openai")
        assert isinstance(get_llm_provider(), OpenAIProvider)

    def test_ollama_alias_selects_local(self):
        assert isinstance(get_llm_provider("ollama"), LocalLLMProvider)

    def test_unknown_provider_raises_instead_of_falling_back(self):
        with pytest.raises(UnknownProviderError):
            get_llm_provider("mock")

    def test_list_available_providers_has_no_mock(self):
        names = [p["provider"] for p in list_available_providers()]
        assert names == ["gemini", "openai", "local-ollama"]
