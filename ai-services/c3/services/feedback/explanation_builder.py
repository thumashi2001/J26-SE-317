"""Rule-based text builders for the explanation and the "how to improve" feedback.

IMPORTANT FOR THE VIVA
    The wording here is produced by Python string formatting from the actual marking result (the mark, the rubric
    level, the evidence sentences, the concept lists). There is no language model. The text is "template based but
    grounded": the templates are filled with real values (concept names, marks, level labels), and no function in this
    file can change a mark.
    build_improvement_suggestions() is the OLD generic version (kept for tests); build_contextual_improvements() is the
    version the live pipeline uses.
"""
from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.marking import CriterionMarkingResult


def build_explanation(
    result: CriterionMarkingResult,
    analysis: AnswerAnalysisResponse,
) -> str:
    """
    Explain the existing Function 2 result using only traceable data.
    The baseline constructs feedback from structured upstream marking and concept evidence
    without an additional generative dependency.
    """
    evidence_ids = ", ".join(str(value) for value in result.evidence_sentence_ids)
    concepts = ", ".join(result.supporting_concepts) or "none"
    # No matching sentence: say so plainly instead of inventing evidence.
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
    """One 'strength' line per concept that was found in the answer."""
    return [
        f"Demonstrated concept supported by the answer: {concept}."
        for concept in demonstrated_concepts
    ]


def build_missing_or_partial_areas(
    partial_concepts: list[str],
    missing_concepts: list[str],
) -> list[str]:
    """Lines describing concepts that are only partly covered, then concepts that are missing."""
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
    """OLD generic suggestions (kept so existing tests still describe the earlier behaviour)."""
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


# ---------------------------------------------------------------------------------------------------------------------
# Criterion-specific improvement guidance (deterministic, rubric-grounded; it never changes a mark).
# ---------------------------------------------------------------------------------------------------------------------
# Shown at the end of the advice so the student is never told the system "understood" their answer.
LEXICAL_NOTE = (
    "These suggestions come from matching the rubric's concepts in your wording, not from a check that your "
    "explanation is correct, so a correct answer written in different words may not be matched."
)

# If the question/rubric contains one of these words, software-architecture hints are allowed; otherwise they are not.
_ARCHITECTURE_WORDS = (
    "architect", "component", "connector", "module", "layer", "microservice", "coupling", "cohesion",
    "subsystem", "interface", "design pattern",
)
_EXAMPLE_HINT = (
    "Add one concrete example (for instance a small system with a user interface, a service layer and a database) "
    "to show how the parts work together."
)


def _is_architecture_context(*texts: str | None) -> bool:
    """True when the question, criterion or concepts look like a software-architecture topic."""
    joined = " ".join(t for t in texts if t).casefold()
    return any(word in joined for word in _ARCHITECTURE_WORDS)


def _concept_hint(concept: str, architecture: bool) -> str:
    """One actionable sentence for a concept. Subject-specific wording only inside an architecture context."""
    low = concept.casefold()
    if architecture:
        if "structure" in low:
            return f"For '{concept}': describe the overall structure of the system, meaning its main parts and how they are organised."
        if "component" in low:
            return f"For '{concept}': name the main components and state what each one is responsible for."
        if any(k in low for k in ("relationship", "interaction", "communicat", "connect", "depend")):
            return f"For '{concept}': explain how the components communicate with or depend on each other."
    # Any other subject (or an unrecognised concept) gets neutral wording.
    return f"For '{concept}': explain it in your own words and show how it applies to this question."


def _quoted(items: list[str]) -> str:
    # ['a', 'b'] -> "'a', 'b'"
    return ", ".join(f"'{item}'" for item in items)


def build_contextual_improvements(
    *,
    criterion,
    result,
    demonstrated: list[str],
    partial: list[str],
    missing: list[str],
    next_level: list[str],
    question_text: str | None = None,
) -> list[str]:
    """Improvement guidance for one criterion from its rubric level, mark, evidence and concept lists.

    Grounded only in data the system holds: the criterion, the selected and next scoring levels (labels and marks),
    the concept statuses and whether any answer sentence was matched. No answer text is quoted, nothing is asserted
    about what the student misunderstood when no evidence exists, and the guidance never contradicts the mark.
    """
    awarded = float(result.awarded_mark)
    maximum = float(result.max_marks)
    levels = list(getattr(criterion, "scoring_levels", []) or [])
    # The next rung up the ladder = the lowest level that is worth more than the current mark.
    higher = sorted((lvl for lvl in levels if float(lvl.mark) > awarded), key=lambda lvl: float(lvl.mark))
    next_lvl = higher[0] if higher else None
    needed = list(dict.fromkeys([*partial, *missing, *next_level]))
    all_rubric_concepts = list(criterion.required_concepts or []) + [c for lvl in levels for c in (lvl.required_concepts or [])]
    architecture = _is_architecture_context(question_text, criterion.description, *all_rubric_concepts)
    has_evidence = bool(result.evidence_sentence_ids)

    # Incomplete rubric metadata: say so instead of inventing specifics.
    if not all_rubric_concepts and not (demonstrated or partial or missing or next_level):
        if next_lvl is None or awarded >= maximum:
            return [f"This criterion is at its top rubric level ({awarded:g}/{maximum:g}); no further improvement is needed for it."]
        return [
            f"The rubric for this criterion ('{criterion.description}') lists no expected concepts, so specific guidance cannot "
            "be generated. Re-read the question and this criterion, and make sure every part is addressed with a clear explanation.",
        ]

    # Top level reached (or nothing left to gain): advanced guidance, consistent with the mark.
    if next_lvl is None or awarded >= maximum:
        out = [f"This criterion is at its top rubric level ({awarded:g}/{maximum:g}); keep this standard."]
        if demonstrated:
            out.append(f"The concepts found in your wording were {_quoted(demonstrated)}.")
        if architecture:
            out.append("To go further, justify your design choices (for example why the parts are separated this way) and mention a trade-off.")
        else:
            out.append("To go further, support your points with a specific example and say why it matters.")
        return out

    # Normal case: tell the student where they are, what the next level is, and what to cover to reach it.
    out: list[str] = []
    target = f"'{next_lvl.label}' ({float(next_lvl.mark):g}/{maximum:g})"
    wanted = _quoted(needed) if needed else "each part of the criterion"
    if not has_evidence:
        # Zero evidence: do NOT pretend to know what the student misunderstood.
        out.append(
            "No sentence in your answer matched the concepts for this criterion, so the system cannot tell what you did or did not "
            f"understand. It currently scores {awarded:g}/{maximum:g}; to reach {target}, write about {wanted}."
        )
    else:
        found = f"Your wording matched {_quoted(demonstrated)}. " if demonstrated else ""
        out.append(f"{found}This criterion scores {awarded:g}/{maximum:g}; to reach {target}, cover {wanted}.")
    for concept in partial:
        out.append(f"For '{concept}': it is only partly covered; state it more completely and explain how it applies to the question.")
    for concept in [c for c in needed if c not in partial]:
        out.append(_concept_hint(concept, architecture))
    if architecture:
        out.append(_EXAMPLE_HINT)
    out.append(LEXICAL_NOTE)
    return list(dict.fromkeys(out))
