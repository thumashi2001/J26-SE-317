"""Sorts a criterion's concepts into four lists used by the feedback text.

SIMPLE ENGLISH
    For the level the student reached, which concepts did they show (demonstrated), partly show (partial) or not show
    (missing)? And which concepts are only asked for by a HIGHER level (next_level), i.e. what to learn to climb up?
    The status of each concept comes from Function 1 (word overlap); this module only groups them.
"""
from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.marking import CriterionMarkingResult, RubricCriterion


def concept_status_lists(
    criterion: RubricCriterion,
    analysis: AnswerAnalysisResponse,
    selected_level_id: str,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Classify concepts for a criterion and selected scoring level.
    Uses Function 1 concept match outputs and respects scoring level hierarchy:
    - Concepts required by the selected level (or criterion-level required concepts)
      are classified into demonstrated, partial, or missing.
    - Concepts required only by higher scoring levels are classified into next_level.
    """
    # Look-up: concept name (lowercase) -> Function 1 status.
    matches = {match.concept.casefold(): match for match in analysis.concept_matches}

    selected_level = next(
        (lvl for lvl in criterion.scoring_levels if lvl.level_id == selected_level_id),
        None,
    )
    current_concepts, higher_exclusive_concepts = _split_by_level(criterion, selected_level)
    return _classify(current_concepts, higher_exclusive_concepts, matches)


def _split_by_level(criterion: RubricCriterion, selected_level) -> tuple[list[str], list[str]]:
    """Split the criterion's concepts into (required at the reached level, required only by a higher level)."""
    # 1. Determine higher levels (levels with mark > selected_level.mark)
    higher_levels = [
        lvl
        for lvl in criterion.scoring_levels
        if selected_level is not None and lvl.mark > selected_level.mark
    ]

    # 2. Identify concepts explicitly required ONLY by higher scoring levels
    selected_level_reqs: list[str] = (
        list(selected_level.required_concepts or []) if selected_level else []
    )
    selected_seen = {c.casefold() for c in selected_level_reqs}

    higher_exclusive_concepts: list[str] = []
    higher_seen: set[str] = set()
    for h_lvl in higher_levels:
        for c in (h_lvl.required_concepts or []):
            if c.casefold() not in selected_seen and c.casefold() not in higher_seen:
                higher_exclusive_concepts.append(c)
                higher_seen.add(c.casefold())

    # 3. Determine current required concepts:
    # Start with selected level required concepts
    current_concepts: list[str] = []
    current_seen: set[str] = set()

    for c in selected_level_reqs:
        if c.casefold() not in current_seen:
            current_concepts.append(c)
            current_seen.add(c.casefold())

    # Include criterion.required_concepts:
    # Deduplicate against selected level concepts.
    # Exclude if the concept is exclusively required by a higher scoring level.
    for c in (criterion.required_concepts or []):
        if c.casefold() not in current_seen:
            if c.casefold() in higher_seen:
                continue
            # When the student is on the zero-mark level, the criterion's concepts belong to the NEXT level up,
            # not to what the student is "missing" at their current level.
            if selected_level is not None and selected_level.mark == 0.0 and higher_levels:
                if c.casefold() not in higher_seen:
                    higher_exclusive_concepts.append(c)
                    higher_seen.add(c.casefold())
                continue
            current_concepts.append(c)
            current_seen.add(c.casefold())
    return current_concepts, higher_exclusive_concepts


def _classify(current_concepts: list[str], higher_exclusive_concepts: list[str], matches: dict) -> tuple[
        list[str], list[str], list[str], list[str]]:
    """Group the concepts by the Function 1 status of each: (demonstrated, partial, missing, next_level)."""
    # 4. Classify current concepts into demonstrated, partial, missing
    demonstrated: list[str] = []
    partial: list[str] = []
    missing: list[str] = []
    next_level: list[str] = []

    for concept in current_concepts:
        match = matches.get(concept.casefold())
        if match is None or match.status == "not_demonstrated":
            missing.append(concept)
        elif match.status == "demonstrated":
            demonstrated.append(concept)
        elif match.status == "partial":
            partial.append(concept)

    # 5. Classify higher-level concepts:
    # not found / partly found -> still to learn (next_level); fully found -> already a strength.
    for concept in higher_exclusive_concepts:
        match = matches.get(concept.casefold())
        if match is None or match.status == "not_demonstrated":
            if concept not in next_level:
                next_level.append(concept)
        elif match.status == "partial":
            if concept not in next_level:
                next_level.append(concept)
        elif match.status == "demonstrated":
            if concept not in demonstrated:
                demonstrated.append(concept)

    return demonstrated, partial, missing, next_level


def evidence_warning(result: CriterionMarkingResult) -> str | None:
    """A warning when a criterion has no matching sentence at all (so the explanation cannot point at evidence)."""
    if result.evidence_sentence_ids:
        return None
    return (
        f"No sentence-level evidence was available for criterion "
        f"{result.criterion_id}; the explanation is limited to the rubric result."
    )
