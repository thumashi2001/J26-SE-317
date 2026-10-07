from app.schemas.analysis import AnswerAnalysisRequest
from app.schemas.feedback import (
    CriterionFeedback,
    FeedbackRequest,
    FeedbackResponse,
    OverallFeedback,
)
from services.feedback.evidence_formatter import (
    concept_status_lists,
    evidence_warning,
)
from services.feedback.explanation_builder import (
    build_explanation,
    build_improvement_suggestions,
    build_missing_or_partial_areas,
    build_strengths,
)
from services.marking.marking_engine import mark_answer
from services.semantic.analyzer import analyze_answer


FEEDBACK_VERSION = "baseline-v1"


def _analysis_request(request: FeedbackRequest) -> AnswerAnalysisRequest:
    return AnswerAnalysisRequest.model_validate(
        request.marking_request.model_dump(exclude={"rubric"})
    )


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def generate_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """
    Generate traceable feedback from the existing Function 2 result.
    Function 3 does not independently generate unsupported evidence. Explanations are constructed
    only from structured evidence and concept matches produced by the upstream analysis pipeline.
    """
    marking = mark_answer(request.marking_request)
    analysis = analyze_answer(_analysis_request(request))
    criteria_by_id = {
        criterion.criterion_id: criterion
        for criterion in request.marking_request.rubric.criteria
    }
    criteria_feedback: list[CriterionFeedback] = []
    all_strengths: list[str] = []
    all_missing: list[str] = []
    all_suggestions: list[str] = []
    all_next_level: list[str] = []
    warnings = list(marking.warnings)

    for result in marking.criteria_results:
        criterion = criteria_by_id[result.criterion_id]
        demonstrated, partial, missing, next_level = concept_status_lists(
            criterion, analysis, result.selected_level_id
        )
        strengths = build_strengths(demonstrated)
        areas = build_missing_or_partial_areas(partial, missing)
        suggestions = build_improvement_suggestions(
            partial,
            missing,
            bool(result.evidence_sentence_ids),
        )
        criterion_warnings = list(result.warnings)
        evidence_warning_message = evidence_warning(result)
        if evidence_warning_message is not None:
            criterion_warnings.append(evidence_warning_message)
            warnings.append(evidence_warning_message)

        criteria_feedback.append(
            CriterionFeedback(
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
                next_level_improvements=next_level,
                explanation=build_explanation(result, analysis),
                strengths=strengths,
                missing_or_partial_areas=areas,
                improvement_suggestions=suggestions,
                warnings=criterion_warnings,
            )
        )
        all_strengths.extend(strengths)
        all_missing.extend(missing)
        all_suggestions.extend(suggestions)
        all_next_level.extend(next_level)

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
