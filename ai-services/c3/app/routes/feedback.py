"""HTTP endpoint for Function 3 (explanations and feedback). Used by the lecturer-only raw Node endpoint
`POST /api/v1/c3/feedback`; live student marking goes through /c3/assess instead."""
from fastapi import APIRouter

from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from services.feedback.generator import generate_feedback

# All routes in this file are served under /feedback.
router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/generate", response_model=FeedbackResponse)
def generate_feedback_endpoint(request: FeedbackRequest) -> FeedbackResponse:
    """Generate traceable explanations and feedback from Function 2 output."""
    # generate_feedback re-runs marking and analysis internally so the feedback always matches the mark.
    return generate_feedback(request)
