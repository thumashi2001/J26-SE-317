"""Function 3: assemble the feedback object (per-criterion explanations, strengths, gaps and improvement advice).

SIMPLE ENGLISH
    The marking engine has already decided the marks. This module only WRITES ABOUT that decision: for each criterion
    it lists which concepts were found, which are partly covered, which are missing, and what to improve next. The
    wording comes from rule-based text builders in explanation_builder.py (no language model), and nothing here can
    change a mark.
"""
from app.schemas.analysis import AnswerAnalysisRequest, AnswerAnalysisResponse
from app.schemas.feedback import (
    CriterionFeedback,
    FeedbackRequest,
    FeedbackResponse,
    OverallFeedback,
)
from app.schemas.marking import MarkingResponse, Rubric
from services.feedback.evidence_formatter import (
    concept_status_lists,
    evidence_warning,
)
from services.feedback.explanation_builder import (
    build_contextual_improvements,
    build_explanation,
    build_missing_or_partial_areas,
    build_strengths,
)
from services.marking.marking_engine import mark_answer
from services.semantic.analyzer import analyze_answer
from services.semantic.negation import WITHHOLD_CREDIT, contradiction_policy

FEEDBACK_VERSION = "baseline-v1"


def _analysis_request(request: FeedbackRequest) -> AnswerAnalysisRequest:
    """Same concept-merging step as in marking: the question's concepts plus every concept used in the rubric."""
    marking_req = request.marking_request
    expected = list(marking_req.expected_concepts or [])
    seen = {c.casefold() for c in expected}
    for criterion in marking_req.rubric.criteria:
        for c in (criterion.required_concepts or []):
            if c.casefold() not in seen:
                expected.append(c)
                seen.add(c.casefold())
        for level in criterion.scoring_levels:
            for c in (level.required_concepts or []):
                if c.casefold() not in seen:
                    expected.append(c)
                    seen.add(c.casefold())
    data = marking_req.model_dump(exclude={"rubric", "expected_concepts"})
    return AnswerAnalysisRequest(expected_concepts=expected or None, **data)


def _unique(values: list[str]) -> list[str]:
    """Remove duplicates while keeping the original order."""
    # Remove duplicates but keep the original order.
    return list(dict.fromkeys(values))


def _contradiction_warnings(contradicted: list[str], withheld: bool) -> list[str]:
    """One warning per possibly-denied concept; the wording says whether the active policy withheld credit."""
    credit = "No credit was given" if withheld else "Credit was not withheld"
    return [
        f"Possible contradiction: your answer appears to deny '{concept}'. {credit}; your lecturer will check."
        for concept in contradicted
    ]


def _criterion_feedback(
    criterion,
    result,
    analysis: AnswerAnalysisResponse,
    contradicted_names: set[str],
    withheld: bool,
    question_text: str | None,
) -> tuple[CriterionFeedback, str | None]:
    """Feedback for one criterion, plus the evidence warning (if any) that must also appear in the overall warnings."""
    # Sort this criterion's concepts into demonstrated / partial / missing / "needed only for a higher level".
    demonstrated, partial, missing, next_level = concept_status_lists(criterion, analysis, result.selected_level_id)
    # Concepts whose only mentions are negated are called out; under withhold_credit they are also in the missing list.
    contradicted = [c for c in (*demonstrated, *partial, *missing, *next_level) if c.casefold() in contradicted_names]
    strengths = build_strengths(demonstrated)
    # The "how to improve" text: uses the rubric level, the mark, the evidence and the question wording.
    suggestions = build_contextual_improvements(
        criterion=criterion,
        result=result,
        demonstrated=demonstrated,
        partial=partial,
        missing=missing,
        next_level=next_level,
        question_text=question_text,
    )
    criterion_warnings = list(result.warnings) + _contradiction_warnings(contradicted, withheld)
    evidence_message = evidence_warning(result)
    if evidence_message is not None:
        criterion_warnings.append(evidence_message)
    feedback = CriterionFeedback(
        criterion_id=result.criterion_id,
        criterion_description=result.criterion_description,
        max_marks=result.max_marks,
        selected_level_id=result.selected_level_id,
        selected_level_descriptor=result.rubric_descriptor,
        awarded_mark=result.awarded_mark,
        evidence_sentence_ids=result.evidence_sentence_ids,
        supporting_concepts=result.supporting_concepts,
        demonstrated_concepts=demonstrated,
        partial_concepts=partial,
        missing_concepts=missing,
        contradicted_concepts=contradicted,
        next_level_improvements=next_level,
        explanation=build_explanation(result, analysis),
        strengths=strengths,
        missing_or_partial_areas=build_missing_or_partial_areas(partial, missing),
        improvement_suggestions=suggestions,
        warnings=criterion_warnings,
    )
    return feedback, evidence_message


def build_feedback_from_results(
    marking: MarkingResponse,
    analysis: AnswerAnalysisResponse,
    rubric: Rubric,
    question_text: str | None = None,
) -> FeedbackResponse:
    """Turn the finished marking + analysis into the feedback object shown to the student and lecturer."""
    criteria_by_id = {
        criterion.criterion_id: criterion
        for criterion in rubric.criteria
    }
    criteria_feedback: list[CriterionFeedback] = []
    all_strengths: list[str] = []
    all_missing: list[str] = []
    all_suggestions: list[str] = []
    all_next_level: list[str] = []
    warnings = list(marking.warnings)

    # the wording must follow the active policy, not the concept list
    withheld = contradiction_policy() == WITHHOLD_CREDIT
    contradicted_names = {m.concept.casefold() for m in analysis.concept_matches if m.contradicted}
    for result in marking.criteria_results:
        feedback, evidence_message = _criterion_feedback(
            criteria_by_id[result.criterion_id], result, analysis, contradicted_names, withheld, question_text
        )
        criteria_feedback.append(feedback)
        if evidence_message is not None:
            warnings.append(evidence_message)
        all_strengths.extend(feedback.strengths)
        all_missing.extend(feedback.missing_concepts)
        all_suggestions.extend(feedback.improvement_suggestions)
        all_next_level.extend(feedback.next_level_improvements)

    # Whole-answer summary = the per-criterion lists merged without duplicates.
    all_missing = _unique(all_missing)
    all_suggestions = _unique(all_suggestions)
    all_next_level = _unique(all_next_level)
    overall_summary = (
        f"Function 2 proposed {marking.total_awarded_marks:g} of "
        f"{marking.total_possible_marks:g} marks across "
        f"{len(marking.criteria_results)} criterion(s)."
    )

    return FeedbackResponse(
        question_id=marking.question_id,
        criteria_feedback=criteria_feedback,
        overall_feedback=OverallFeedback(
            total_mark=marking.total_awarded_marks,
            total_possible=marking.total_possible_marks,
            percentage=marking.percentage,
            overall_summary=overall_summary,
            overall_strengths=_unique(all_strengths),
            overall_missing_concepts=all_missing,
            overall_next_level_improvements=all_next_level,
            overall_improvement_suggestions=all_suggestions,
        ),
        warnings=_unique(warnings),
        feedback_version=FEEDBACK_VERSION,
    )


def generate_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Generate traceable feedback from the existing Function 2 result.
    The baseline constructs feedback from structured upstream marking and concept evidence
    without an additional generative dependency.
    """
    # Used by the stand-alone /feedback/generate endpoint: re-mark and re-analyse, then build the feedback from them.
    marking = mark_answer(request.marking_request)
    analysis = analyze_answer(_analysis_request(request))
    return build_feedback_from_results(
        marking=marking,
        analysis=analysis,
        rubric=request.marking_request.rubric,
        question_text=request.marking_request.question_text,
    )
