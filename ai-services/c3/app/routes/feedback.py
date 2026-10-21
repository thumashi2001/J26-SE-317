from fastapi import APIRouter

from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from services.feedback.generator import generate_feedback


router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/generate", response_model=FeedbackResponse)
def generate_feedback_endpoint(request: FeedbackRequest) -> FeedbackResponse:
    """Generate traceable explanations and feedback from Function 2 output."""
    return generate_feedback(request)
