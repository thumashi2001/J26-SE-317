from app.schemas.analysis import (
    AnswerAnalysisRequest,
    AnswerAnalysisResponse,
    ConceptMatch,
    SentenceAnalysis,
)
from app.schemas.marking import EvidenceRule, RubricCriterion, ScoringLevel
from services.marking.criterion_evaluator import evaluate_criterion
from services.semantic.analyzer import analyze_answer


def analysis(answer: str, concepts: list[str]) :
    return analyze_answer(
        AnswerAnalysisRequest(
            question_id="Q1",
            question_text="Explain two benefits.",
            student_answer=answer,
            expected_concepts=concepts,
            answer_type="short",
        )
    )


def criterion(levels: list[ScoringLevel]) -> RubricCriterion:
    return RubricCriterion(
        criterion_id="C1",
        description="Benefits",
        max_marks=4,
        scoring_levels=levels,
    )


def status_analysis(statuses: list[str]) -> AnswerAnalysisResponse:
    return AnswerAnalysisResponse(
        question_id="Q1",
        normalized_answer="Concept evidence.",
        sentence_count=len(statuses),
        token_count=3,
        sentences=[
            SentenceAnalysis(sentence_id=index, text=f"Concept {index}.")
            for index in range(1, len(statuses) + 1)
        ],
        reference_similarity=0.0,
        concept_matches=[
            ConceptMatch(
                concept=f"concept {index}",
                status=status,
                overlap_score=1.0 if status == "demonstrated" else 0.5 if status == "partial" else 0.0,
                evidence_sentence_ids=[index],
            )
            for index, status in enumerate(statuses, start=1)
        ],
        warnings=[],
        analysis_version="baseline-v1",
    )


def test_full_level_evidence_selects_full_level() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L4", label="Full", mark=4, descriptor="Both", required_concepts=["security", "performance"]),
        ]),
        analysis("Security and performance are benefits.", ["security", "performance"]),
    )
    assert result.selected_level_id == "L4"
    assert result.awarded_mark == 4
    assert result.evidence_sentence_ids == [1]


def test_partial_level_evidence_selects_explicit_partial_level() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L1", label="One", mark=1, descriptor="One", required_concepts=["security"]),
            ScoringLevel(level_id="L4", label="Two", mark=4, descriptor="Two", required_concepts=["security", "performance"]),
        ]),
        analysis("Security is a benefit.", ["security", "performance"]),
    )
    assert result.selected_level_id == "L1"
    assert result.awarded_mark == 1


def test_lowest_level_is_selected_when_no_positive_level_is_supported() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L2", label="Some", mark=2, descriptor="Some", required_concepts=["security"]),
        ]),
        analysis("An unrelated answer.", ["security"]),
    )
    assert result.selected_level_id == "L0"
    assert result.awarded_mark == 0
    assert result.warnings


def test_evidence_requirement_adds_sentence_evidence() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L2", label="Supported", mark=2, descriptor="Supported", evidence_requirements=["reduces cost"]),
        ]),
        analysis("Normalization reduces cost.", []),
    )
    assert result.selected_level_id == "L2"
    assert result.evidence_sentence_ids == [1]


def test_multiple_levels_select_highest_supported_level() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L1", label="One", mark=1, descriptor="One", required_concepts=["security"]),
            ScoringLevel(level_id="L2", label="Two", mark=2, descriptor="Two", required_concepts=["security"], evidence_requirements=["protects users"]),
        ]),
        analysis("Security protects users.", ["security"]),
    )
    assert result.selected_level_id == "L2"


def test_supporting_concepts_are_returned() -> None:
    result = evaluate_criterion(
        criterion([ScoringLevel(level_id="L1", label="One", mark=1, descriptor="One", required_concepts=["security"])]),
        analysis("Security matters.", ["security"]),
    )
    assert result.supporting_concepts == ["security"]


def test_insufficient_positive_level_requirements_produce_warning() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L1", label="Positive", mark=1, descriptor="Positive"),
        ]),
        analysis("An answer.", []),
    )
    assert result.awarded_mark == 0
    assert result.warnings


def test_no_arbitrary_percentage_rule_is_used() -> None:
    result = evaluate_criterion(
        criterion([ScoringLevel(level_id="L3", label="Explicit", mark=3, descriptor="Explicit", required_concepts=["security"])]),
        analysis("Security.", ["security"]),
    )
    assert result.awarded_mark == 3


def test_evidence_rule_selects_explicit_partial_level() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(
                level_id="L2",
                label="Partial",
                mark=2,
                descriptor="One demonstrated aspect",
                required_concepts=["concept 1", "concept 2"],
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_demonstrated=1,
                ),
            ),
            ScoringLevel(
                level_id="L4",
                label="Full",
                mark=4,
                descriptor="Two demonstrated aspects",
                required_concepts=["concept 1", "concept 2"],
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_demonstrated=2,
                ),
            ),
        ]),
        status_analysis(["demonstrated", "partial"]),
    )
    assert result.selected_level_id == "L2"
    assert result.awarded_mark == 2
    assert result.evidence_sentence_ids == [1]


def test_partial_concept_does_not_satisfy_demonstrated_rule() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(
                level_id="L2",
                label="Partial",
                mark=2,
                descriptor="One demonstrated aspect",
                required_concepts=["concept 1"],
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_demonstrated=1,
                ),
            ),
        ]),
        status_analysis(["partial"]),
    )
    assert result.selected_level_id == "L0"
    assert result.awarded_mark == 0


def test_explicit_rule_can_allow_partial_evidence() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(
                level_id="L1",
                label="Partial evidence",
                mark=1,
                descriptor="Partial evidence is accepted",
                required_concepts=["concept 1"],
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_partial=1,
                    allow_partial=True,
                ),
            ),
        ]),
        status_analysis(["partial"]),
    )
    assert result.selected_level_id == "L1"
    assert result.awarded_mark == 1


def test_evidence_rule_preserves_arbitrary_rubric_mark() -> None:
    result = evaluate_criterion(
        criterion([
            ScoringLevel(
                level_id="L3_5",
                label="Explicit mark",
                mark=3.5,
                descriptor="Explicit rubric mark",
                required_concepts=["concept 1"],
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_demonstrated=1,
                ),
            ),
        ]),
        status_analysis(["demonstrated"]),
    )
    assert result.awarded_mark == 3.5


def test_criterion_level_required_concepts_are_evaluated_strictly_but_can_be_lenient() -> None:
    c_strict = RubricCriterion(
        criterion_id="C1",
        description="Strict",
        max_marks=2,
        required_concepts=["concept 1", "concept 2"],
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(level_id="L2", label="Full", mark=2, descriptor="Both"),
        ],
    )
    result_strict = evaluate_criterion(c_strict, status_analysis(["demonstrated", "partial"]))
    assert result_strict.selected_level_id == "L0"
    assert result_strict.awarded_mark == 0

    c_lenient = RubricCriterion(
        criterion_id="C1",
        description="Lenient",
        max_marks=2,
        required_concepts=["concept 1", "concept 2"],
        scoring_levels=[
            ScoringLevel(level_id="L0", label="None", mark=0, descriptor="None"),
            ScoringLevel(
                level_id="L2",
                label="Full",
                mark=2,
                descriptor="Lenient",
                evidence_rule=EvidenceRule(
                    type="required_concept_count",
                    minimum_demonstrated=1,
                    minimum_partial=1,
                    allow_partial=True,
                ),
            ),
        ],
    )
    result_lenient = evaluate_criterion(c_lenient, status_analysis(["demonstrated", "partial"]))
    assert result_lenient.selected_level_id == "L2"
    assert result_lenient.awarded_mark == 2
