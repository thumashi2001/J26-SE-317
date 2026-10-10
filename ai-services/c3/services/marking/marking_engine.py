from app.schemas.analysis import AnswerAnalysisRequest
from app.schemas.marking import (
    CriterionMarkingResult,
    MarkingRequest,
    MarkingResponse,
)
from services.semantic.analyzer import analyze_answer
from services.marking.criterion_evaluator import evaluate_criterion
from services.marking.rubric_validator import validate_rubric


MARKING_VERSION = "baseline-v1"


def _analysis_request(request: MarkingRequest) -> AnswerAnalysisRequest:
    concepts: list[str] = list(request.expected_concepts or [])
    seen: set[str] = {c.casefold() for c in concepts}
    for criterion in request.rubric.criteria:
        for concept in criterion.required_concepts:
            if concept.casefold() not in seen:
                concepts.append(concept)
                seen.add(concept.casefold())
        for level in criterion.scoring_levels:
            for concept in level.required_concepts:
                if concept.casefold() not in seen:
                    concepts.append(concept)
                    seen.add(concept.casefold())

    dump = request.model_dump(exclude={"rubric", "expected_concepts"})
    dump["expected_concepts"] = concepts if concepts else None
    return AnswerAnalysisRequest.model_validate(dump)


def _overall_explanation(results: list[CriterionMarkingResult]) -> str:
    details = "; ".join(
        f"{result.criterion_id}={result.awarded_mark:g}/{result.max_marks:g}"
        for result in results
    )
    return (
        "The overall proposed mark is derived by summing the rubric-defined "
        f"criterion marks: {details}. It is a deterministic baseline proposal, "
        "not a claim of factual correctness or final lecturer judgment."
    )


def mark_answer(request: MarkingRequest) -> MarkingResponse:
    """Produce a rubric-controlled proposed mark from Function 1 evidence."""
    validate_rubric(request.rubric)
    analysis = analyze_answer(_analysis_request(request))
    criteria_results = [
        evaluate_criterion(criterion, analysis)
        for criterion in request.rubric.criteria
    ]
    total_awarded_marks = sum(result.awarded_mark for result in criteria_results)
    total_possible_marks = sum(result.max_marks for result in criteria_results)
    percentage = round(total_awarded_marks / total_possible_marks * 100, 2)
    warnings = list(analysis.warnings)
    warnings.extend(
        warning
        for result in criteria_results
        for warning in result.warnings
    )

    return MarkingResponse(
        question_id=request.question_id,
        criteria_results=criteria_results,
        total_awarded_marks=total_awarded_marks,
        total_possible_marks=total_possible_marks,
        percentage=percentage,
        overall_explanation=_overall_explanation(criteria_results),
        warnings=warnings,
        marking_version=MARKING_VERSION,
    )
