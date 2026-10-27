"""
AdaptiveLearnSE Component 3 — OpenAI REST API Provider
Real execution against an OpenAI-compatible chat/completions endpoint using httpx. The model
comes from C3_OPENAI_MODEL; credentials from OPENAI_API_KEY. Nothing is simulated.

STATUS: offline/experiment support (second real provider for the multi-LLM comparison). NOT USED BY LIVE MARKING: the
web service's /c3/assess path never imports or calls this module's functionality.
"""

import json
import os
import time
from typing import Any

import httpx

from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMUsage
from .gemini_provider import strip_json_fence
from .http_utils import get_rate_limiter, post_json_with_retry

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider (second real provider used for the multi-LLM comparison)."""

    def __init__(
        self,
        provider_name: str = "openai",
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        key_env: str = "OPENAI_API_KEY",
    ):
        super().__init__(provider_name)
        # key_env names the environment variable holding the key, so OpenAI-compatible hosts (Groq, OpenRouter,
        # DeepSeek ...) can reuse this class with their own key and base URL (see factory.OPENAI_COMPATIBLE_PRESETS).
        self.key_env = key_env
        self.api_key = api_key if api_key is not None else os.getenv(key_env, "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("C3_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

    def is_available(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("change-me") and len(self.api_key) > 10)

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "configured": self.is_available(),
            "base_url": self.base_url,
            "is_real_execution": self.is_available(),
            "status": "ready" if self.is_available() else f"pending_credentials ({self.key_env} not set)",
        }

    def _failure(self, model: str, start: float, message: str, **extra: Any) -> LLMResponse:
        return LLMResponse(
            raw_content=extra.pop("raw_content", ""),
            model_identifier=extra.pop("model_identifier", model),
            provider_name=self.provider_name,
            latency_ms=round((time.perf_counter() - start) * 1000.0, 2),
            is_success=False,
            error_message=message,
            **extra,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        model = self.model if request.model in ("default", "") else request.model
        start = time.perf_counter()
        if not self.is_available():
            return self._failure(model, start, f"{self.key_env} is not configured.")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        try:
            data, retries = post_json_with_retry(
                f"{self.base_url}/chat/completions",
                headers=headers,
                payload=payload,
                timeout=request.timeout_seconds,
                limiter=get_rate_limiter(self.provider_name),  # one limiter per host so free-tier quotas stay separate
            )
            choice = data["choices"][0]
            raw_text = choice["message"]["content"] or ""
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            return self._failure(model, start, f"OpenAI API call failed: {type(exc).__name__}: {exc}")

        usage_data = data.get("usage", {})
        common = {
            "model_identifier": data.get("model", model),
            "usage": LLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            ),
            "finish_reason": choice.get("finish_reason", "stop"),
            "is_real_execution": True,
            "retries": retries,
        }

        parsed = None
        if request.response_format == "json":
            try:
                parsed = json.loads(strip_json_fence(raw_text))
            except json.JSONDecodeError as exc:
                return self._failure(
                    model, start, f"OpenAI response was not valid JSON: {exc}", raw_content=raw_text, **common
                )
            if not isinstance(parsed, dict):
                return self._failure(
                    model, start, "OpenAI JSON response was not an object", raw_content=raw_text, **common
                )

        ok = common["finish_reason"] == "stop"
        return LLMResponse(
            raw_content=raw_text,
            parsed_json=parsed,
            provider_name=self.provider_name,
            latency_ms=round((time.perf_counter() - start) * 1000.0, 2),
            is_success=ok,
            error_message=None if ok else f"finish_reason={common['finish_reason']}",
            **common,
        )
