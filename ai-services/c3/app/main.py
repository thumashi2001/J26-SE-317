from fastapi import FastAPI

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
