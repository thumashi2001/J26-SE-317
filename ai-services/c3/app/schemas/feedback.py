"""Data shapes for Function 3: explanations and feedback (built from the marking result, never able to change it)."""
from pydantic import BaseModel, Field

from app.schemas.marking import MarkingRequest


class FeedbackRequest(BaseModel):
    """Feedback is requested with the same payload as marking (the service re-marks to keep feedback consistent)."""

    marking_request: MarkingRequest


class CriterionFeedback(BaseModel):
    """Feedback for one criterion: the mark, the concept status lists, and the text shown to the student."""

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
    # concepts whose only mentions are negated (possible contradiction); also listed under missing_concepts
    # only when C3_CONTRADICTION_POLICY=withhold_credit
    contradicted_concepts: list[str] = []
    next_level_improvements: list[str] = []     # concepts only needed by a HIGHER rubric level
    explanation: str
    strengths: list[str]
    missing_or_partial_areas: list[str]
    improvement_suggestions: list[str]          # the "how to improve" text
    warnings: list[str]


class OverallFeedback(BaseModel):
    """Whole-answer summary built by merging the per-criterion feedback."""

    total_mark: float = Field(ge=0.0)
    total_possible: float = Field(gt=0.0)
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    overall_summary: str
    overall_strengths: list[str]
    overall_missing_concepts: list[str]
    overall_next_level_improvements: list[str] = []
    overall_improvement_suggestions: list[str]


class FeedbackResponse(BaseModel):
    """Function 3 output: per-criterion feedback, the overall feedback block, and any warnings."""
    question_id: str
    criteria_feedback: list[CriterionFeedback]
    overall_feedback: OverallFeedback
    warnings: list[str]
    feedback_version: str
