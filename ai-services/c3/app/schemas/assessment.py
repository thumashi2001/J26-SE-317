from pydantic import BaseModel, Field

from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.feedback import FeedbackResponse
from app.schemas.marking import MarkingRequest, MarkingResponse
from app.schemas.mindmap import MindMapResponse


class AssessmentRequest(MarkingRequest):
    """End-to-end assessment request containing student answer, rubric, and context."""
    pass


class AssessmentResponse(BaseModel):
    """End-to-end C3 assessment output combining F1, F2, F3, and F4 outputs."""

    question_id: str
    total_awarded_marks: float = Field(ge=0.0)
    total_possible_marks: float = Field(gt=0.0)
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    marking: MarkingResponse
    analysis: AnswerAnalysisResponse
    feedback: FeedbackResponse
    mindmap: MindMapResponse
    warnings: list[str] = Field(default_factory=list)
    pipeline_version: str = "integrated-v1"
