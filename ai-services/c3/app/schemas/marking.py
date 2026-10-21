from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.analysis import AnswerAnalysisRequest


EvidenceRuleType = Literal["required_concept_count"]


class EvidenceRule(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: EvidenceRuleType
    minimum_demonstrated: int = Field(default=0, ge=0)
    minimum_partial: int = Field(default=0, ge=0)
    allow_partial: bool = False

    @model_validator(mode="after")
    def validate_thresholds(self) -> "EvidenceRule":
        if self.minimum_demonstrated == 0 and self.minimum_partial == 0:
            raise ValueError("evidence_rule must require at least one concept")
        if self.minimum_partial > 0 and not self.allow_partial:
            raise ValueError(
                "allow_partial must be true when minimum_partial is greater than zero"
            )
        if self.allow_partial and self.minimum_partial == 0:
            raise ValueError(
                "minimum_partial must be greater than zero when allow_partial is true"
            )
        return self


class ScoringLevel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    level_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    mark: float = Field(ge=0.0)
    descriptor: str = Field(min_length=1)
    required_concepts: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    evidence_rule: EvidenceRule | None = None

    @field_validator("required_concepts", "evidence_requirements")
    @classmethod
    def validate_non_blank_requirements(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("requirements cannot contain blank values")
        return [value.strip() for value in values]


class RubricCriterion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    criterion_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    max_marks: float = Field(gt=0.0)
    required_concepts: list[str] = Field(default_factory=list)
    scoring_levels: list[ScoringLevel] = Field(min_length=1)

    @field_validator("required_concepts")
    @classmethod
    def validate_non_blank_concepts(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("required_concepts cannot contain blank values")
        return [value.strip() for value in values]


class Rubric(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    rubric_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    criteria: list[RubricCriterion] = Field(min_length=1)


class MarkingRequest(AnswerAnalysisRequest):
    rubric: Rubric


class CriterionMarkingResult(BaseModel):
    criterion_id: str
    criterion_description: str
    selected_level_id: str
    selected_level_label: str
    rubric_descriptor: str
    awarded_mark: float = Field(ge=0.0)
    max_marks: float = Field(gt=0.0)
    evidence_sentence_ids: list[int]
    supporting_concepts: list[str]
    explanation: str
    warnings: list[str]


class MarkingResponse(BaseModel):
    question_id: str
    criteria_results: list[CriterionMarkingResult]
    total_awarded_marks: float = Field(ge=0.0)
    total_possible_marks: float = Field(gt=0.0)
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    overall_explanation: str
    warnings: list[str]
    marking_version: str
