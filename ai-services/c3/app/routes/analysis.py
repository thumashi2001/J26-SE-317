"""HTTP endpoint for Function 1 (answer analysis). Called by Node only through the lecturer-only raw endpoint
`POST /api/v1/c3/analysis`; a student submission does not use it (it uses /c3/assess instead)."""
from fastapi import APIRouter

from app.schemas.analysis import AnswerAnalysisRequest, AnswerAnalysisResponse
from services.semantic.analyzer import analyze_answer

# All routes in this file are served under /analysis.
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/answer", response_model=AnswerAnalysisResponse)
def analyze_answer_endpoint(request: AnswerAnalysisRequest) -> AnswerAnalysisResponse:
    """Return deterministic answer-processing and baseline analysis evidence."""
    # FastAPI has already validated the JSON against AnswerAnalysisRequest (a 422 is returned automatically if not).
    return analyze_answer(request)
