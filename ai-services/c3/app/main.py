from fastapi import FastAPI

from app.routes.analysis import router as analysis_router
from app.routes.feedback import router as feedback_router
from app.routes.marking import router as marking_router
from app.routes.mindmap import router as mindmap_router

app = FastAPI(
    title="AdaptiveLearnSE - Component 3 AI Service",
    description="AI-powered Automated Marking and Answer Analysis System",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "service": "component-3-ai-service",
        "status": "running",
        "version": "0.1.0",
    }


app.include_router(analysis_router)
app.include_router(marking_router)
app.include_router(feedback_router)
app.include_router(mindmap_router)
