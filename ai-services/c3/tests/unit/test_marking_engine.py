import pytest
from pydantic import ValidationError

from app.schemas.marking import MarkingRequest, Rubric, RubricCriterion, ScoringLevel
from services.marking.marking_engine import mark_answer
from services.marking.rubric_validator import RubricValidationError


def request(criteria: list[RubricCriterion], answer: str = "Security and performance are benefits.", reference: str | None = None, concepts: list[str] | None = None) -> MarkingRequest:
    return MarkingRequest(
        question_id="Q1",
        question_text="Explain two benefits.",
        student_answer=answer,
        reference_answer=reference,
        expected_concepts=concepts,
        answer_type="short",
        rubric=Rubric(rubric_id="R1", title="Benefits", criteria=criteria),
    )


def criterion(criterion_id: str, max_marks: float, concept: str, mark: float) -> RubricCriterion:
    return RubricCriterion(
        criterion_id=criterion_id,
        description=criterion_id,
        max_marks=max_marks,
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L1", label="Supported", mark=mark, descriptor="Supported", required_concepts=[concept]),
        ],
    )


def test_single_criterion_and_totals() -> None:
    result = mark_answer(request([criterion("C1", 4, "security", 4)], concepts=["security"]))
    assert result.total_awarded_marks == 4
    assert result.total_possible_marks == 4
    assert result.percentage == 100.0


def test_multiple_criteria_are_aggregated() -> None:
    result = mark_answer(request([
        criterion("C1", 2, "security", 2),
        criterion("C2", 3, "performance", 3),
    ], concepts=["security", "performance"]))
    assert result.total_awarded_marks == 5
    assert result.total_possible_marks == 5
    assert result.percentage == 100.0
    assert [item.criterion_id for item in result.criteria_results] == ["C1", "C2"]


def test_criterion_explanations_and_version_are_returned() -> None:
    result = mark_answer(request([criterion("C1", 2, "security", 2)], concepts=["security"]))
    assert result.criteria_results[0].explanation
    assert result.marking_version == "baseline-v1"
    assert "criterion marks" in result.overall_explanation


def test_warnings_include_missing_reference_and_concepts() -> None:
    result = mark_answer(request([criterion("C1", 2, "security", 2)], answer="An answer."))
    assert "reference_answer was not provided" in result.warnings
    assert "expected_concepts were not provided" in result.warnings


def test_empty_student_answer_is_safe() -> None:
    result = mark_answer(request([criterion("C1", 2, "security", 2)], answer=""))
    assert result.total_awarded_marks == 0
    assert "student_answer is empty or contains only whitespace" in result.warnings


def test_invalid_rubric_is_rejected() -> None:
    invalid = request([criterion("C1", 1, "security", 2)], concepts=["security"])
    with pytest.raises(RubricValidationError):
        mark_answer(invalid)


def test_missing_required_request_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        MarkingRequest.model_validate({"question_id": "Q1"})
