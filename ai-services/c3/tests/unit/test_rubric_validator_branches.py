"""Branch-level tests for validate_rubric.

Pydantic already rejects: empty criteria/levels, max_marks <= 0, negative marks, blank descriptions or
concepts, and EvidenceRule with zero thresholds or inconsistent allow_partial. validate_rubric is the
second line of defence; those branches are exercised by bypassing Pydantic with model_construct.
Only duplicate ids, level mark > max_marks and concept-count checks are reachable via normal input.
"""
import pytest
from pydantic import ValidationError

from app.schemas.marking import EvidenceRule, Rubric, RubricCriterion, ScoringLevel
from services.marking.rubric_validator import RubricValidationError, validate_rubric


def level(level_id="L1", mark=1.0, concepts=None, rule=None, requirements=None) -> ScoringLevel:
    return ScoringLevel(
        level_id=level_id,
        label=level_id,
        mark=mark,
        descriptor="d",
        required_concepts=concepts or [],
        evidence_requirements=requirements or [],
        evidence_rule=rule,
    )


def criterion(levels, criterion_id="C1", max_marks=4.0, concepts=None) -> RubricCriterion:
    return RubricCriterion(
        criterion_id=criterion_id,
        description="d",
        max_marks=max_marks,
        required_concepts=concepts or [],
        scoring_levels=levels,
    )


def rubric(*criteria) -> Rubric:
    return Rubric(rubric_id="R", title="T", criteria=list(criteria))


def errors_of(r: Rubric) -> list[str]:
    with pytest.raises(RubricValidationError) as info:
        validate_rubric(r)
    return info.value.errors


def test_error_message_joins_all_errors_and_exposes_list() -> None:
    r = rubric(criterion([level("L1", 1), level("L1", 9)], max_marks=2))
    errs = errors_of(r)
    assert any("duplicate level_id L1" in e for e in errs)
    assert any("exceeds" in e for e in errs)
    with pytest.raises(RubricValidationError) as info:
        validate_rubric(r)
    assert str(info.value) == "; ".join(errs)


def test_mark_equal_to_max_marks_is_valid() -> None:
    validate_rubric(rubric(criterion([level("L4", 4)], max_marks=4)))


def test_mark_just_above_max_marks_is_rejected() -> None:
    errs = errors_of(rubric(criterion([level("L4", 4.01)], max_marks=4)))
    assert errs == ["level L4 mark exceeds criterion C1 max_marks"]


def test_duplicate_level_ids_allowed_across_different_criteria() -> None:
    validate_rubric(rubric(criterion([level("L1", 1)], "C1"), criterion([level("L1", 1)], "C2")))


def test_errors_are_collected_across_criteria() -> None:
    errs = errors_of(rubric(criterion([level("L9", 9)], "C1", 2), criterion([level("L9", 9)], "C2", 2)))
    assert len(errs) == 2


def test_evidence_rule_uses_criterion_level_concepts() -> None:
    rule = EvidenceRule(type="required_concept_count", minimum_demonstrated=2)
    validate_rubric(rubric(criterion([level(rule=rule)], concepts=["a", "b"])))


def test_evidence_rule_counts_union_of_criterion_and_level_concepts_case_insensitively() -> None:
    rule = EvidenceRule(type="required_concept_count", minimum_demonstrated=2)
    # "A" and "a" are one concept, so only one effective concept exists for a threshold of two.
    errs = errors_of(rubric(criterion([level(concepts=["A"], rule=rule)], concepts=["a"])))
    assert "level L1 minimum_demonstrated exceeds required concepts" in errs


def test_evidence_rule_without_any_concepts_is_rejected() -> None:
    rule = EvidenceRule(type="required_concept_count", minimum_demonstrated=1)
    errs = errors_of(rubric(criterion([level(rule=rule)])))
    assert "level L1 evidence_rule requires required_concepts" in errs
    assert "level L1 minimum_demonstrated exceeds required concepts" in errs


def test_minimum_partial_exceeding_concepts_is_rejected() -> None:
    rule = EvidenceRule(type="required_concept_count", minimum_partial=3, allow_partial=True)
    errs = errors_of(rubric(criterion([level(concepts=["a", "b"], rule=rule)])))
    assert "level L1 minimum_partial exceeds required concepts" in errs


def test_partial_plus_demonstrated_exceeding_concepts_is_rejected_even_if_each_fits() -> None:
    rule = EvidenceRule(type="required_concept_count", minimum_demonstrated=2, minimum_partial=2, allow_partial=True)
    errs = errors_of(rubric(criterion([level(concepts=["a", "b", "c"], rule=rule)])))
    assert errs == ["level L1 combined evidence thresholds exceed required concepts"]


@pytest.mark.parametrize(
    "build",
    [
        lambda: EvidenceRule(type="required_concept_count"),
        lambda: EvidenceRule(type="required_concept_count", minimum_partial=1),
        lambda: EvidenceRule(type="required_concept_count", minimum_demonstrated=1, allow_partial=True),
        lambda: EvidenceRule(type="required_concept_count", minimum_demonstrated=-1),
    ],
)
def test_pydantic_already_rejects_bad_evidence_rule_thresholds(build) -> None:
    with pytest.raises(ValidationError):
        build()


def test_pydantic_already_rejects_negative_mark_and_zero_max_marks() -> None:
    with pytest.raises(ValidationError):
        level("L1", -1)
    with pytest.raises(ValidationError):
        criterion([level()], max_marks=0)


def test_blank_description_is_rejected_by_pydantic_after_strip() -> None:
    with pytest.raises(ValidationError):
        RubricCriterion(criterion_id="C1", description="   ", max_marks=1, scoring_levels=[level()])


# ---- branches only reachable by bypassing Pydantic ----
def test_validator_catches_blank_description_when_pydantic_bypassed() -> None:
    c = RubricCriterion.model_construct(
        criterion_id="C1", description="  ", max_marks=1.0, required_concepts=[], scoring_levels=[level()]
    )
    r = Rubric.model_construct(rubric_id="R", title="T", criteria=[c])
    assert "criterion C1 has a blank description" in errors_of(r)


def test_validator_catches_non_positive_max_marks_when_bypassed() -> None:
    c = RubricCriterion.model_construct(
        criterion_id="C1", description="d", max_marks=0.0, required_concepts=[], scoring_levels=[level("L0", 0)]
    )
    r = Rubric.model_construct(rubric_id="R", title="T", criteria=[c])
    assert "criterion C1 max_marks must be greater than zero" in errors_of(r)


def test_validator_catches_empty_criteria_and_empty_levels_when_bypassed() -> None:
    assert errors_of(Rubric.model_construct(rubric_id="R", title="T", criteria=[])) == [
        "rubric must contain at least one criterion"
    ]
    c = RubricCriterion.model_construct(
        criterion_id="C1", description="d", max_marks=1.0, required_concepts=[], scoring_levels=[]
    )
    assert "criterion C1 must contain scoring levels" in errors_of(
        Rubric.model_construct(rubric_id="R", title="T", criteria=[c])
    )


def test_validator_catches_blank_concepts_requirements_and_negative_mark_when_bypassed() -> None:
    bad_level = ScoringLevel.model_construct(
        level_id="L1",
        label="L1",
        mark=-1.0,
        descriptor="d",
        required_concepts=[" "],
        evidence_requirements=[" "],
        evidence_rule=None,
    )
    c = RubricCriterion.model_construct(
        criterion_id="C1", description="d", max_marks=2.0, required_concepts=[""], scoring_levels=[bad_level]
    )
    errs = errors_of(Rubric.model_construct(rubric_id="R", title="T", criteria=[c]))
    assert "criterion C1 has a blank required concept" in errs
    assert "level L1 cannot have a negative mark" in errs
    assert "level L1 has a blank required concept" in errs
    assert "level L1 has an invalid evidence requirement" in errs
