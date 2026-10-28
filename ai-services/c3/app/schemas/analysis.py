"""Data shapes (Pydantic models) for Function 1: answer analysis.

WHY THIS FILE MATTERS FOR "PARAMETER VALIDATION"
    FastAPI checks every incoming JSON body against these models BEFORE any marking code runs. A wrong type, a missing
    field, an empty question or a blank concept is rejected automatically with HTTP 422. This is *input validation*
    (is the request well formed?). It is not model hyper-parameter tuning.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Allowed answer types and the three possible concept states used all through C3.
AnswerType = Literal["short", "structured", "essay"]
ConceptStatus = Literal["demonstrated", "partial", "not_demonstrated"]


class AnswerAnalysisRequest(BaseModel):
    """What the analysis step needs: the question, the student's answer and (optionally) the expected concepts."""

    model_config = ConfigDict(str_strip_whitespace=True)  # leading/trailing spaces are removed from every string

    question_id: str = Field(min_length=1)       # must not be empty
    question_text: str = Field(min_length=1)     # must not be empty
    student_answer: str                           # may be empty (an empty answer is analysed and scores nothing)
    reference_answer: str | None = None           # model answer, only used to compute a similarity figure
    expected_concepts: list[str] | None = None    # concepts the rubric wants to see in the answer
    answer_type: AnswerType

    @field_validator("expected_concepts")
    @classmethod
    def validate_expected_concepts(
        cls, concepts: list[str] | None
    ) -> list[str] | None:
        """Reject blank concept strings and return the trimmed list (None stays None)."""
        # Reject lists that contain blank strings; otherwise return the trimmed concepts.
        if concepts is None:
            return None
        if any(not concept.strip() for concept in concepts):
            raise ValueError("expected_concepts cannot contain blank values")
        return [concept.strip() for concept in concepts]


class SentenceAnalysis(BaseModel):
    """One sentence of the student's answer. sentence_id starts at 1 and is what evidence refers to."""

    sentence_id: int = Field(ge=1)
    text: str


class ConceptMatch(BaseModel):
    """How well one expected concept is covered by the answer (token overlap, not semantic understanding)."""

    concept: str
    status: ConceptStatus                 # demonstrated / partial / not_demonstrated
    overlap_score: float = Field(ge=0.0, le=1.0)  # share of the concept's words found in the answer
    evidence_sentence_ids: list[int]      # sentences that contain at least one of the concept's words
    # Optional semantic layer (C3_SEMANTIC_MATCH=local). Absent/"lexical" means word matching only.
    # "semantic" = status upgraded by sentence-embedding similarity
    match_method: Literal["lexical", "semantic"] = "lexical"
    semantic_score: float | None = None                         # best sentence cosine similarity (informational)
    # Negation-cue check (services/semantic/negation.py): a POSSIBLE contradiction, never a verified error.
    # True = every sentence naming the concept also negates it; status is then not_demonstrated
    contradicted: bool = False
    # True = one sentence affirms the concept and another negates it (status unchanged)
    conflicting: bool = False
    negated_sentence_ids: list[int] = []  # sentences that name the concept next to a negation cue


class AnswerAnalysisResponse(BaseModel):
    """Result of Function 1; later steps (marking, feedback, mind map) are built from this evidence."""

    question_id: str
    normalized_answer: str
    sentence_count: int = Field(ge=0)
    token_count: int = Field(ge=0)
    sentences: list[SentenceAnalysis]
    reference_similarity: float = Field(ge=0.0, le=1.0)  # shown to the lecturer; does NOT change the mark
    concept_matches: list[ConceptMatch]
    warnings: list[str]
    analysis_version: str
    contradiction_check: str | None = None  # which contradiction rule ran (None = results made before it existed)
