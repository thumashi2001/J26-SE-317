from fastapi import APIRouter

from app.schemas.assessment import AssessmentRequest, AssessmentResponse
from services.assessment.orchestrator import assess_answer

router = APIRouter(tags=["assessment"])


@router.post("/c3/assess", response_model=AssessmentResponse)
def run_c3_assessment(request: AssessmentRequest) -> AssessmentResponse:
    """Execute the end-to-end C3 assessment pipeline:

    F1 Answer Processing -> F2 Rubric Marking -> F3 Feedback -> F4 Mind Map.
    """
    return assess_answer(request)


@router.post("/assess", response_model=AssessmentResponse, include_in_schema=False)
def run_assessment_alias(request: AssessmentRequest) -> AssessmentResponse:
    """Alias for /c3/assess."""
    return assess_answer(request)
