"""
AdaptiveLearnSE Component 3 — Real dense embedding providers (Gemini, OpenAI).

Embeddings are produced by genuine remote embedding models; nothing is simulated. Vectors are
validated (finite, consistent dimension) and L2-normalised so a dot product equals cosine
similarity. An optional JSONL cache makes experiment runs reproducible and cheap.
"""

import hashlib
import json
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np

from services.llm.http_utils import get_rate_limiter, post_json_with_retry

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 64


class EmbeddingError(RuntimeError):
    """Raised when a real embedding provider is unconfigured or returns invalid vectors."""


class EmbeddingProvider(ABC):
    provider_name: str
    model: str

    def __init__(self, cache_file: str | Path | None = None):
        self._cache_path = Path(cache_file) if cache_file else None
        self._cache: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        self.dimension = 0
        self.api_calls = 0
        if self._cache_path:
            self._load_cache()

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def _embed_batch(self, texts: list[str], task: str) -> list[list[float]]: ...

    def _key(self, text: str, task: str) -> str:
        return hashlib.sha256(f"{self.provider_name}|{self.model}|{task}|{text}".encode()).hexdigest()

    def _load_cache(self) -> None:
        if not self._cache_path or not self._cache_path.exists():
            return
        with self._cache_path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    self._cache[rec["k"]] = rec["v"]
                except (json.JSONDecodeError, KeyError):
                    continue

    def _append_cache(self, items: dict[str, list[float]]) -> None:
        if not self._cache_path or not items:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self._cache_path.open("a", encoding="utf-8") as fh:
            for key, vec in items.items():
                fh.write(json.dumps({"k": key, "v": vec}) + "\n")

    def embed(self, texts: list[str], task: str = "document") -> np.ndarray:
        """Return an (n, d) matrix of unit-length vectors. task is 'document' or 'query'."""
        if not self.is_available():
            raise EmbeddingError(f"{self.provider_name} embedding provider is not configured (missing API key).")
        keys = [self._key(t, task) for t in texts]
        missing = [i for i, k in enumerate(keys) if k not in self._cache]
        for start in range(0, len(missing), BATCH_SIZE):
            idxs = missing[start : start + BATCH_SIZE]
            vectors = self._embed_batch([texts[i] for i in idxs], task)
            if len(vectors) != len(idxs):
                raise EmbeddingError(f"Expected {len(idxs)} vectors, received {len(vectors)}.")
            fresh: dict[str, list[float]] = {}
            for i, vec in zip(idxs, vectors, strict=True):
                fresh[keys[i]] = vec
            with self._lock:
                self._cache.update(fresh)
            self._append_cache(fresh)
        matrix = np.array([self._cache[k] for k in keys], dtype=float)
        if matrix.ndim != 2 or not np.all(np.isfinite(matrix)):
            raise EmbeddingError("Embedding provider returned non-finite or malformed vectors.")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if np.any(norms == 0):
            raise EmbeddingError("Embedding provider returned a zero vector.")
        self.dimension = matrix.shape[1]
        return matrix / norms

    def diagnostics(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "configured": self.is_available(),
            "is_real_embedding": True,
            "dimension": self.dimension or None,
            "api_calls": self.api_calls,
            "cached_vectors": len(self._cache),
            "status": "ready" if self.is_available() else "pending_credentials",
        }


class GeminiEmbedding(EmbeddingProvider):
    provider_name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None, cache_file: str | Path | None = None):
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("C3_GEMINI_EMBEDDING_MODEL", DEFAULT_GEMINI_EMBEDDING_MODEL)
        self.base_url = os.getenv("GEMINI_BASE_URL", GEMINI_BASE_URL).rstrip("/")
        super().__init__(cache_file)

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _embed_batch(self, texts: list[str], task: str) -> list[list[float]]:
        task_type = "RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT"
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": t}]},
                    "taskType": task_type,
                }
                for t in texts
            ]
        }
        data, _ = post_json_with_retry(
            f"{self.base_url}/models/{self.model}:batchEmbedContents",
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            payload=payload,
            timeout=60.0,
            limiter=get_rate_limiter("gemini-embedding"),
        )
        self.api_calls += 1
        return [e["values"] for e in data["embeddings"]]


class OpenAIEmbedding(EmbeddingProvider):
    provider_name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None, cache_file: str | Path | None = None):
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("C3_OPENAI_EMBEDDING_MODEL", DEFAULT_OPENAI_EMBEDDING_MODEL)
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        super().__init__(cache_file)

    def is_available(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("change-me")

    def _embed_batch(self, texts: list[str], task: str) -> list[list[float]]:
        data, _ = post_json_with_retry(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            payload={"model": self.model, "input": texts},
            timeout=60.0,
            limiter=get_rate_limiter("openai-embedding"),
        )
        self.api_calls += 1
        ordered = sorted(data["data"], key=lambda d: d["index"])
        return [d["embedding"] for d in ordered]


def get_embedding_provider(name: str | None = None, cache_file: str | Path | None = None) -> EmbeddingProvider:
    """Build the configured dense embedding provider (C3_EMBEDDING_PROVIDER, default gemini)."""
    provider = (name or os.getenv("C3_EMBEDDING_PROVIDER", "gemini")).lower().strip()
    if provider == "gemini":
        return GeminiEmbedding(cache_file=cache_file)
    if provider == "openai":
        return OpenAIEmbedding(cache_file=cache_file)
    raise EmbeddingError(f"Unsupported embedding provider '{provider}'. Supported: gemini, openai.")
