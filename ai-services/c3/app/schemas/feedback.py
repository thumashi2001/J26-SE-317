from pydantic import BaseModel, Field

from app.schemas.marking import MarkingRequest


class FeedbackRequest(BaseModel):
    marking_request: MarkingRequest


class CriterionFeedback(BaseModel):
    criterion_id: str
    criterion_description: str
    max_marks: float = Field(gt=0.0)
    selected_level_id: str
    selected_level_descriptor: str
    awarded_mark: float = Field(ge=0.0)
    evidence_sentence_ids: list[int]
    supporting_concepts: list[str]
    demonstrated_concepts: list[str]
    partial_concepts: list[str]
    missing_concepts: list[str]
    next_level_improvements: list[str] = []
    explanation: str
    strengths: list[str]
    missing_or_partial_areas: list[str]
    improvement_suggestions: list[str]
    warnings: list[str]


class OverallFeedback(BaseModel):
    total_mark: float = Field(ge=0.0)
    total_possible: float = Field(gt=0.0)
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    overall_summary: str
    overall_strengths: list[str]
    overall_missing_concepts: list[str]
    overall_next_level_improvements: list[str] = []
    overall_improvement_suggestions: list[str]


class FeedbackResponse(BaseModel):
    question_id: str
    criteria_feedback: list[CriterionFeedback]
    overall_feedback: OverallFeedback
    warnings: list[str]
    feedback_version: str
