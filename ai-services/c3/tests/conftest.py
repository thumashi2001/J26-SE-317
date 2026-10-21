"""Shared test setup: deterministic offline defaults and singleton resets."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("C3_VECTOR_BACKEND", "tfidf")
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:1")


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Clear module-level caches so tests do not leak state into each other."""
    yield
    import services.cckg.graph_adapter as cckg
    import services.llm.factory as factory
    import services.rag.vector_store as vstore

    for mod, names in (
        (factory, ("_provider_registry",)),
        (vstore, ("_vector_store_instance",)),
        (cckg, ("_adapter_instance",)),
    ):
        for name in names:
            value = getattr(mod, name, None)
            if isinstance(value, dict):
                value.clear()
            elif value is not None:
                setattr(mod, name, None)


@pytest.fixture(autouse=True)
def _hermetic_offline(monkeypatch, request):
    """Offline tests never read ai-services/c3/.env, never see API keys and can never open a real HTTP connection.

    httpx.MockTransport (used by the stubbed-HTTP tests) is a different class and keeps working. Tests marked
    live_llm are the only ones allowed to talk to real providers.
    """
    if request.node.get_closest_marker("live_llm"):
        yield
        return
    import httpx

    import datasets.generator.roles as roles

    monkeypatch.setattr(roles, "ENV_FILE", Path(__file__).parent / "_no_such_dir" / ".env")
    for name in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    def _blocked(self, request):  # noqa: ARG001
        raise RuntimeError("real network access is blocked in offline tests (use httpx.MockTransport)")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _blocked)
    yield
