"""Characterization tests for services/marking/criterion_evaluator.py.

Known bugs are written as the CORRECT expected behaviour under strict xfail.
"""
import pytest

from app.schemas.analysis import AnswerAnalysisRequest
from app.schemas.marking import EvidenceRule, RubricCriterion, ScoringLevel
from services.marking.criterion_evaluator import evaluate_criterion
from services.semantic.analyzer import analyze_answer


def analysis(answer: str, concepts: list[str] | None = None):
    return analyze_answer(
        AnswerAnalysisRequest(
            question_id="Q1",
            question_text="Q?",
            student_answer=answer,
            expected_concepts=concepts,
            answer_type="short",
        )
    )


def lvl(level_id: str, mark: float, concepts=None, requirements=None, rule=None) -> ScoringLevel:
    return ScoringLevel(
        level_id=level_id,
        label=level_id,
        mark=mark,
        descriptor="d",
        required_concepts=concepts or [],
        evidence_requirements=requirements or [],
        evidence_rule=rule,
    )


def crit(levels: list[ScoringLevel], concepts: list[str] | None = None) -> RubricCriterion:
    return RubricCriterion(
        criterion_id="C1",
        description="d",
        max_marks=4,
        required_concepts=concepts or [],
        scoring_levels=levels,
    )


# ---------------------------------------------------------------- correct behaviours
def test_highest_supported_level_is_chosen_regardless_of_declaration_order() -> None:
    levels = [
        lvl("L4", 4, ["security", "speed"]),
        lvl("L0", 0),
        lvl("L2", 2, ["security"]),
    ]
    result = evaluate_criterion(crit(levels), analysis("Security and speed matter.", ["security", "speed"]))
    assert result.selected_level_id == "L4"
    result = evaluate_criterion(crit(levels), analysis("Security matters.", ["security", "speed"]))
    assert result.selected_level_id == "L2"


def test_zero_level_fallback_when_zero_level_exists() -> None:
    levels = [lvl("L0", 0), lvl("L2", 2, ["security"])]
    result = evaluate_criterion(crit(levels), analysis("Cooking dinner.", ["security"]))
    assert result.selected_level_id == "L0"
    assert result.awarded_mark == 0
    assert result.warnings


def test_positive_level_without_any_requirements_is_never_selected() -> None:
    levels = [lvl("L0", 0), lvl("L3", 3)]
    result = evaluate_criterion(crit(levels), analysis("Anything at all."))
    assert result.selected_level_id == "L0"
    assert result.awarded_mark == 0


def test_zero_level_with_no_requirements_is_selected_without_requirement_reasons() -> None:
    result = evaluate_criterion(crit([lvl("L0", 0)]), analysis("Anything."))
    assert result.selected_level_id == "L0"
    assert result.awarded_mark == 0


def test_empty_answer_gets_zero_level() -> None:
    levels = [lvl("L0", 0), lvl("L2", 2, ["security"])]
    result = evaluate_criterion(crit(levels), analysis("", ["security"]))
    assert result.awarded_mark == 0
    assert result.evidence_sentence_ids == []


def test_awarded_mark_never_exceeds_declared_level_mark() -> None:
    levels = [lvl("L0", 0), lvl("L3", 3, ["security"])]
    result = evaluate_criterion(crit(levels), analysis("Security.", ["security"]))
    assert result.awarded_mark == 3 and result.max_marks == 4


def test_tie_between_equal_marks_prefers_first_declared_supported_level() -> None:
    levels = [lvl("A", 2, ["security"]), lvl("B", 2, ["security"])]
    result = evaluate_criterion(crit(levels), analysis("Security.", ["security"]))
    assert result.selected_level_id == "A"


def test_unsupported_evidence_requirement_blocks_level() -> None:
    levels = [lvl("L0", 0), lvl("L2", 2, requirements=["normalization reduces storage"])]
    result = evaluate_criterion(crit(levels), analysis("Unrelated words here."))
    assert result.selected_level_id == "L0"


# ---------------------------------------------------------------- known bugs
@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-M1: with no zero-mark level and an answer supporting no level, the lowest POSITIVE "
    "level (L2, 2 marks) is awarded with a warning (criterion_evaluator.py:175-184); expected 0 marks",
)
def test_no_zero_level_and_unsupported_answer_awards_zero() -> None:
    levels = [lvl("L2", 2, ["security"]), lvl("L4", 4, ["security", "speed"])]
    result = evaluate_criterion(crit(levels), analysis("Cooking dinner tonight.", ["security", "speed"]))
    assert result.awarded_mark == 0


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-M4: criterion.required_concepts are merged into every level (criterion_evaluator.py:21-32), "
    "so L1 (needs 'security') also demands 'speed'; answer demonstrating only 'security' gets L0/0 marks, "
    "expected L1/1 mark",
)
def test_partial_level_reachable_when_only_some_criterion_concepts_demonstrated() -> None:
    levels = [
        lvl("L0", 0),
        lvl("L1", 1, ["security"]),
        lvl("L2", 2, ["security", "speed"]),
    ]
    result = evaluate_criterion(
        crit(levels, concepts=["security", "speed"]),
        analysis("Security is key.", ["security", "speed"]),
    )
    assert result.selected_level_id == "L1"
    assert result.awarded_mark == 1


def test_criterion_concepts_are_merged_into_every_level_current_behaviour() -> None:
    """Documents the M4 mechanism: criterion concepts apply to all levels, so a full answer still wins."""
    levels = [lvl("L0", 0), lvl("L1", 1, ["security"]), lvl("L2", 2, ["security", "speed"])]
    result = evaluate_criterion(
        crit(levels, concepts=["security", "speed"]),
        analysis("Security and speed.", ["security", "speed"]),
    )
    assert result.selected_level_id == "L2"


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-M5: evidence requirement 'normalization reduces storage cost' is satisfied by the single "
    "incidental token 'cost' (criterion_evaluator.py:105-113 uses overlap > 0); answer 'The cost of a car is "
    "high.' awards L2/2 marks, expected 0",
)
def test_single_shared_token_does_not_satisfy_multiword_evidence_requirement() -> None:
    levels = [lvl("L0", 0), lvl("L2", 2, requirements=["normalization reduces storage cost"])]
    result = evaluate_criterion(crit(levels), analysis("The cost of a car is high."))
    assert result.awarded_mark == 0


def test_evidence_requirement_fully_present_is_satisfied() -> None:
    levels = [lvl("L0", 0), lvl("L2", 2, requirements=["reduces cost"])]
    result = evaluate_criterion(crit(levels), analysis("Normalization reduces cost."))
    assert result.awarded_mark == 2


def test_evidence_rule_with_criterion_concepts_selects_partial_level() -> None:
    """The documented workaround for M4: an explicit evidence_rule makes partial levels reachable."""
    rule = EvidenceRule(type="required_concept_count", minimum_demonstrated=1)
    levels = [
        lvl("L0", 0),
        lvl("L1", 1, rule=rule),
        lvl("L2", 2, rule=EvidenceRule(type="required_concept_count", minimum_demonstrated=2)),
    ]
    result = evaluate_criterion(
        crit(levels, concepts=["security", "speed"]),
        analysis("Security is key.", ["security", "speed"]),
    )
    assert result.selected_level_id == "L1"
