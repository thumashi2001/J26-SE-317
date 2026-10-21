"""
AdaptiveLearnSE Component 3 — Google Gemini REST Provider
Real execution against the Gemini generateContent API using httpx. Credentials and the model
come from the environment (GEMINI_API_KEY, C3_GEMINI_MODEL); nothing is simulated.
"""

import json
import os
import time
from typing import Any

import httpx

from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMUsage
from .http_utils import get_json, get_rate_limiter, post_json_with_retry

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"  # gemini-2.5-* returns 404 "no longer available to new users"
# Thinking models spend part of maxOutputTokens on reasoning; never starve the visible answer.
MIN_OUTPUT_TOKENS = 2048
OK_FINISH = ("STOP", "FINISH_REASON_UNSPECIFIED")


def strip_json_fence(text: str) -> str:
    """Remove a markdown code fence some models wrap around JSON output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    return cleaned.strip()


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider (default provider for AdaptiveLearnSE C3)."""

    def __init__(
        self,
        provider_name: str = "gemini",
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        super().__init__(provider_name)
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("C3_GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.base_url = (base_url or os.getenv("GEMINI_BASE_URL", GEMINI_BASE_URL)).rstrip("/")
        self.http_client: httpx.Client | None = None  # optional injected client (tests / preflight)

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

    def is_available(self) -> bool:
        return bool(self.api_key) and not self.api_key.lower().startswith("change-me")

    def list_models(self) -> list[dict[str, Any]]:
        data = get_json(f"{self.base_url}/models?pageSize=1000", headers=self._headers(), client=self.http_client)
        return data.get("models", [])

    def verify_model(self, model: str | None = None) -> tuple[bool, str]:
        """Check the configured model exists and supports generateContent (ListModels)."""
        wanted = f"models/{model or self.model}"
        try:
            for entry in self.list_models():
                if entry.get("name") == wanted:
                    if "generateContent" in entry.get("supportedGenerationMethods", []):
                        return True, "ok"
                    return False, f"{wanted} does not support generateContent"
            return False, f"{wanted} not found in ListModels"
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            hint = {
                400: " (Gemini reports an invalid API key as 400)",
                401: " (authentication error)",
                403: " (authentication/permission error)",
                429: " (rate limited / quota)",
            }.get(code, "")
            return False, f"ListModels failed: HTTP {code}{hint}"
        except Exception as exc:
            return False, f"ListModels failed: {type(exc).__name__}: {exc}"

    def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "configured": self.is_available(),
            "base_url": self.base_url,
            "is_real_execution": self.is_available(),
            "status": "ready" if self.is_available() else "pending_credentials (GEMINI_API_KEY not set)",
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
            return self._failure(model, start, "GEMINI_API_KEY is not configured.")

        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": max(request.max_tokens, MIN_OUTPUT_TOKENS),
        }
        if request.response_format == "json":
            generation_config["responseMimeType"] = "application/json"
        budget = os.getenv("C3_GEMINI_THINKING_BUDGET")
        level = os.getenv("C3_GEMINI_THINKING_LEVEL", "low").strip()
        if budget:
            generation_config["thinkingConfig"] = {"thinkingBudget": int(budget)}
        elif model.startswith("gemini-3") and level:
            # Gemini 3 models otherwise spend the whole output budget on hidden reasoning and return
            # truncated JSON (finishReason=MAX_TOKENS) - verified live on the 3.x Flash models.
            generation_config["thinkingConfig"] = {"thinkingLevel": level}

        payload = {
            "systemInstruction": {"parts": [{"text": request.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": generation_config,
        }
        url = f"{self.base_url}/models/{model}:generateContent"

        try:
            data, retries = post_json_with_retry(
                url,
                headers=self._headers(),
                payload=payload,
                timeout=request.timeout_seconds,
                limiter=get_rate_limiter(f"gemini:{model}"),
            )
        except (httpx.HTTPError, ValueError) as exc:
            return self._failure(model, start, f"Gemini API call failed: {type(exc).__name__}: {exc}")

        candidate = (data.get("candidates") or [{}])[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        raw_text = "".join(p.get("text", "") for p in parts)
        finish = candidate.get("finishReason", "STOP")
        meta = data.get("usageMetadata", {})
        usage = LLMUsage(
            prompt_tokens=meta.get("promptTokenCount", 0),
            completion_tokens=meta.get("candidatesTokenCount", 0),
            total_tokens=meta.get("totalTokenCount", 0),
        )
        common = {
            "model_identifier": data.get("modelVersion", model),
            "usage": usage,
            "finish_reason": finish,
            "is_real_execution": True,
            "retries": retries,
        }

        if not raw_text:
            reason = data.get("promptFeedback", {}).get("blockReason") or finish
            return self._failure(model, start, f"Gemini returned no text (reason: {reason})", **common)

        if finish == "MAX_TOKENS":
            return self._failure(
                model, start,
                f"Gemini output truncated (finishReason=MAX_TOKENS, thoughts={meta.get('thoughtsTokenCount')}); "
                "lower C3_GEMINI_THINKING_LEVEL or raise max_tokens",
                raw_content=raw_text, **common,
            )

        parsed = None
        if request.response_format == "json":
            try:
                parsed = json.loads(strip_json_fence(raw_text))
            except json.JSONDecodeError as exc:
                return self._failure(
                    model, start, f"Gemini response was not valid JSON: {exc}", raw_content=raw_text, **common
                )
            if not isinstance(parsed, dict):
                return self._failure(
                    model, start, "Gemini JSON response was not an object", raw_content=raw_text, **common
                )

        ok = finish in OK_FINISH
        return LLMResponse(
            raw_content=raw_text,
            parsed_json=parsed,
            provider_name=self.provider_name,
            latency_ms=round((time.perf_counter() - start) * 1000.0, 2),
            is_success=ok,
            error_message=None if ok else f"finishReason={finish}",
            **common,
        )
