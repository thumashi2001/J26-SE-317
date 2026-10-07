from app.schemas.feedback import FeedbackRequest
from app.schemas.marking import EvidenceRule, MarkingRequest, Rubric, RubricCriterion, ScoringLevel
from services.feedback.generator import generate_feedback


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
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=1)
                    ),
                    ScoringLevel(
                        level_id="L2",
                        label="Full",
                        mark=2,
                        descriptor="L2 requires auth and enc.",
                        required_concepts=["authentication", "encryption"],
                        evidence_rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=2)
                    ),
                ]
            )
        ]
    )
    request = FeedbackRequest(
        marking_request=MarkingRequest(
            question_id="Q2",
            question_text="Auth test",
            student_answer="I use authentication.",
            expected_concepts=["authentication", "encryption"],
            answer_type="short",
            rubric=rubric
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
