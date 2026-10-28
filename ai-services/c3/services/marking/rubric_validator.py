"""Rubric sanity checks that run BEFORE any answer is marked.

SIMPLE ENGLISH
    A rubric written by a lecturer can contain mistakes (two criteria with the same id, a level worth more than the
    criterion, a rule that asks for 3 concepts when only 2 exist). Marking with such a rubric would give meaningless
    marks, so these checks stop the request and report every problem instead of silently "fixing" the rubric.
    This is input validation of the marking scheme, not model validation.
"""
from app.schemas.marking import Rubric


class RubricValidationError(ValueError):
    """Raised when a rubric cannot support deterministic evaluation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors  # the route turns this list into an HTTP 422 response
        super().__init__("; ".join(errors))


def validate_rubric(rubric: Rubric) -> None:
    """Validate cross-field rubric rules without silently repairing input."""
    errors: list[str] = []
    if not rubric.criteria:
        errors.append("rubric must contain at least one criterion")

    # --- checks per criterion -----------------------------------------------------------------------------------------
    criterion_ids: set[str] = set()
    for criterion in rubric.criteria:
        if criterion.criterion_id in criterion_ids:
            errors.append(f"duplicate criterion_id: {criterion.criterion_id}")
        criterion_ids.add(criterion.criterion_id)

        if not criterion.description.strip():
            errors.append(f"criterion {criterion.criterion_id} has a blank description")
        if criterion.max_marks <= 0:
            errors.append(f"criterion {criterion.criterion_id} max_marks must be greater than zero")
        if any(not concept.strip() for concept in criterion.required_concepts):
            errors.append(f"criterion {criterion.criterion_id} has a blank required concept")
        if not criterion.scoring_levels:
            errors.append(f"criterion {criterion.criterion_id} must contain scoring levels")

        # --- checks per scoring level ---------------------------------------------------------------------------------
        level_ids: set[str] = set()
        for level in criterion.scoring_levels:
            if level.level_id in level_ids:
                errors.append(
                    f"duplicate level_id {level.level_id} in criterion {criterion.criterion_id}"
                )
            level_ids.add(level.level_id)

            if level.mark < 0:
                errors.append(f"level {level.level_id} cannot have a negative mark")
            if level.mark > criterion.max_marks:
                errors.append(
                    f"level {level.level_id} mark exceeds criterion {criterion.criterion_id} max_marks"
                )
            if any(not concept.strip() for concept in level.required_concepts):
                errors.append(f"level {level.level_id} has a blank required concept")
            if any(not requirement.strip() for requirement in level.evidence_requirements):
                errors.append(f"level {level.level_id} has an invalid evidence requirement")
            # The evidence rule ("at least N concepts") must be satisfiable with the concepts that actually exist.
            if level.evidence_rule is not None:
                effective_concepts = {c.casefold() for c in criterion.required_concepts} | {
                    c.casefold() for c in level.required_concepts
                }
                required_concept_count = len(effective_concepts)
                if required_concept_count == 0:
                    errors.append(
                        f"level {level.level_id} evidence_rule requires required_concepts"
                    )
                if (
                    level.evidence_rule.minimum_demonstrated
                    > required_concept_count
                ):
                    errors.append(
                        f"level {level.level_id} minimum_demonstrated exceeds required concepts"
                    )
                if level.evidence_rule.minimum_partial > required_concept_count:
                    errors.append(
                        f"level {level.level_id} minimum_partial exceeds required concepts"
                    )
                if (
                    level.evidence_rule.minimum_demonstrated
                    + level.evidence_rule.minimum_partial
                    > required_concept_count
                ):
                    errors.append(
                        f"level {level.level_id} combined evidence thresholds exceed required concepts"
                    )

    # Report all problems together so the lecturer can fix them in one go.
    if errors:
        raise RubricValidationError(errors)
