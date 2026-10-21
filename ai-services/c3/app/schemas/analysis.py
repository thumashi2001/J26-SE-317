from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AnswerType = Literal["short", "structured", "essay"]
ConceptStatus = Literal["demonstrated", "partial", "not_demonstrated"]


class AnswerAnalysisRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question_id: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    student_answer: str
    reference_answer: str | None = None
    expected_concepts: list[str] | None = None
    answer_type: AnswerType

    @field_validator("expected_concepts")
    @classmethod
    def validate_expected_concepts(
        cls, concepts: list[str] | None
    ) -> list[str] | None:
        if concepts is None:
            return None
        if any(not concept.strip() for concept in concepts):
            raise ValueError("expected_concepts cannot contain blank values")
        return [concept.strip() for concept in concepts]


class SentenceAnalysis(BaseModel):
    sentence_id: int = Field(ge=1)
    text: str


class ConceptMatch(BaseModel):
    concept: str
    status: ConceptStatus
    overlap_score: float = Field(ge=0.0, le=1.0)
    evidence_sentence_ids: list[int]


class AnswerAnalysisResponse(BaseModel):
    question_id: str
    normalized_answer: str
    sentence_count: int = Field(ge=0)
    token_count: int = Field(ge=0)
    sentences: list[SentenceAnalysis]
    reference_similarity: float = Field(ge=0.0, le=1.0)
    concept_matches: list[ConceptMatch]
    warnings: list[str]
    analysis_version: str
