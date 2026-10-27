"""The endpoint a LIVE student submission uses: POST /c3/assess.

Node's controller (backend/src/modules/c3/controllers/c3Controller.js, assessAnswer) sends the demo question, rubric and
the student's answer here and gets back marks, evidence, feedback and a mind map in a single response.
"""
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
    # Kept for older callers; hidden from the OpenAPI docs.
    return assess_answer(request)
