import os
from fastapi import FastAPI

from app.routes.analysis import router as analysis_router
from app.routes.marking import router as marking_router
from app.routes.feedback import router as feedback_router
from app.routes.mindmap import router as mindmap_router
from app.routes.assessment import router as assessment_router

from services.llm.factory import get_llm_provider, list_available_providers
from services.rag.vector_store import get_vector_store
from services.cckg.graph_adapter import get_cckg_adapter

app = FastAPI(
    title="AdaptiveLearnSE - Component 3 AI Service",
    description="AI-powered Automated Marking and Answer Analysis System",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    provider = get_llm_provider()
    v_store = get_vector_store()
    return {
        "service": "component-3-ai-service",
        "status": "running",
        "version": "0.1.0",
        "provider": provider.provider_name,
        "is_mock": not getattr(provider, "is_available", lambda: False)() if provider.provider_name != "calibrated-mock" else True,
        "vector_backend": v_store.active_backend
    }


@app.get("/api/v1/provider/status")
def provider_status():
    """
    Exposes safe, non-sensitive diagnostic status for PP1 readiness and research audits:
    - Active LLM provider and whether execution is real or mock
    - Vector store embeddings status and dimensionality
    - Curriculum knowledge graph (CCKG) status
    - Safe environment flags (zero exposed secrets or tokens)
    """
    active_llm = get_llm_provider()
    v_store = get_vector_store()
    graph_adapter = get_cckg_adapter()

    return {
        "active_llm_provider": active_llm.health_check(),
        "registered_providers": list_available_providers(),
        "vector_store": v_store.diagnostics(),
        "knowledge_graph": {
            "is_live_neo4j": graph_adapter._is_live_neo4j,
            "backend": "neo4j_live" if graph_adapter._is_live_neo4j else "in_memory_cckg_ontology",
            "modules_count": 4,
            "concepts_count": 7
        },
        "safe_config": {
            "c3_llm_provider": os.getenv("C3_LLM_PROVIDER", "mock"),
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.2"),
            "c3_vector_backend": os.getenv("C3_VECTOR_BACKEND", "auto")
        }
    }


app.include_router(analysis_router)
app.include_router(marking_router)
app.include_router(feedback_router)
app.include_router(mindmap_router)
app.include_router(assessment_router)
