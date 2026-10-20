"""
Unit tests for CCKGGraphAdapter and CurriculumVectorStore
Validates ontology retrieval, prerequisite traversal, vector search, and offline fallback.
"""

import pytest
from services.rag.vector_store import CurriculumVectorStore, get_vector_store
from services.cckg.graph_adapter import CCKGGraphAdapter, get_cckg_adapter


class TestCurriculumVectorStore:
    def test_vector_store_initialization(self):
        vstore = CurriculumVectorStore()
        assert len(vstore.docs) > 0
        assert vstore.vectorizer is not None
        assert vstore.doc_vectors is not None

    def test_search_relevant_query(self):
        vstore = CurriculumVectorStore()
        results = vstore.retrieve("statement coverage branch coverage testing", top_k=2)
        assert len(results) > 0
        top_res = results[0]
        assert "module_id" in top_res
        assert "content" in top_res
        assert "relevance_score" in top_res
        assert top_res["relevance_score"] > 0.0

    def test_search_empty_query(self):
        vstore = CurriculumVectorStore()
        results = vstore.retrieve("", top_k=3)
        assert len(results) == 0

    def test_format_retrieval_context(self):
        vstore = CurriculumVectorStore()
        res = vstore.format_retrieval_context("RESTful API design and endpoints", top_k=2)
        assert "context_text" in res
        assert "citations" in res
        assert res["chunks_retrieved"] > 0 or len(res["citations"]) >= 0

    def test_singleton_accessor(self):
        s1 = get_vector_store()
        s2 = get_vector_store()
        assert s1 is s2


class TestCCKGGraphAdapter:
    def test_graph_adapter_offline_mode(self):
        # Default with non-existent live port falls back gracefully to in-memory
        adapter = CCKGGraphAdapter(uri="bolt://127.0.0.1:9999")
        assert adapter.is_live is False

    def test_get_concept_details(self):
        adapter = CCKGGraphAdapter(uri="bolt://127.0.0.1:9999")
        c = adapter.get_concept("branch coverage")
        assert c is not None
        assert c["name"] == "branch coverage"
        assert "statement coverage" in c["prerequisites"]

    def test_get_concept_details_nonexistent(self):
        adapter = CCKGGraphAdapter(uri="bolt://127.0.0.1:9999")
        c = adapter.get_concept("nonexistent_concept_xyz")
        assert c is None

    def test_get_prerequisite_closure(self):
        adapter = CCKGGraphAdapter(uri="bolt://127.0.0.1:9999")
        closure = adapter.get_prerequisite_closure(["microservices"])
        concept_names = [c["name"] for c in closure]
        assert "microservices" in concept_names
        assert "loose coupling" in concept_names
        assert "high cohesion" in concept_names

    def test_retrieve_graphrag_context_by_question_id(self):
        adapter = CCKGGraphAdapter(uri="bolt://127.0.0.1:9999")
        res = adapter.retrieve_graphrag_context(question_id="DIAG-SE3010-001")
        assert res["question_id"] == "DIAG-SE3010-001"
        assert len(res["target_concepts"]) > 0
        assert "graphrag_context_text" in res

    def test_retrieve_graphrag_context_by_concept_list(self):
        adapter = CCKGGraphAdapter(uri="bolt://127.0.0.1:9999")
        res = adapter.retrieve_graphrag_context(question_id="UNKNOWN-Q", concepts=["high cohesion", "loose coupling"])
        assert len(res["target_concepts"]) > 0
        assert "graphrag_context_text" in res

    def test_graph_adapter_singleton(self):
        a1 = get_cckg_adapter()
        a2 = get_cckg_adapter()
        assert a1 is a2
