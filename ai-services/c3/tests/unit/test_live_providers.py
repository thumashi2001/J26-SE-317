"""
Live provider checks. These call REAL services (cost money / need keys), so they are excluded from
the default run. Execute with:  python -m pytest -m live_llm -q
"""

import pytest

from services.llm.base import LLMRequest
from services.llm.gemini_provider import GeminiProvider
from services.llm.openai_provider import OpenAIProvider
from services.rag.embeddings import GeminiEmbedding, OpenAIEmbedding

pytestmark = pytest.mark.live_llm

PROMPT = 'Reply with JSON only: {"answer": 4} where answer is 2+2.'


def _require(provider):
    if not provider.is_available():
        pytest.skip(f"{provider.provider_name} credentials not configured")


def test_gemini_model_exists_and_generates_json():
    provider = GeminiProvider()
    _require(provider)
    ok, detail = provider.verify_model()
    assert ok, detail
    res = provider.generate(LLMRequest(prompt=PROMPT, temperature=0.0))
    assert res.is_success, res.error_message
    assert res.is_real_execution is True
    assert res.parsed_json["answer"] == 4
    assert res.usage.total_tokens > 0


def test_openai_generates_json():
    provider = OpenAIProvider()
    _require(provider)
    res = provider.generate(LLMRequest(prompt=PROMPT, temperature=0.0))
    assert res.is_success, res.error_message
    assert res.is_real_execution is True
    assert res.parsed_json["answer"] == 4


@pytest.mark.parametrize("cls", [GeminiEmbedding, OpenAIEmbedding])
def test_embeddings_are_real_unit_vectors(cls):
    embedder = cls()
    if not embedder.is_available():
        pytest.skip(f"{embedder.provider_name} credentials not configured")
    vecs = embedder.embed(["software architecture", "database normalisation"])
    assert vecs.shape[0] == 2 and vecs.shape[1] > 100
    assert abs(float((vecs[0] ** 2).sum()) - 1.0) < 1e-6
