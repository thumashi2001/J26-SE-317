from fastapi import APIRouter

from app.schemas.mindmap import MindMapRequest, MindMapResponse
from services.mindmap.generator import generate_mindmap

router = APIRouter(prefix="/mindmap", tags=["Mind Map"])

@router.post("/generate", response_model=MindMapResponse)
def generate_mindmap_endpoint(request: MindMapRequest) -> MindMapResponse:
    """Generate a conceptual mind map from an answer analysis request."""
    return generate_mindmap(request)
