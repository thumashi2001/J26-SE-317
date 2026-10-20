"""
AdaptiveLearnSE Component 3 — OpenAI REST API Provider
Connects to OpenAI API using httpx with environment-driven credentials and timeout safety.
"""

import os
import time
import json
from typing import Any
import httpx
from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMUsage


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider."""

    def __init__(self, provider_name: str = "openai", api_key: str | None = None, base_url: str | None = None):
        super().__init__(provider_name)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    def is_available(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("change-me") and len(self.api_key) > 10)

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "configured": self.is_available(),
            "base_url": self.base_url,
            "status": "ready" if self.is_available() else "pending_credentials (OPENAI_API_KEY not set)"
        }

    def generate(self, request: LLMRequest) -> LLMResponse:
        start_time = time.perf_counter()
        if not self.is_available():
            return LLMResponse(
                raw_content="",
                model_identifier=request.model,
                provider_name=self.provider_name,
                is_success=False,
                error_message="OPENAI_API_KEY is not configured. Live cloud execution is pending explicit authorization."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt}
        ]

        payload = {
            "model": request.model if request.model != "default" else "gpt-4o-mini",
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }

        if request.response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=request.timeout_seconds) as client:
                res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

            choice = data["choices"][0]
            raw_text = choice["message"]["content"]
            usage_data = data.get("usage", {})

            parsed_json = None
            if request.response_format == "json":
                try:
                    parsed_json = json.loads(raw_text)
                except Exception:
                    pass

            latency = (time.perf_counter() - start_time) * 1000.0
            usage = LLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
                estimated_cost_usd=round((usage_data.get("prompt_tokens", 0) * 0.15 + usage_data.get("completion_tokens", 0) * 0.60) / 1_000_000, 6)
            )

            return LLMResponse(
                raw_content=raw_text,
                parsed_json=parsed_json,
                model_identifier=data.get("model", request.model),
                provider_name=self.provider_name,
                usage=usage,
                latency_ms=round(latency, 2),
                finish_reason=choice.get("finish_reason", "stop"),
                is_success=True,
                is_real_execution=True
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            return LLMResponse(
                raw_content="",
                model_identifier=request.model,
                provider_name=self.provider_name,
                latency_ms=round(latency, 2),
                is_success=False,
                is_real_execution=False,
                error_message=f"OpenAI API call failed: {str(e)}"
            )
