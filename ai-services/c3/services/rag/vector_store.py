"""
AdaptiveLearnSE Component 3 — Curriculum Vector Store & Retrieval Pipeline

Cosine-similarity retrieval over an explicitly supplied document corpus. There is no built-in
corpus: callers must provide documents (for the experiments these are derived from the training
split only, so retrieval can never leak held-out data).

Two backends, each reported honestly through `active_backend`:
  * "dense"  - genuine remote embeddings (C3_EMBEDDING_PROVIDER: gemini | openai).
  * "tfidf"  - a lexical TF-IDF baseline. It is NOT a dense embedding model.
If "dense" is requested but unavailable, construction fails; there is no silent fallback.

STATUS: offline library and experiments. vector_store_config_status() is only what /health reports (configuration, no
index is built at start-up). NOT USED BY LIVE MARKING: the web service's /c3/assess path never imports or calls this
module's functionality.
"""

import logging
import os
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .embeddings import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger("c3.rag.vector_store")

REQUIRED_DOC_FIELDS = ("doc_id", "title", "content", "citation")


class CorpusError(ValueError):
    """Raised when the retrieval corpus is missing or malformed."""


class CurriculumVectorStore:
    """Cosine-similarity retrieval over supplied curriculum documents."""

    def __init__(
        self,
        documents: list[dict[str, Any]],
        embedding_backend: str | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        if not documents:
            raise CorpusError("CurriculumVectorStore requires a non-empty document corpus.")
        for doc in documents:
            missing = [f for f in REQUIRED_DOC_FIELDS if not str(doc.get(f, "")).strip()]
            if missing:
                raise CorpusError(f"Document {doc.get('doc_id', '?')} is missing fields: {missing}")

        self.docs = list(documents)
        corpus_texts = [f"{d['title']} {d['content']}" for d in self.docs]

        requested = (embedding_backend or os.getenv("C3_VECTOR_BACKEND", "dense")).lower().strip()
        if requested not in ("dense", "tfidf"):
            raise CorpusError(f"Unsupported vector backend '{requested}'. Use 'dense' or 'tfidf'.")
        self.requested_backend = requested
        self.is_real_embedding = requested == "dense"
        self.active_backend = requested
        self.embedder: EmbeddingProvider | None = None
        self.vectorizer: TfidfVectorizer | None = None

        if requested == "dense":
            self.embedder = embedding_provider or get_embedding_provider()
            self.doc_vectors = self.embedder.embed(corpus_texts, task="document")
        else:
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            self.doc_vectors = self.vectorizer.fit_transform(corpus_texts)
        self.vector_dim = int(self.doc_vectors.shape[1])

    def retrieve(self, query: str, top_k: int = 2, threshold: float = 0.05) -> list[dict[str, Any]]:
        """Return the top_k documents whose similarity to the query is at least threshold."""
        if not query.strip():
            return []
        if self.embedder is not None:
            query_vec = self.embedder.embed([query], task="query")
            similarities = np.dot(query_vec, self.doc_vectors.T)[0]
        else:
            query_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self.doc_vectors)[0]

        results: list[dict[str, Any]] = []
        for idx in np.argsort(similarities)[::-1]:
            score = float(similarities[idx])
            if score >= threshold and len(results) < top_k:
                doc = dict(self.docs[idx])
                doc["relevance_score"] = round(score, 4)
                doc["embedding_backend"] = self.active_backend
                doc["is_real_embedding"] = self.is_real_embedding
                results.append(doc)
        return results

    def format_retrieval_context(self, query: str, top_k: int = 2) -> dict[str, Any]:
        """Format retrieved passages into a grounded context string and citation list."""
        hits = self.retrieve(query, top_k=top_k)
        if not hits:
            return {
                "context_text": "No supporting passage retrieved above the relevance threshold.",
                "citations": [],
                "chunks_retrieved": 0,
                "backend": self.active_backend,
                "is_real_embedding": self.is_real_embedding,
            }
        context_parts = [
            f"[Source {i}: {hit['title']} ({hit['citation']})]\n{hit['content']}" for i, hit in enumerate(hits, 1)
        ]
        return {
            "context_text": "\n\n".join(context_parts),
            "citations": [hit["citation"] for hit in hits],
            "chunks_retrieved": len(hits),
            "backend": self.active_backend,
            "is_real_embedding": self.is_real_embedding,
        }

    def diagnostics(self) -> dict[str, Any]:
        """Runtime state of the index (no network calls)."""
        return {
            "active_backend": self.active_backend,
            "requested_backend": self.requested_backend,
            "is_real_embedding": self.is_real_embedding,
            "vector_dimension": self.vector_dim,
            "documents_indexed": len(self.docs),
            "embedding_provider": self.embedder.diagnostics() if self.embedder else None,
            "status": "ready",
        }


def vector_store_config_status() -> dict[str, Any]:
    """Configuration-only status (no index built, no network): safe for /health."""
    backend = os.getenv("C3_VECTOR_BACKEND", "dense").lower().strip()
    info: dict[str, Any] = {"requested_backend": backend, "index_built": _vector_store_instance is not None}
    if backend == "dense":
        try:
            info["embedding_provider"] = get_embedding_provider().diagnostics()
        except Exception as exc:
            info["embedding_provider"] = {"status": f"unavailable: {exc}"}
    return info


_vector_store_instance: CurriculumVectorStore | None = None


def configure_vector_store(documents: list[dict[str, Any]], **kwargs: Any) -> CurriculumVectorStore:
    """Build and register the process-wide store from an explicit corpus."""
    global _vector_store_instance
    _vector_store_instance = CurriculumVectorStore(documents, **kwargs)
    return _vector_store_instance


def get_vector_store() -> CurriculumVectorStore:
    """Return the configured store; fails loudly if no corpus was supplied."""
    if _vector_store_instance is None:
        raise CorpusError("Vector store is not configured; call configure_vector_store(documents) first.")
    return _vector_store_instance
