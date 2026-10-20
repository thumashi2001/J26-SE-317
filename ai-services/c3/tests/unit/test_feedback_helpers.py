"""Direct unit tests for services/feedback explanation_builder and evidence_formatter."""
from app.schemas.analysis import AnswerAnalysisResponse, ConceptMatch
from app.schemas.marking import CriterionMarkingResult, RubricCriterion, ScoringLevel
from services.feedback.evidence_formatter import concept_status_lists, evidence_warning
from services.feedback.explanation_builder import (
    build_explanation,
    build_improvement_suggestions,
    build_missing_or_partial_areas,
    build_strengths,
)


def make_result(
    awarded: float = 2.0,
    max_marks: float = 4.0,
    sentence_ids: list[int] | None = None,
    concepts: list[str] | None = None,
) -> CriterionMarkingResult:
    return CriterionMarkingResult(
        criterion_id="C1",
        criterion_description="Desc",
        selected_level_id="L2",
        selected_level_label="Mid",
        rubric_descriptor="Mid descriptor",
        awarded_mark=awarded,
        max_marks=max_marks,
        evidence_sentence_ids=[] if sentence_ids is None else sentence_ids,
        supporting_concepts=[] if concepts is None else concepts,
        explanation="x",
        warnings=[],
    )


def make_analysis(matches: dict[str, str]) -> AnswerAnalysisResponse:
    return AnswerAnalysisResponse(
        question_id="Q1",
        normalized_answer="text",
        sentence_count=1,
        token_count=1,
        sentences=[],
        reference_similarity=0.0,
        concept_matches=[
            ConceptMatch(concept=name, status=status, overlap_score=0.0, evidence_sentence_ids=[])
            for name, status in matches.items()
        ],
        warnings=[],
        analysis_version="baseline-v1",
    )


def make_criterion(levels: list[ScoringLevel], required: list[str] | None = None) -> RubricCriterion:
    return RubricCriterion(
        criterion_id="C1",
        description="d",
        max_marks=4,
        required_concepts=required or [],
        scoring_levels=levels,
    )


def lvl(level_id: str, mark: float, concepts: list[str] | None = None) -> ScoringLevel:
    return ScoringLevel(
        level_id=level_id, label=level_id, mark=mark, descriptor="d", required_concepts=concepts or []
    )


# ---------------- explanation_builder ----------------
def test_explanation_with_evidence_lists_concepts_and_ids() -> None:
    text = build_explanation(make_result(sentence_ids=[1, 3], concepts=["a", "b"]), make_analysis({}))
    assert "2/4" in text
    assert "Supporting concepts: a, b." in text
    assert "1, 3" in text
    assert "'L2'" in text


def test_explanation_without_evidence_does_not_claim_evidence() -> None:
    text = build_explanation(make_result(sentence_ids=[]), make_analysis({}))
    assert "No sentence-level evidence" in text
    assert "Supporting concepts" not in text


def test_explanation_zero_mark_formatting() -> None:
    text = build_explanation(make_result(awarded=0.0, sentence_ids=[]), make_analysis({}))
    assert "0/4" in text


def test_explanation_full_mark_formatting() -> None:
    text = build_explanation(make_result(awarded=4.0, sentence_ids=[2]), make_analysis({}))
    assert "4/4" in text


def test_explanation_fractional_mark_formatting() -> None:
    text = build_explanation(make_result(awarded=1.5, max_marks=3.5, sentence_ids=[1]), make_analysis({}))
    assert "1.5/3.5" in text


def test_explanation_no_supporting_concepts_says_none() -> None:
    text = build_explanation(make_result(sentence_ids=[1], concepts=[]), make_analysis({}))
    assert "Supporting concepts: none." in text


def test_build_strengths_empty_and_populated() -> None:
    assert build_strengths([]) == []
    out = build_strengths(["a", "b"])
    assert len(out) == 2
    assert out[0].endswith("a.")


def test_build_missing_or_partial_areas_empty() -> None:
    assert build_missing_or_partial_areas([], []) == []


def test_build_missing_or_partial_areas_orders_partial_before_missing() -> None:
    areas = build_missing_or_partial_areas(["p"], ["m"])
    assert len(areas) == 2
    assert "stronger or more complete" in areas[0] and areas[0].endswith("p.")
    assert "not demonstrated" in areas[1] and areas[1].endswith("m.")


def test_improvement_suggestions_partial_and_missing() -> None:
    out = build_improvement_suggestions(["p"], ["m"], has_evidence=True)
    assert out == ["Explain the relevant aspect of 'p' more explicitly.", "Add answer evidence addressing 'm'."]


def test_improvement_suggestions_empty_with_evidence_is_empty() -> None:
    assert build_improvement_suggestions([], [], has_evidence=True) == []


def test_improvement_suggestions_empty_without_evidence_gets_generic() -> None:
    out = build_improvement_suggestions([], [], has_evidence=False)
    assert len(out) == 1
    assert "traced" in out[0]


def test_improvement_suggestions_no_generic_when_concept_suggestions_exist() -> None:
    out = build_improvement_suggestions([], ["m"], has_evidence=False)
    assert out == ["Add answer evidence addressing 'm'."]


# ---------------- evidence_formatter ----------------
def test_evidence_warning_none_when_evidence_present() -> None:
    assert evidence_warning(make_result(sentence_ids=[1])) is None


def test_evidence_warning_when_no_evidence() -> None:
    warning = evidence_warning(make_result(sentence_ids=[]))
    assert warning is not None and "C1" in warning


def test_concept_status_lists_empty_inputs() -> None:
    criterion = make_criterion([lvl("L0", 0)])
    assert concept_status_lists(criterion, make_analysis({}), "L0") == ([], [], [], [])


def test_concept_status_lists_classifies_selected_level_concepts() -> None:
    criterion = make_criterion([lvl("L0", 0), lvl("L2", 2, ["a", "b", "c"])])
    analysis = make_analysis({"a": "demonstrated", "b": "partial", "c": "not_demonstrated"})
    assert concept_status_lists(criterion, analysis, "L2") == (["a"], ["b"], ["c"], [])


def test_concept_status_lists_missing_match_counts_as_missing() -> None:
    criterion = make_criterion([lvl("L2", 2, ["a"])])
    assert concept_status_lists(criterion, make_analysis({}), "L2") == ([], [], ["a"], [])


def test_concept_status_lists_is_case_insensitive() -> None:
    criterion = make_criterion([lvl("L2", 2, ["Alpha"])])
    result = concept_status_lists(criterion, make_analysis({"alpha": "demonstrated"}), "L2")
    assert result[0] == ["Alpha"]


def test_concept_status_lists_higher_level_concepts_go_to_next_level() -> None:
    criterion = make_criterion([lvl("L1", 1, ["a"]), lvl("L3", 3, ["a", "b"])])
    analysis = make_analysis({"a": "demonstrated", "b": "not_demonstrated"})
    assert concept_status_lists(criterion, analysis, "L1") == (["a"], [], [], ["b"])


def test_concept_status_lists_higher_level_demonstrated_is_reported_demonstrated() -> None:
    criterion = make_criterion([lvl("L1", 1, ["a"]), lvl("L3", 3, ["b"])])
    analysis = make_analysis({"a": "demonstrated", "b": "demonstrated"})
    demonstrated, _, _, next_level = concept_status_lists(criterion, analysis, "L1")
    assert demonstrated == ["a", "b"]
    assert next_level == []


def test_concept_status_lists_criterion_concepts_deferred_at_zero_level() -> None:
    criterion = make_criterion([lvl("L0", 0), lvl("L2", 2)], required=["x"])
    analysis = make_analysis({"x": "not_demonstrated"})
    assert concept_status_lists(criterion, analysis, "L0") == ([], [], [], ["x"])


def test_concept_status_lists_criterion_concepts_current_at_top_level() -> None:
    criterion = make_criterion([lvl("L0", 0), lvl("L2", 2)], required=["x"])
    analysis = make_analysis({"x": "partial"})
    assert concept_status_lists(criterion, analysis, "L2") == ([], ["x"], [], [])


def test_concept_status_lists_unknown_level_id_uses_criterion_concepts() -> None:
    criterion = make_criterion([lvl("L2", 2)], required=["x"])
    analysis = make_analysis({"x": "demonstrated"})
    assert concept_status_lists(criterion, analysis, "NOPE") == (["x"], [], [], [])
