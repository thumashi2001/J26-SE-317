import pytest
from pydantic import ValidationError

from app.schemas.marking import EvidenceRule, Rubric, RubricCriterion, ScoringLevel
from services.marking.rubric_validator import RubricValidationError, validate_rubric


def level(level_id: str = "L0", mark: float = 0, concepts: list[str] | None = None) -> ScoringLevel:
    return ScoringLevel(
        level_id=level_id,
        label=level_id,
        mark=mark,
        descriptor="A rubric descriptor.",
        required_concepts=concepts or [],
        evidence_requirements=[],
    )


def criterion(criterion_id: str = "C1", max_marks: float = 2, levels: list[ScoringLevel] | None = None) -> RubricCriterion:
    return RubricCriterion(
        criterion_id=criterion_id,
        description="A criterion.",
        max_marks=max_marks,
        scoring_levels=[level()] if levels is None else levels,
    )


def rubric(criteria: list[RubricCriterion] | None = None) -> Rubric:
    return Rubric(
        rubric_id="R1",
        title="Test rubric",
        criteria=[criterion()] if criteria is None else criteria,
    )


def test_valid_rubric() -> None:
    validate_rubric(rubric())


def test_empty_criteria_is_rejected() -> None:
    with pytest.raises(ValidationError):
        rubric([])


def test_duplicate_criterion_ids_are_rejected() -> None:
    with pytest.raises(RubricValidationError, match="duplicate criterion_id"):
        validate_rubric(rubric([criterion(), criterion()]))


def test_invalid_max_marks_is_rejected() -> None:
    with pytest.raises(ValidationError):
        criterion(max_marks=0)


def test_missing_scoring_levels_is_rejected() -> None:
    with pytest.raises(ValidationError):
        criterion(levels=[])


def test_duplicate_level_ids_are_rejected() -> None:
    with pytest.raises(RubricValidationError, match="duplicate level_id"):
        validate_rubric(rubric([criterion(levels=[level(), level()])]))


def test_negative_marks_are_rejected() -> None:
    with pytest.raises(ValidationError):
        level(mark=-1)


def test_level_exceeding_max_marks_is_rejected() -> None:
    with pytest.raises(RubricValidationError, match="exceeds"):
        validate_rubric(rubric([criterion(max_marks=1, levels=[level(mark=2)])]))


def test_blank_required_concept_is_rejected() -> None:
    with pytest.raises(ValidationError):
        level(concepts=[" "])


def test_blank_evidence_requirement_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ScoringLevel(
            level_id="L1",
            label="Level 1",
            mark=1,
            descriptor="Descriptor",
            evidence_requirements=[" "],
        )


def test_valid_evidence_rule_is_accepted() -> None:
    validate_rubric(
        rubric([
            criterion(
                levels=[
                    ScoringLevel(
                        level_id="L2",
                        label="Partial",
                        mark=2,
                        descriptor="Partial",
                        required_concepts=["security", "performance"],
                        evidence_rule=EvidenceRule(
                            type="required_concept_count",
                            minimum_demonstrated=1,
                        ),
                    )
                ]
            )
        ])
    )


def test_unsupported_evidence_rule_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceRule(type="unsupported", minimum_demonstrated=1)


def test_evidence_rule_threshold_cannot_exceed_required_concepts() -> None:
    with pytest.raises(RubricValidationError, match="exceeds required concepts"):
        validate_rubric(
            rubric([
                criterion(
                    levels=[
                        ScoringLevel(
                            level_id="L2",
                            label="Partial",
                            mark=2,
                            descriptor="Partial",
                            required_concepts=["security"],
                            evidence_rule=EvidenceRule(
                                type="required_concept_count",
                                minimum_demonstrated=2,
                            ),
                        )
                    ]
                )
            ])
        )


def test_combined_evidence_thresholds_equal_required_concepts_are_valid() -> None:
    validate_rubric(
        rubric([
            criterion(
                levels=[
                    ScoringLevel(
                        level_id="L2",
                        label="Partial",
                        mark=2,
                        descriptor="Partial",
                        required_concepts=["security", "performance"],
                        evidence_rule=EvidenceRule(
                            type="required_concept_count",
                            minimum_demonstrated=1,
                            minimum_partial=1,
                            allow_partial=True,
                        ),
                    )
                ]
            )
        ])
    )


def test_combined_evidence_thresholds_exceed_required_concepts() -> None:
    with pytest.raises(
        RubricValidationError,
        match="combined evidence thresholds exceed required concepts",
    ):
        validate_rubric(
            rubric([
                criterion(
                    levels=[
                        ScoringLevel(
                            level_id="L4",
                            label="Full",
                            mark=4,
                            descriptor="Full",
                            required_concepts=["security", "performance"],
                            evidence_rule=EvidenceRule(
                                type="required_concept_count",
                                minimum_demonstrated=2,
                                minimum_partial=1,
                                allow_partial=True,
                            ),
                        )
                    ]
                )
            ])
        )


def test_zero_partial_threshold_remains_valid() -> None:
    validate_rubric(
        rubric([
            criterion(
                max_marks=4,
                levels=[
                    ScoringLevel(
                        level_id="L4",
                        label="Full",
                        mark=4,
                        descriptor="Full",
                        required_concepts=["security", "performance"],
                        evidence_rule=EvidenceRule(
                            type="required_concept_count",
                            minimum_demonstrated=2,
                        ),
                    )
                ]
            )
        ])
    )


def test_partial_threshold_requires_explicit_permission() -> None:
    with pytest.raises(ValidationError):
        EvidenceRule(
            type="required_concept_count",
            minimum_partial=1,
            allow_partial=False,
        )
