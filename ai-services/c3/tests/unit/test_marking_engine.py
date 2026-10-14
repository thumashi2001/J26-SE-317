import pytest
from pydantic import ValidationError

from app.schemas.marking import (
    EvidenceRule,
    MarkingRequest,
    Rubric,
    RubricCriterion,
    ScoringLevel,
)
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
    empty_criterion = RubricCriterion(
        criterion_id="C1",
        description="C1",
        max_marks=2,
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None")
        ],
    )
    result = mark_answer(request([empty_criterion], answer="An answer."))
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


def test_integration_missing_root_concepts_extracts_from_rubric() -> None:
    answer = (
        "1NF means that each field should contain a single atomic value and there should not be repeating groups. "
        "2NF removes partial dependencies from a composite key. "
        "3NF removes transitive dependencies so non-key attributes depend on the primary key. "
        "These forms help reduce redundancy and improve database design."
    )

    c1 = RubricCriterion(
        criterion_id="C1",
        description="1NF and atomic values",
        max_marks=2,
        required_concepts=["1NF", "Atomic values"],
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L1", label="Partial", mark=1, descriptor="Some"),
            ScoringLevel(level_id="L2", label="Full", mark=2, descriptor="Both"),
        ],
    )
    c2 = RubricCriterion(
        criterion_id="C2",
        description="2NF and partial dependency",
        max_marks=2,
        required_concepts=["2NF", "Partial dependency"],
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L1", label="Partial", mark=1, descriptor="Some"),
            ScoringLevel(level_id="L2", label="Full", mark=2, descriptor="Both"),
        ],
    )
    c3 = RubricCriterion(
        criterion_id="C3",
        description="3NF and transitive dependency",
        max_marks=2,
        required_concepts=["3NF", "Transitive dependency"],
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L1", label="Partial", mark=1, descriptor="Some"),
            ScoringLevel(level_id="L2", label="Full", mark=2, descriptor="Both"),
        ],
    )
    c4 = RubricCriterion(
        criterion_id="C4",
        description="Redundancy",
        max_marks=2,
        required_concepts=["Data redundancy"],
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L1", label="Partial", mark=1, descriptor="Some"),
            ScoringLevel(level_id="L2", label="Full", mark=2, descriptor="Full"),
        ],
    )

    req = MarkingRequest(
        question_id="Q1",
        question_text="Explain the three normal forms 1NF, 2NF, and 3NF in database normalization.",
        student_answer=answer,
        reference_answer="1NF, 2NF, 3NF reduce data redundancy.",
        expected_concepts=None,
        answer_type="short",
        rubric=Rubric(rubric_id="R1", title="Normalization", criteria=[c1, c2, c3, c4]),
    )

    result = mark_answer(req)
    assert "expected_concepts were not provided" not in result.warnings
    assert result.criteria_results[0].supporting_concepts == ["1NF"]
    assert result.criteria_results[1].supporting_concepts == ["2NF"]
    assert result.criteria_results[2].supporting_concepts == ["3NF"]
    assert result.criteria_results[3].supporting_concepts == []
    # Strict policy correctly enforces 0 marks because partial concepts are not converted to demonstrated
    assert result.total_awarded_marks == 0.0


def test_integration_partial_credit_policy() -> None:
    answer = (
        "1NF means that each field should contain a single atomic value and there should not be repeating groups. "
        "2NF removes partial dependencies from a composite key. "
        "3NF removes transitive dependencies so non-key attributes depend on the primary key. "
        "These forms help reduce redundancy and improve database design."
    )

    c1 = RubricCriterion(
        criterion_id="C1",
        description="1NF and atomic values",
        max_marks=2,
        required_concepts=["1NF", "Atomic values"],
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(
                level_id="L1",
                label="Partial credit",
                mark=1,
                descriptor="At least one demonstrated and one partial",
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_demonstrated=1,
                    minimum_partial=1,
                    allow_partial=True,
                ),
            ),
            ScoringLevel(
                level_id="L2",
                label="Full credit",
                mark=2,
                descriptor="Both demonstrated",
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_demonstrated=2,
                ),
            ),
        ],
    )

    req = MarkingRequest(
        question_id="Q1",
        question_text="Explain the three normal forms 1NF, 2NF, and 3NF in database normalization.",
        student_answer=answer,
        reference_answer="1NF, 2NF, 3NF reduce data redundancy.",
        expected_concepts=None,
        answer_type="short",
        rubric=Rubric(rubric_id="R1", title="Normalization", criteria=[c1]),
    )

    result = mark_answer(req)
    assert result.criteria_results[0].selected_level_id == "L1"
    assert result.criteria_results[0].awarded_mark == 1.0
    assert "1NF" in result.criteria_results[0].supporting_concepts
    assert "Atomic values" in result.criteria_results[0].supporting_concepts
