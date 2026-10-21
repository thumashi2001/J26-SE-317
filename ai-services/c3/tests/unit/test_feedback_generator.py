from app.schemas.feedback import FeedbackRequest
from app.schemas.marking import (
    EvidenceRule,
    MarkingRequest,
    Rubric,
    RubricCriterion,
    ScoringLevel,
)
from services.feedback.generator import generate_feedback
from services.marking.marking_engine import mark_answer


def feedback_request(answer: str, concepts: list[str]) -> FeedbackRequest:
    rubric = Rubric(
        rubric_id="R1",
        title="Feedback rubric",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                description="Explain two concepts",
                max_marks=4,
                scoring_levels=[
                    ScoringLevel(
                        level_id="L0",
                        label="None",
                        mark=0,
                        descriptor="No evidence.",
                    ),
                    ScoringLevel(
                        level_id="L2",
                        label="Partial",
                        mark=2,
                        descriptor="One concept demonstrated.",
                        required_concepts=concepts,
                        evidence_rule=EvidenceRule(
                            type="required_concept_count",
                            minimum_demonstrated=1,
                        ),
                    ),
                    ScoringLevel(
                        level_id="L4",
                        label="Full",
                        mark=4,
                        descriptor="Two concepts demonstrated.",
                        required_concepts=concepts,
                        evidence_rule=EvidenceRule(
                            type="required_concept_count",
                            minimum_demonstrated=2,
                        ),
                    ),
                ],
            )
        ],
    )
    return FeedbackRequest(
        marking_request=MarkingRequest(
            question_id="Q1",
            question_text="Explain two concepts.",
            student_answer=answer,
            expected_concepts=concepts,
            answer_type="short",
            rubric=rubric,
        )
    )


def test_full_credit_feedback_reports_demonstrated_concepts_and_evidence() -> None:
    response = generate_feedback(
        feedback_request("Security matters. Performance improves.", ["security", "performance"])
    )
    criterion = response.criteria_feedback[0]
    assert response.overall_feedback.total_mark == 4
    assert criterion.selected_level_id == "L4"
    assert criterion.demonstrated_concepts == ["security", "performance"]
    assert criterion.evidence_sentence_ids == [1, 2]
    assert criterion.strengths
    assert "sentence IDs" in criterion.explanation


def test_partial_credit_feedback_preserves_function_two_mark() -> None:
    response = generate_feedback(
        feedback_request("Security matters. Performance is unclear.", ["security", "performance benefits"])
    )
    criterion = response.criteria_feedback[0]
    assert response.overall_feedback.total_mark == 2
    assert criterion.awarded_mark == 2
    assert criterion.demonstrated_concepts == ["security"]
    assert criterion.partial_concepts == ["performance benefits"]
    assert criterion.missing_concepts == []
    assert criterion.improvement_suggestions


def test_zero_credit_feedback_reports_missing_concepts_without_inventing_evidence() -> None:
    response = generate_feedback(
        feedback_request("An unrelated answer.", ["security", "performance"])
    )
    criterion = response.criteria_feedback[0]
    assert response.overall_feedback.total_mark == 0
    assert criterion.missing_concepts == []
    assert criterion.next_level_improvements == ["security", "performance"]
    assert criterion.evidence_sentence_ids == []
    assert any("No sentence-level evidence" in warning for warning in criterion.warnings)
    assert "No sentence-level evidence was available" in criterion.explanation


def test_multiple_criteria_are_aggregated_from_marking_output() -> None:
    request = feedback_request("Security matters. Performance improves.", ["security", "performance"])
    request.marking_request.rubric.criteria.append(
        RubricCriterion(
            criterion_id="C2",
            description="Security",
            max_marks=1,
            scoring_levels=[
                ScoringLevel(
                    level_id="L1",
                    label="Supported",
                    mark=1,
                    descriptor="Security supported.",
                    required_concepts=["security"],
                )
            ],
        )
    )
    response = generate_feedback(request)
    assert response.overall_feedback.total_mark == 5
    assert len(response.criteria_feedback) == 2
    assert response.overall_feedback.total_possible == 5


def test_function_3_preserves_function_2_selected_level_and_mark() -> None:
    request = feedback_request("Security matters. Performance is unclear.", ["security", "performance benefits"])
    response = generate_feedback(request)
    criterion = response.criteria_feedback[0]

    # Function 2 marks this as Level L2 (1 concept demonstrated) with a mark of 2
    assert criterion.selected_level_id == "L2"
    assert criterion.awarded_mark == 2.0


def test_higher_level_concepts_are_not_reported_as_missing() -> None:
    rubric = Rubric(
        rubric_id="R2",
        title="Higher level test",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                description="Test L1 vs L2",
                max_marks=2,
                scoring_levels=[
                    ScoringLevel(
                        level_id="L1",
                        label="Partial",
                        mark=1,
                        descriptor="L1 requires auth.",
                        required_concepts=["authentication"],
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=1),
                    ),
                    ScoringLevel(
                        level_id="L2",
                        label="Full",
                        mark=2,
                        descriptor="L2 requires auth and enc.",
                        required_concepts=["authentication", "encryption"],
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=2),
                    ),
                ],
            )
        ],
    )
    request = FeedbackRequest(
        marking_request=MarkingRequest(
            question_id="Q2",
            question_text="Auth test",
            student_answer="I use authentication.",
            expected_concepts=["authentication", "encryption"],
            answer_type="short",
            rubric=rubric,
        )
    )
    response = generate_feedback(request)
    criterion = response.criteria_feedback[0]

    assert criterion.selected_level_id == "L1"
    assert criterion.awarded_mark == 1.0

    # Authentication is required by L1 and is demonstrated
    assert "authentication" in criterion.demonstrated_concepts

    # Encryption is required by L2 but we only selected L1, so it should NOT be in missing_concepts
    assert "encryption" not in criterion.missing_concepts

    # It SHOULD be in next_level_improvements
    assert "encryption" in criterion.next_level_improvements


# =========================================================================
# Regression Tests for Criterion-level required_concepts & Score Authority
# =========================================================================


def test_criterion_concepts_propagated_to_analysis_when_root_concepts_absent() -> None:
    """Requirement 8A: Criterion concepts are propagated into Function 1 analysis."""
    rubric = Rubric(
        rubric_id="R-PROP",
        title="Propagation Rubric",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                description="Database normal forms",
                max_marks=2,
                required_concepts=["1NF", "Atomic values"],
                scoring_levels=[
                    ScoringLevel(
                        level_id="L0",
                        label="None",
                        mark=0,
                        descriptor="No explanation.",
                    ),
                    ScoringLevel(
                        level_id="L2",
                        label="Full",
                        mark=2,
                        descriptor="1NF and atomic values explained.",
                    ),
                ],
            )
        ],
    )
    request = FeedbackRequest(
        marking_request=MarkingRequest(
            question_id="Q-PROP",
            question_text="Explain 1NF.",
            student_answer="1NF requires each attribute to contain atomic values.",
            expected_concepts=None,  # Root concepts absent!
            answer_type="short",
            rubric=rubric,
        )
    )
    response = generate_feedback(request)
    criterion = response.criteria_feedback[0]

    # Analysis must have received the criterion concepts and generated evidence
    assert len(criterion.evidence_sentence_ids) > 0
    assert "1NF" in criterion.demonstrated_concepts
    assert "Atomic values" in criterion.demonstrated_concepts


def test_selected_level_without_own_concepts_uses_criterion_required_concepts() -> None:
    """Requirements 8B & 8C: Criterion concepts appear in demonstrated/missing classification."""
    rubric = Rubric(
        rubric_id="R-CRIT-CONCEPTS",
        title="Criterion concepts without level concepts",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                description="Database normalization",
                max_marks=2,
                required_concepts=["1NF", "Atomic values"],
                scoring_levels=[
                    ScoringLevel(
                        level_id="L0",
                        label="Not Demonstrated",
                        mark=0,
                        descriptor="No explanation.",
                    ),
                    ScoringLevel(
                        level_id="L1",
                        label="Partial",
                        mark=1,
                        descriptor="Explains 1NF partially.",
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=1),
                    ),
                    ScoringLevel(
                        level_id="L2",
                        label="Full",
                        mark=2,
                        descriptor="Fully explains 1NF and atomic values.",
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=2),
                    ),
                ],
            )
        ],
    )
    # Student mentions 1NF but misses Atomic values
    request = FeedbackRequest(
        marking_request=MarkingRequest(
            question_id="Q-CRIT",
            question_text="Explain 1NF and atomic values.",
            student_answer="1NF means no repeating groups in tables.",
            expected_concepts=None,
            answer_type="short",
            rubric=rubric,
        )
    )
    response = generate_feedback(request)
    criterion = response.criteria_feedback[0]

    # 1NF is demonstrated, Atomic values is missing
    assert "1NF" in criterion.demonstrated_concepts
    assert "Atomic values" in criterion.missing_concepts
    assert any("Atomic values" in suggestion for suggestion in criterion.improvement_suggestions)


def test_higher_level_criterion_concepts_not_reported_as_missing_when_not_required() -> None:
    """Requirement 8D: Higher-level criterion concepts are not incorrectly reported as missing."""
    rubric = Rubric(
        rubric_id="R-HIGHER-CRIT",
        title="Higher level criterion concepts",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                description="Explain normal forms",
                max_marks=2,
                required_concepts=["1NF", "2NF"],
                scoring_levels=[
                    ScoringLevel(
                        level_id="L1",
                        label="Basic",
                        mark=1,
                        descriptor="Requires 1NF only.",
                        required_concepts=["1NF"],
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=1),
                    ),
                    ScoringLevel(
                        level_id="L2",
                        label="Advanced",
                        mark=2,
                        descriptor="Requires 1NF and 2NF.",
                        required_concepts=["1NF", "2NF"],
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=2),
                    ),
                ],
            )
        ],
    )
    # Answer only provides 1NF
    request = FeedbackRequest(
        marking_request=MarkingRequest(
            question_id="Q-H-CRIT",
            question_text="Explain 1NF and 2NF.",
            student_answer="1NF requires atomic values and no repeating groups.",
            expected_concepts=None,
            answer_type="short",
            rubric=rubric,
        )
    )
    response = generate_feedback(request)
    criterion = response.criteria_feedback[0]

    assert criterion.selected_level_id == "L1"
    assert criterion.awarded_mark == 1.0
    assert "1NF" in criterion.demonstrated_concepts
    # 2NF is required only by L2 (higher level), so it must NOT be in missing_concepts for L1
    assert "2NF" not in criterion.missing_concepts
    assert "2NF" in criterion.next_level_improvements


def test_function_3_preserves_exact_function_2_marks_and_selected_level() -> None:
    """Requirement 8E: Function 3 preserves Function 2's exact mark and selected level."""
    rubric = Rubric(
        rubric_id="R-AUTHORITY",
        title="Authority Check Rubric",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                description="Criterion 1",
                max_marks=3,
                required_concepts=["authentication", "authorization"],
                scoring_levels=[
                    ScoringLevel(
                        level_id="L0",
                        label="Zero",
                        mark=0,
                        descriptor="None.",
                    ),
                    ScoringLevel(
                        level_id="L1",
                        label="Partial",
                        mark=1.5,
                        descriptor="One concept.",
                        required_concepts=["authentication"],
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=1),
                    ),
                    ScoringLevel(
                        level_id="L2",
                        label="Full",
                        mark=3,
                        descriptor="Both concepts.",
                        required_concepts=["authentication", "authorization"],
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=2),
                    ),
                ],
            )
        ],
    )
    request = FeedbackRequest(
        marking_request=MarkingRequest(
            question_id="Q-AUTH",
            question_text="Security concepts",
            student_answer="Authentication verifies identity.",
            expected_concepts=None,
            answer_type="short",
            rubric=rubric,
        )
    )
    marking_result = mark_answer(request.marking_request)
    feedback_result = generate_feedback(request)

    assert feedback_result.overall_feedback.total_mark == marking_result.total_awarded_marks
    assert feedback_result.overall_feedback.total_possible == marking_result.total_possible_marks
    assert feedback_result.overall_feedback.percentage == marking_result.percentage

    crit_mark = marking_result.criteria_results[0]
    crit_fb = feedback_result.criteria_feedback[0]

    assert crit_fb.awarded_mark == crit_mark.awarded_mark
    assert crit_fb.selected_level_id == crit_mark.selected_level_id
    assert crit_fb.evidence_sentence_ids == crit_mark.evidence_sentence_ids
    assert crit_fb.supporting_concepts == crit_mark.supporting_concepts
