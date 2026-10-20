"""
AdaptiveLearnSE Component 3 — Local LLM Provider (Ollama / Local REST Server)
Connects to locally hosted inference endpoints with zero external network transmission.
Enforces strict model availability checks, transparent real vs mock execution flags,
and explicit error reporting without silent mock fallback.
"""

import os
import time
import json
import logging
from typing import Any
import httpx
from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger("c3.llm.ollama")


class LocalLLMProvider(BaseLLMProvider):
    """
    Local LLM Provider for Ollama or OpenAI-compatible local servers (vLLM/TGI).
    Evaluates real instruction-tuned models (e.g., llama3.2, qwen2.5:7b) locally.
    """

    def __init__(
        self,
        provider_name: str = "local-ollama",
        base_url: str | None = None,
        default_model: str | None = None
    ):
        super().__init__(provider_name)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.default_model = default_model or os.getenv("OLLAMA_MODEL", "llama3.2")

    def is_available(self) -> bool:
        """Check if local Ollama daemon is reachable on configured port."""
        try:
            with httpx.Client(timeout=1.5) as client:
                res = client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    def get_installed_models(self) -> list[str]:
        """Query Ollama daemon for list of locally installed model tags."""
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception as e:
            logger.debug(f"Failed to fetch Ollama model tags: {e}")
        return []

    def is_model_installed(self, model_name: str) -> bool:
        """Verify whether the requested model is available locally in Ollama."""
        models = self.get_installed_models()
        if not models:
            return False
        # Match exact name or without tag suffix (e.g., 'llama3.2' matches 'llama3.2:latest')
        target = model_name.lower().strip()
        for m in models:
            m_lower = m.lower()
            if m_lower == target or m_lower.startswith(f"{target}:"):
                return True
        return False

    def health_check(self) -> dict[str, Any]:
        """Return safe, non-sensitive operational health and installed model status."""
        alive = self.is_available()
        installed = self.get_installed_models() if alive else []
        model_ready = self.is_model_installed(self.default_model) if alive else False

        status_msg = "ready"
        if not alive:
            status_msg = f"offline (Local Ollama daemon unreachable at {self.base_url})"
        elif not model_ready:
            status_msg = f"model_missing (Daemon running, but model '{self.default_model}' not installed)"

        return {
            "provider": self.provider_name,
            "provider_type": "ollama",
            "is_real_execution": True,
            "configured": True,
            "base_url": self.base_url,
            "daemon_running": alive,
            "installed_models": installed,
            "default_model": self.default_model,
            "model_ready": model_ready,
            "status": status_msg
        }

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Execute real local model inference via Ollama /api/generate.
        NEVER silently falls back to mock output. Fails explicitly with logged error.
        """
        start_time = time.perf_counter()
        model_name = request.model if request.model != "default" else self.default_model

        # 1. Daemon Reachability Check
        if not self.is_available():
            latency = (time.perf_counter() - start_time) * 1000.0
            err = (
                f"Local Ollama daemon is offline or unreachable at {self.base_url}. "
                "Ensure Ollama is running ('ollama serve') before requesting real model execution."
            )
            logger.error(err)
            return LLMResponse(
                raw_content="",
                model_identifier=model_name,
                provider_name=self.provider_name,
                latency_ms=round(latency, 2),
                is_success=False,
                is_real_execution=False,
                error_message=err
            )

        # 2. Model Installation Check
        installed_models = self.get_installed_models()
        if not self.is_model_installed(model_name):
            latency = (time.perf_counter() - start_time) * 1000.0
            err = (
                f"Model '{model_name}' is not installed in local Ollama daemon. "
                f"Available models: {installed_models or 'none'}. "
                f"Run 'ollama pull {model_name}' to install before running."
            )
            logger.error(err)
            return LLMResponse(
                raw_content="",
                model_identifier=model_name,
                provider_name=self.provider_name,
                latency_ms=round(latency, 2),
                is_success=False,
                is_real_execution=False,
                error_message=err
            )

        # 3. Payload Construction
        payload: dict[str, Any] = {
            "model": model_name,
            "prompt": f"{request.system_prompt}\n\n{request.prompt}",
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens
            }
        }
        if request.response_format == "json":
            payload["format"] = "json"

        # 4. Genuine Inference Execution
        try:
            with httpx.Client(timeout=request.timeout_seconds) as client:
                res = client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data = res.json()

            raw_text = data.get("response", "")
            parsed_json = None
            if request.response_format == "json":
                try:
                    parsed_json = json.loads(raw_text)
                except Exception as json_err:
                    logger.warning(f"Ollama returned unparseable JSON: {json_err}")

            latency = (time.perf_counter() - start_time) * 1000.0
            usage = LLMUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                estimated_cost_usd=0.0  # Local inference has zero API marginal cost
            )

            return LLMResponse(
                raw_content=raw_text,
                parsed_json=parsed_json,
                model_identifier=model_name,
                provider_name=self.provider_name,
                usage=usage,
                latency_ms=round(latency, 2),
                finish_reason="stop",
                is_success=True,
                is_real_execution=True  # Genuine neural execution verified
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            err_msg = f"Local Ollama inference failed during execution: {str(e)}"
            logger.error(err_msg)
            return LLMResponse(
                raw_content="",
                model_identifier=model_name,
                provider_name=self.provider_name,
                latency_ms=round(latency, 2),
                is_success=False,
                is_real_execution=False,
                error_message=err_msg
            )
