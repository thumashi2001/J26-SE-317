from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.marking import CriterionMarkingResult


def build_explanation(
    result: CriterionMarkingResult,
    analysis: AnswerAnalysisResponse,
) -> str:
    """
    Explain the existing Function 2 result using only traceable data.
    Function 3 does not independently generate unsupported evidence. Explanations are constructed 
    only from structured evidence and concept matches produced by the upstream analysis pipeline.
    """
    evidence_ids = ", ".join(str(value) for value in result.evidence_sentence_ids)
    concepts = ", ".join(result.supporting_concepts) or "none"
    if not result.evidence_sentence_ids:
        return (
            f"Criterion {result.criterion_id} received the proposed mark "
            f"{result.awarded_mark:g}/{result.max_marks:g} at rubric level "
            f"'{result.selected_level_id}'. No sentence-level evidence was "
            "available, so this explanation does not assert unsupported evidence."
        )

    return (
        f"Criterion {result.criterion_id} received the proposed mark "
        f"{result.awarded_mark:g}/{result.max_marks:g} at rubric level "
        f"'{result.selected_level_id}'. Supporting concepts: {concepts}. "
        f"Student evidence is referenced by sentence IDs: {evidence_ids}. "
        "This explanation reports the existing rubric result and does not create "
        "a new mark."
    )


def build_strengths(demonstrated_concepts: list[str]) -> list[str]:
    return [
        f"Demonstrated concept supported by the answer: {concept}."
        for concept in demonstrated_concepts
    ]


def build_missing_or_partial_areas(
    partial_concepts: list[str],
    missing_concepts: list[str],
) -> list[str]:
    areas = [
        f"Concept requires stronger or more complete evidence: {concept}."
        for concept in partial_concepts
    ]
    areas.extend(
        f"Required concept was not demonstrated by the available evidence: {concept}."
        for concept in missing_concepts
    )
    return areas


def build_improvement_suggestions(
    partial_concepts: list[str],
    missing_concepts: list[str],
    has_evidence: bool,
) -> list[str]:
    suggestions = [
        f"Explain the relevant aspect of '{concept}' more explicitly."
        for concept in partial_concepts
    ]
    suggestions.extend(
        f"Add answer evidence addressing '{concept}'."
        for concept in missing_concepts
    )
    if not has_evidence and not suggestions:
        suggestions.append(
            "Provide answer evidence that can be traced to the rubric requirements."
        )
    return suggestions
