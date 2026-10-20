"""
AdaptiveLearnSE Component 3 — Reproducible response cache for real LLM calls.

Wraps any provider and stores successful responses in an append-only JSONL file keyed by a
sha256 of (provider, model, prompts, generation parameters). A re-run therefore reproduces the
original real responses exactly, saves API cost, and keeps experiment provenance auditable.
Only genuine, successful provider responses are cached; failures are never stored.
"""

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from .base import BaseLLMProvider, LLMRequest, LLMResponse


def request_cache_key(provider: str, model: str, request: LLMRequest) -> str:
    material = {
        "provider": provider,
        "model": model,
        "system_prompt": request.system_prompt,
        "prompt": request.prompt,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "response_format": request.response_format,
        "json_schema": request.json_schema,
    }
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class CachedLLMProvider(BaseLLMProvider):
    """Transparent caching decorator around a real provider."""

    def __init__(self, inner: BaseLLMProvider, cache_file: str | Path):
        super().__init__(inner.provider_name)
        self.inner = inner
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0
        self._load()

    def _load(self) -> None:
        if not self.cache_file.exists():
            return
        with self.cache_file.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # tolerate a torn final line from an interrupted run
                self._entries[entry["key"]] = entry

    def is_available(self) -> bool:
        return self.inner.is_available()

    def health_check(self) -> dict[str, Any]:
        info = dict(self.inner.health_check())
        info.update({"cache_file": str(self.cache_file), "cache_entries": len(self._entries)})
        return info

    def _model_of(self, request: LLMRequest) -> str:
        if request.model in ("default", ""):
            return str(getattr(self.inner, "model", "default"))
        return request.model

    def generate(self, request: LLMRequest) -> LLMResponse:
        key = request_cache_key(self.inner.provider_name, self._model_of(request), request)
        with self._lock:
            entry = self._entries.get(key)
        if entry is not None:
            self.hits += 1
            response = LLMResponse(**entry["response"])
            response.cached = True
            return response

        self.misses += 1
        response = self.inner.generate(request)
        if response.is_success and response.is_real_execution:
            record = {"key": key, "response": response.model_dump(exclude={"cached"})}
            with self._lock:
                self._entries[key] = record
                with self.cache_file.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return response
