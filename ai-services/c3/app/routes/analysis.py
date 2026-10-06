from fastapi import APIRouter

from app.schemas.analysis import AnswerAnalysisRequest, AnswerAnalysisResponse
from services.semantic.analyzer import analyze_answer


router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/answer", response_model=AnswerAnalysisResponse)
def analyze_answer_endpoint(request: AnswerAnalysisRequest) -> AnswerAnalysisResponse:
    """Return deterministic answer-processing and baseline analysis evidence."""
    return analyze_answer(request)
