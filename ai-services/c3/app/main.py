"""Entry point of the C3 Python AI service (FastAPI).

WHAT IT IS
    A small HTTP service on port 8003 (started with `uvicorn app.main:app --port 8003`). The Node.js backend calls it;
    the browser never talks to it directly. It has no login of its own because it is an internal service.

WHAT IT EXPOSES
    GET  /health                 liveness + configuration status (makes no network calls)
    GET  /api/v1/provider/status safe diagnostics (never prints secrets)
    POST /analysis/answer        F1: answer processing and lexical concept analysis
    POST /marking/evaluate       F2: rubric-controlled proposed mark
    POST /feedback/generate      F3: explanations and feedback
    POST /mindmap/generate       F4: concept mind map
    POST /c3/assess              all four steps in one call  <-- the ONLY endpoint a live student submission uses

HOW A LIVE MARK IS PRODUCED
    /c3/assess -> services/assessment/orchestrator.py. That pipeline is rule based (token overlap + rubric levels).
    The LLM provider, vector store and Neo4j graph imported below are only reported in /health and used by offline
    experiments; they are NOT called while marking a student answer.
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()  # read ai-services/c3/.env before any provider reads the environment

from app.routes.analysis import router as analysis_router
from app.routes.assessment import router as assessment_router
from app.routes.feedback import router as feedback_router
from app.routes.marking import router as marking_router
from app.routes.mindmap import router as mindmap_router
from services.cckg.graph_adapter import get_cckg_adapter
from services.llm.factory import UnknownProviderError, get_llm_provider, list_available_providers
from services.rag.vector_store import vector_store_config_status

# The FastAPI application object that uvicorn serves.
app = FastAPI(
    title="AdaptiveLearnSE - Component 3 AI Service",
    description="AI-powered Automated Marking and Answer Analysis System",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Liveness plus configuration status. Makes no network calls to LLM or graph backends."""
    # The "llm" block only reports which provider is *configured*; marking does not call it.
    try:
        provider = get_llm_provider()
        info = provider.health_check()
        llm = {
            "provider": provider.provider_name,
            "model": info.get("model"),
            "configured": bool(info.get("configured", provider.is_available())),
            "is_real_execution": bool(info.get("is_real_execution", False)),
        }
    except UnknownProviderError as exc:
        llm = {"provider": None, "configured": False, "is_real_execution": False, "error": str(exc)}
    return {
        "service": "component-3-ai-service",
        "status": "running",
        "version": "0.1.0",
        "llm": llm,
        "vector_store": vector_store_config_status(),
    }


@app.get("/api/v1/provider/status")
def provider_status():
    """Safe, non-sensitive diagnostics for readiness checks and research audits (no secrets)."""
    try:
        active_llm = get_llm_provider().health_check()
    except UnknownProviderError as exc:
        active_llm = {"configured": False, "error": str(exc)}
    # The graph adapter is only asked for its status here (live Neo4j or in-memory fallback); no marking uses it.
    graph_adapter = get_cckg_adapter()
    return {
        "active_llm_provider": active_llm,
        "registered_providers": list_available_providers(),
        "vector_store": vector_store_config_status(),
        "knowledge_graph": graph_adapter.status(),
        "safe_config": {
            "c3_llm_provider": os.getenv("C3_LLM_PROVIDER", "gemini"),
            "c3_embedding_provider": os.getenv("C3_EMBEDDING_PROVIDER", "gemini"),
            "c3_vector_backend": os.getenv("C3_VECTOR_BACKEND", "dense"),
        },
    }


# Register the endpoint groups (each router lives in app/routes/*.py).
app.include_router(analysis_router)
app.include_router(marking_router)
app.include_router(feedback_router)
app.include_router(mindmap_router)
app.include_router(assessment_router)
