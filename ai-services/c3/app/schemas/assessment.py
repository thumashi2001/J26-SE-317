"""Data shapes for the end-to-end endpoint POST /c3/assess (the one live student submissions use)."""
from pydantic import BaseModel, Field

from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.feedback import FeedbackResponse
from app.schemas.marking import MarkingRequest, MarkingResponse
from app.schemas.mindmap import MindMapResponse


class AssessmentRequest(MarkingRequest):
    """End-to-end assessment request containing student answer, rubric, and context."""
    pass


class AIScoreEstimate(BaseModel):
    """ADVISORY second opinion from a fine-tuned transformer. It never changes `total_awarded_marks`."""

    estimated_ratio: float = Field(ge=0.0, le=1.0)       # estimated mark / maximum mark
    estimated_marks: float = Field(ge=0.0)               # estimated_ratio * total_possible_marks (not a rubric mark)
    rubric_ratio: float = Field(ge=0.0, le=1.0)          # the rubric engine's awarded / possible, for comparison
    difference: float                                    # estimated_ratio - rubric_ratio
    needs_review: bool                                   # True when the two disagree by more than the review threshold
    model: str | None = None
    advisory: bool = True
    note: str = ("Advisory estimate from a model trained on tier-derived labels; the rubric mark is the proposed mark "
                 "and the lecturer's decision is final.")


class AssessmentResponse(BaseModel):
    """End-to-end C3 assessment output combining F1, F2, F3, and F4 outputs."""

    # Headline numbers (the same values appear inside `marking`).
    question_id: str
    total_awarded_marks: float = Field(ge=0.0)
    total_possible_marks: float = Field(gt=0.0)
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    # The four step outputs; Node stores this whole object in MongoDB as c3_results.ai_evaluation.
    marking: MarkingResponse
    analysis: AnswerAnalysisResponse
    feedback: FeedbackResponse
    mindmap: MindMapResponse
    warnings: list[str] = Field(default_factory=list)
    pipeline_version: str = "integrated-v1"
    # Present only when C3_ML_MODEL_DIR is configured and the answer has a reference answer; otherwise None.
    ai_estimate: AIScoreEstimate | None = None
