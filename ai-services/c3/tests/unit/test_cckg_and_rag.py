"""
Unit tests for CCKGGraphAdapter and CurriculumVectorStore.
Validates ontology retrieval, prerequisite traversal, vector search, strict mode and offline fallback.
"""

import numpy as np
import pytest

from services.cckg.graph_adapter import CCKGGraphAdapter, CCKGUnavailableError, get_cckg_adapter
from services.rag.embeddings import EmbeddingError
from services.rag.vector_store import (
    CorpusError,
    CurriculumVectorStore,
    configure_vector_store,
    get_vector_store,
)

DOCS = [
    {
        "doc_id": "D1",
        "title": "Statement coverage",
        "citation": "train:Q1",
        "content": "Statement coverage and branch coverage measure how much code a test suite executes.",
    },
    {
        "doc_id": "D2",
        "title": "REST API design",
        "citation": "train:Q2",
        "content": "RESTful API design uses resources, HTTP verbs and stateless endpoints.",
    },
    {
        "doc_id": "D3",
        "title": "Normalisation",
        "citation": "train:Q3",
        "content": "Database normalisation removes redundancy using normal forms.",
    },
]


class FakeEmbedder:
    """Deterministic stand-in for the remote embedding API, used only to test index logic offline."""

    provider_name = "fake"

    def embed(self, texts, task="document"):
        vocab = ["coverage", "rest", "normal"]
        mat = np.array([[float(w in t.lower()) for w in vocab] + [0.01] for t in texts])
        return mat / np.linalg.norm(mat, axis=1, keepdims=True)

    def diagnostics(self):
        return {"provider": "fake"}


class TestCurriculumVectorStore:
    def test_requires_documents(self):
        with pytest.raises(CorpusError):
            CurriculumVectorStore([], embedding_backend="tfidf")

    def test_rejects_documents_missing_fields(self):
        with pytest.raises(CorpusError):
            CurriculumVectorStore([{"doc_id": "x", "title": "t", "content": "c"}], embedding_backend="tfidf")

    def test_tfidf_backend_is_labelled_lexical(self):
        vstore = CurriculumVectorStore(DOCS, embedding_backend="tfidf")
        assert vstore.active_backend == "tfidf"
        assert vstore.is_real_embedding is False
        assert vstore.doc_vectors.shape[0] == len(DOCS)

    def test_search_relevant_query(self):
        vstore = CurriculumVectorStore(DOCS, embedding_backend="tfidf")
        results = vstore.retrieve("statement coverage branch coverage testing", top_k=2)
        assert results[0]["doc_id"] == "D1"
        assert results[0]["relevance_score"] > 0.0

    def test_search_empty_query(self):
        assert CurriculumVectorStore(DOCS, embedding_backend="tfidf").retrieve("", top_k=3) == []

    def test_format_retrieval_context(self):
        res = CurriculumVectorStore(DOCS, embedding_backend="tfidf").format_retrieval_context("RESTful API design")
        assert res["chunks_retrieved"] > 0
        assert len(res["citations"]) == res["chunks_retrieved"]
        assert res["backend"] == "tfidf"
        assert res["is_real_embedding"] is False

    def test_dense_backend_uses_embedder(self):
        vstore = CurriculumVectorStore(DOCS, embedding_backend="dense", embedding_provider=FakeEmbedder())
        assert vstore.active_backend == "dense"
        assert vstore.is_real_embedding is True
        assert vstore.retrieve("normal forms", top_k=1)[0]["doc_id"] == "D3"

    def test_dense_backend_without_credentials_fails_loudly(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("C3_EMBEDDING_PROVIDER", "gemini")
        with pytest.raises(EmbeddingError):
            CurriculumVectorStore(DOCS, embedding_backend="dense")

    def test_unknown_backend_rejected(self):
        with pytest.raises(CorpusError):
            CurriculumVectorStore(DOCS, embedding_backend="sentence-transformers")

    def test_singleton_requires_configuration(self):
        with pytest.raises(CorpusError):
            get_vector_store()
        store = configure_vector_store(DOCS, embedding_backend="tfidf")
        assert get_vector_store() is store

    def test_diagnostics_report_actual_state(self):
        diag = CurriculumVectorStore(DOCS, embedding_backend="tfidf").diagnostics()
        assert diag["documents_indexed"] == 3
        assert diag["embedding_provider"] is None


@pytest.fixture
def offline_adapter(monkeypatch):
    """In-memory CCKG adapter that never opens a Neo4j connection (no network, no 2s timeout)."""
    monkeypatch.setattr(CCKGGraphAdapter, "_init_connection", lambda self: None)
    return CCKGGraphAdapter(uri="bolt://127.0.0.1:9999")


class TestCCKGGraphAdapter:
    def test_graph_adapter_offline_mode(self):
        # A real connection attempt to a closed port must fall back to the in-memory store
        adapter = CCKGGraphAdapter(uri="bolt://127.0.0.1:9999", strict=False)
        assert adapter.is_live is False
        assert adapter.status()["backend"] == "in_memory_cckg_ontology"

    def test_strict_mode_refuses_silent_fallback(self):
        with pytest.raises(CCKGUnavailableError):
            CCKGGraphAdapter(uri="bolt://127.0.0.1:9999", strict=True)

    def test_status_counts_match_loaded_ontology(self, offline_adapter):
        status = offline_adapter.status()
        assert status["modules_count"] >= 1
        assert status["concepts_count"] >= 1
        assert status["is_live_neo4j"] is False

    def test_get_concept_details(self, offline_adapter):
        c = offline_adapter.get_concept("branch coverage")
        assert c is not None
        assert c["name"] == "branch coverage"
        assert "statement coverage" in c["prerequisites"]

    def test_get_concept_details_nonexistent(self, offline_adapter):
        assert offline_adapter.get_concept("nonexistent_concept_xyz") is None

    def test_get_prerequisite_closure(self, offline_adapter):
        closure = offline_adapter.get_prerequisite_closure(["microservices"])
        concept_names = [c["name"] for c in closure]
        assert "microservices" in concept_names
        assert "loose coupling" in concept_names
        assert "high cohesion" in concept_names

    def test_retrieve_graphrag_context_by_question_id(self, offline_adapter):
        res = offline_adapter.retrieve_graphrag_context(question_id="DIAG-SE3010-001")
        assert res["question_id"] == "DIAG-SE3010-001"
        assert len(res["target_concepts"]) > 0
        assert "graphrag_context_text" in res

    def test_retrieve_graphrag_context_by_concept_list(self, offline_adapter):
        res = offline_adapter.retrieve_graphrag_context(
            question_id="UNKNOWN-Q", concepts=["high cohesion", "loose coupling"]
        )
        assert len(res["target_concepts"]) > 0
        assert "graphrag_context_text" in res

    def test_graph_adapter_singleton(self, monkeypatch):
        monkeypatch.setattr(CCKGGraphAdapter, "_init_connection", lambda self: None)
        assert get_cckg_adapter() is get_cckg_adapter()
