from app.schemas.marking import Rubric


class RubricValidationError(ValueError):
    """Raised when a rubric cannot support deterministic evaluation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_rubric(rubric: Rubric) -> None:
    """Validate cross-field rubric rules without silently repairing input."""
    errors: list[str] = []
    if not rubric.criteria:
        errors.append("rubric must contain at least one criterion")

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
            if level.evidence_rule is not None:
                effective_concepts = {c.casefold() for c in criterion.required_concepts} | {c.casefold() for c in level.required_concepts}
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

    if errors:
        raise RubricValidationError(errors)
