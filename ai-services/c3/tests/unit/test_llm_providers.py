"""
Unit tests for Provider-Neutral LLM & Vector Architecture
Validates LLMRequest/Response contracts, MockLLMProvider calibration, factory fallback,
Ollama real-execution error handling and model verification, real sentence embeddings,
and runtime diagnostic exposure without credentials leakage.
"""

from unittest.mock import MagicMock, patch

from services.llm.base import LLMRequest, LLMResponse, LLMUsage
from services.llm.factory import get_llm_provider, list_available_providers
from services.llm.local_provider import LocalLLMProvider
from services.llm.mock_provider import MockLLMProvider
from services.llm.openai_provider import OpenAIProvider
from services.rag.vector_store import CurriculumVectorStore, RealSentenceTransformerEmbedding


class TestLLMBaseContracts:
    def test_llm_request_creation(self):
        req = LLMRequest(
            prompt="Test prompt",
            model="mock-gpt4o",
            temperature=0.2,
            max_tokens=256,
            response_format="json"
        )
        assert req.prompt == "Test prompt"
        assert req.model == "mock-gpt4o"
        assert req.response_format == "json"

    def test_llm_response_creation(self):
        usage = LLMUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75, estimated_cost_usd=0.0)
        res = LLMResponse(
            raw_content='{"total_awarded_mark": 8.5}',
            parsed_json={"total_awarded_mark": 8.5},
            model_identifier="mock-gpt4o",
            provider_name="mock",
            usage=usage,
            latency_ms=12.5,
            is_success=True,
            is_real_execution=False
        )
        assert res.is_success is True
        assert res.is_real_execution is False
        assert res.parsed_json["total_awarded_mark"] == 8.5
        assert res.usage.total_tokens == 75


class TestMockLLMProvider:
    def test_mock_provider_health(self):
        provider = MockLLMProvider()
        health = provider.health_check()
        assert health["status"] == "healthy"
        assert health["is_real_execution"] is False
        assert "mock-gpt4o" in health["supported_models"]

    def test_mock_generation_json(self):
        provider = MockLLMProvider()
        req = LLMRequest(
            prompt="Question: Explain testing.\nReference Answer: Testing is verifying software.\nMaximum Marks: 10\nStudent Answer:\nTesting is verifying software.\nProvide JSON with total_awarded_mark.",
            model="mock-gpt4o",
            response_format="json"
        )
        res = provider.generate(req)
        assert res.is_success is True
        assert res.is_real_execution is False
        assert res.parsed_json is not None
        assert "total_awarded_mark" in res.parsed_json
        assert res.latency_ms > 0

    def test_mock_generation_irrelevant_distractor(self):
        provider = MockLLMProvider()
        req = LLMRequest(
            prompt="Question: Explain testing.\nReference Answer: Testing is verifying software.\nMaximum Marks: 10\nStudent Answer:\nThe Roman Empire was a post-Republican period of ancient Rome.\nProvide JSON with total_awarded_mark.",
            model="mock-gpt4o",
            response_format="json"
        )
        res = provider.generate(req)
        assert res.is_success is True
        assert res.is_real_execution is False
        # Distractor should receive 0.0 marks
        assert res.parsed_json["total_awarded_mark"] == 0.0


class TestLocalOllamaProvider:
    def test_ollama_daemon_offline_returns_explicit_failure(self):
        """When local Ollama is offline, provider must return non-silent failure with is_real_execution=False."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:99999", default_model="llama3.2")
        req = LLMRequest(prompt="Test assessment", model="llama3.2")
        res = provider.generate(req)
        assert res.is_success is False
        assert res.is_real_execution is False
        assert "offline or unreachable" in res.error_message

    def test_ollama_missing_model_returns_explicit_failure(self):
        """When Ollama is online but requested model is missing, fail explicitly with pull instruction."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", default_model="llama3.2")
        # Mock daemon online returning empty model list
        with patch.object(provider, "is_available", return_value=True), \
             patch.object(provider, "get_installed_models", return_value=["qwen2.5:7b"]):
            req = LLMRequest(prompt="Test assessment", model="llama3.2")
            res = provider.generate(req)
            assert res.is_success is False
            assert res.is_real_execution is False
            assert "not installed in local Ollama daemon" in res.error_message
            assert "ollama pull llama3.2" in res.error_message

    def test_ollama_successful_inference_sets_real_flag(self):
        """When Ollama generates response, is_real_execution must be True."""
        provider = LocalLLMProvider(base_url="http://127.0.0.1:11434", default_model="llama3.2")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": '{"total_awarded_mark": 9.0}',
            "prompt_eval_count": 80,
            "eval_count": 40
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider, "is_available", return_value=True), \
             patch.object(provider, "is_model_installed", return_value=True), \
             patch("httpx.Client.post", return_value=mock_response):
            req = LLMRequest(prompt="Assess answer", model="llama3.2", response_format="json")
            res = provider.generate(req)
            assert res.is_success is True
            assert res.is_real_execution is True
            assert res.model_identifier == "llama3.2"
            assert res.parsed_json == {"total_awarded_mark": 9.0}
            assert res.usage.total_tokens == 120


class TestVectorStoreAndEmbeddings:
    def test_real_embedding_adapter_offline_handling(self):
        """When sentence_transformers is absent, RealSentenceTransformerEmbedding reports offline status safely."""
        adapter = RealSentenceTransformerEmbedding()
        diag = adapter.diagnostics()
        assert diag["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert diag["expected_dim"] == 384
        if not adapter.is_loaded:
            assert "offline" in diag["status"]

    def test_vector_store_retrieval_and_diagnostics(self):
        """CurriculumVectorStore retrieves relevant chunks and exposes diagnostic metadata."""
        vstore = CurriculumVectorStore()
        diag = vstore.diagnostics()
        assert diag["status"] == "ready"
        assert diag["documents_indexed"] >= 5
        assert "tfidf" in diag["active_backend"] or "sentence-transformers" in diag["active_backend"]

        # Test query retrieval
        hits = vstore.retrieve("high cohesion and loose coupling in software architecture", top_k=2)
        assert len(hits) > 0
        assert "relevance_score" in hits[0]
        assert hits[0]["relevance_score"] > 0
        assert "embedding_backend" in hits[0]


class TestLLMFactoryAndSafety:
    def test_factory_returns_mock_by_default(self):
        provider = get_llm_provider("mock")
        assert isinstance(provider, MockLLMProvider)

    def test_factory_fallback_on_unsupported(self):
        provider = get_llm_provider("non_existent_provider_123")
        assert isinstance(provider, MockLLMProvider)

    def test_openai_provider_reports_missing_key_safely(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        provider = OpenAIProvider()
        health = provider.health_check()
        assert "pending_credentials" in health["status"]
        # Ensure it does NOT crash or expose secrets
        req = LLMRequest(prompt="Test", model="gpt-4o")
        res = provider.generate(req)
        assert res.is_success is False
        assert res.is_real_execution is False
        assert "OPENAI_API_KEY" in res.error_message

    def test_list_available_providers(self):
        providers = list_available_providers()
        assert len(providers) >= 3
        names = [p["provider"] for p in providers]
        assert "calibrated-mock" in names
        assert "openai" in names
        assert "local-ollama" in names
