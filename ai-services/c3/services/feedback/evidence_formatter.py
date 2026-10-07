from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.marking import CriterionMarkingResult, RubricCriterion


def concept_status_lists(
    criterion: RubricCriterion,
    analysis: AnswerAnalysisResponse,
    selected_level_id: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Classify only rubric-required concepts using existing Function 1 output."""
    matches = {match.concept.casefold(): match for match in analysis.concept_matches}
    
    selected_level = next((lvl for lvl in criterion.scoring_levels if lvl.level_id == selected_level_id), None)
    if selected_level is None:
        required_concepts = []
    else:
        required_concepts = selected_level.required_concepts or []
        
    higher_level_concepts = []
    if selected_level is not None:
        for level in criterion.scoring_levels:
            if level.mark > selected_level.mark:
                for concept in (level.required_concepts or []):
                    if concept not in required_concepts and concept not in higher_level_concepts:
                        higher_level_concepts.append(concept)
    
    demonstrated: list[str] = []
    partial: list[str] = []
    missing: list[str] = []
    next_level: list[str] = []

    for concept in required_concepts:
        match = matches.get(concept.casefold())
        if match is None or match.status == "not_demonstrated":
            missing.append(concept)
        elif match.status == "demonstrated":
            demonstrated.append(concept)
        elif match.status == "partial":
            partial.append(concept)
            
    for concept in higher_level_concepts:
        match = matches.get(concept.casefold())
        if match is None or match.status == "not_demonstrated":
            next_level.append(concept)

    return demonstrated, partial, missing, next_level


def evidence_warning(result: CriterionMarkingResult) -> str | None:
    if result.evidence_sentence_ids:
        return None
    return (
        f"No sentence-level evidence was available for criterion "
        f"{result.criterion_id}; the explanation is limited to the rubric result."
    )
