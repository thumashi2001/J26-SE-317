"""HTTP endpoint for Function 4 (concept mind map). Used by the lecturer-only raw Node endpoint
`POST /api/v1/c3/mindmap`; live student marking gets its mind map from /c3/assess instead."""
from fastapi import APIRouter

from app.schemas.mindmap import MindMapRequest, MindMapResponse
from services.mindmap.generator import generate_mindmap

# All routes in this file are served under /mindmap.
router = APIRouter(prefix="/mindmap", tags=["Mind Map"])

@router.post("/generate", response_model=MindMapResponse)
def generate_mindmap_endpoint(request: MindMapRequest) -> MindMapResponse:
    """Generate a conceptual mind map from an answer analysis request."""
    return generate_mindmap(request)
