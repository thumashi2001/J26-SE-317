"""THE FUNCTION THAT AWARDS THE MARK: evaluate_criterion() at the bottom of this file.

SIMPLE ENGLISH
    A rubric criterion is a ladder of levels, each with a fixed mark, for example
        L4 "Proficient" = 4 marks  (needs all 3 concepts)
        L2 "Developing" = 2 marks  (needs at least 1 concept)
        L0 "Unsatisfactory" = 0 marks (no requirement)
    The engine starts at the TOP rung and walks down. The first rung whose requirements are satisfied by the
    evidence found in the student's answer is the level awarded, and the student gets exactly that level's mark.

HOW "EVIDENCE" IS DECIDED
    Evidence comes from Function 1 (services/semantic/analyzer.py): for every concept the analyzer says
    demonstrated / partial / not_demonstrated using TOKEN OVERLAP (shared words), never a trained model.
    So the awarded mark is: fixed rubric rules + word matching. There is no machine-learning model, embedding, LLM or
    percentage formula in this file.

WORKED EXAMPLE (rubric above, answer = "The system is made of components.")
    concept statuses: components = demonstrated, the other two = not_demonstrated
    try L4: needs 3 demonstrated -> only 1 found -> not supported
    try L2: needs 1 demonstrated -> 1 found       -> supported  => awarded mark = 2
"""
from dataclasses import dataclass

from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.marking import CriterionMarkingResult, RubricCriterion, ScoringLevel
from services.preprocessing.text_normalizer import tokenize
from services.semantic.baseline import token_overlap_score


@dataclass(frozen=True)
class LevelEvidence:
    """Verdict for ONE rubric level: is it supported by the answer, and what evidence backs that."""

    supported: bool           # True = the answer meets this level's requirements
    concepts: list[str]       # concepts that were found and count towards this level
    sentence_ids: list[int]   # answer sentences that contain that evidence
    reasons: list[str]        # why the level was NOT supported (empty when supported)


def _concept_matches(analysis: AnswerAnalysisResponse) -> dict[str, object]:
    """Look-up table from lowercase concept name to its Function 1 match."""
    # Look-up table: concept name (lowercase) -> its ConceptMatch from Function 1.
    return {match.concept.casefold(): match for match in analysis.concept_matches}


def _effective_concepts(criterion: RubricCriterion, level: ScoringLevel) -> list[str]:
    """Concepts a level really requires = the criterion's concepts plus the level's own (no duplicates)."""
    concepts: list[str] = []
    seen: set[str] = set()
    for c in criterion.required_concepts:
        if c.casefold() not in seen:
            concepts.append(c)
            seen.add(c.casefold())
    for c in level.required_concepts:
        if c.casefold() not in seen:
            concepts.append(c)
            seen.add(c.casefold())
    return concepts


def _is_safety_net_level(level: ScoringLevel) -> bool:
    """The lowest "zero marks" level with no requirement of any kind: it is always supported."""
    return (
        level.mark == 0.0
        and level.evidence_rule is None
        and not level.required_concepts
        and not level.evidence_requirements
    )


def _all_demonstrated_evidence(
    required: list[str], matches: dict[str, object]
) -> tuple[list[str], set[int], list[str]]:
    """CASE 2 - no explicit counting rule: EVERY required concept must be fully demonstrated."""
    concepts: list[str] = []
    sentence_ids: set[int] = set()
    reasons: list[str] = []
    for required_concept in required:
        match = matches.get(required_concept.casefold())
        if match is None:
            reasons.append(f"required concept not supplied by analysis: {required_concept}")
            continue
        if match.status != "demonstrated":
            reasons.append(f"required concept is not fully demonstrated by lexical evidence: {required_concept}")
            continue
        concepts.append(required_concept)
        sentence_ids.update(match.evidence_sentence_ids)
    return concepts, sentence_ids, reasons


def _rule_counted_evidence(
    level: ScoringLevel, required: list[str], matches: dict[str, object]
) -> tuple[list[str], set[int], list[str]]:
    """CASE 3 - an explicit rule ("at least N demonstrated / M partial"): count the concepts, compare with the rule."""
    concepts: list[str] = []
    sentence_ids: set[int] = set()
    reasons: list[str] = []
    demonstrated_count = 0
    partial_count = 0
    for required_concept in required:
        match = matches.get(required_concept.casefold())
        if match is None:
            reasons.append(f"required concept not supplied by analysis: {required_concept}")
            continue
        if match.status == "demonstrated":
            demonstrated_count += 1
            concepts.append(required_concept)
            sentence_ids.update(match.evidence_sentence_ids)
        elif match.status == "partial":
            partial_count += 1
            # Partial concepts only help when the rubric explicitly allows partial credit.
            if level.evidence_rule.allow_partial:
                concepts.append(required_concept)
                sentence_ids.update(match.evidence_sentence_ids)

    if demonstrated_count < level.evidence_rule.minimum_demonstrated:
        reasons.append("demonstrated concept count is below the evidence-rule minimum")
    if partial_count < level.evidence_rule.minimum_partial:
        reasons.append("partial concept count is below the evidence-rule minimum")
    return concepts, sentence_ids, reasons


def _requirement_evidence(level: ScoringLevel, analysis: AnswerAnalysisResponse) -> tuple[set[int], list[str]]:
    """Optional extra requirements (phrases the level wants): each needs at least one word shared with the answer."""
    sentence_ids: set[int] = set()
    reasons: list[str] = []
    answer_tokens = tokenize(analysis.normalized_answer)
    for requirement in level.evidence_requirements:
        if token_overlap_score(requirement, answer_tokens) == 0.0:
            reasons.append(f"evidence requirement not supported by lexical overlap: {requirement}")
            continue
        sentence_ids.update(
            sentence_id
            for sentence_id, sentence in enumerate(analysis.sentences, start=1)
            if token_overlap_score(requirement, tokenize(sentence.text)) > 0.0
        )
    return sentence_ids, reasons


def _level_evidence(
    criterion: RubricCriterion,
    level: ScoringLevel,
    analysis: AnswerAnalysisResponse,
) -> LevelEvidence:
    """Decide whether the answer satisfies ONE level (this is where the rubric rules are applied)."""
    matches = _concept_matches(analysis)
    effective_required_concepts = _effective_concepts(criterion, level)

    # CASE 1 - the lowest "zero marks" level has no requirement, so it is always supported (it is the safety net).
    if _is_safety_net_level(level):
        concepts: list[str] = []
        sentence_ids: set[int] = set()
        for required_concept in effective_required_concepts:
            match = matches.get(required_concept.casefold())
            if match and match.status == "demonstrated":
                concepts.append(required_concept)
                sentence_ids.update(match.evidence_sentence_ids)
        return LevelEvidence(supported=True, concepts=concepts, sentence_ids=sorted(sentence_ids), reasons=[])

    if level.evidence_rule is None:
        concepts, sentence_ids, reasons = _all_demonstrated_evidence(effective_required_concepts, matches)
    else:
        concepts, sentence_ids, reasons = _rule_counted_evidence(level, effective_required_concepts, matches)

    requirement_ids, requirement_reasons = _requirement_evidence(level, analysis)
    sentence_ids.update(requirement_ids)
    reasons.extend(requirement_reasons)

    has_requirements = bool(
        effective_required_concepts
        or level.evidence_requirements
        or level.evidence_rule
    )
    # A level is supported only if it asked for something AND nothing was missing (no reasons collected).
    supported = has_requirements and not reasons
    if level.mark == 0.0 and not has_requirements:
        supported = True

    return LevelEvidence(
        supported=supported,
        concepts=concepts,
        sentence_ids=sorted(sentence_ids),
        reasons=reasons,
    )


def _explanation(
    criterion: RubricCriterion,
    level: ScoringLevel,
    evidence: LevelEvidence,
    warnings: list[str],
) -> str:
    """One-sentence explanation stored with the result (the richer 'how to improve' text is built in
        services/feedback)."""
    if warnings:
        return (
            f"Selected rubric level '{level.label}' ({level.mark:g} marks) for "
            f"criterion {criterion.criterion_id}. No higher scoring level was "
            "supported by the available deterministic lexical evidence."
        )

    evidence_text = ", ".join(str(value) for value in evidence.sentence_ids) or "none"
    concepts_text = ", ".join(evidence.concepts) or "none"
    return (
        f"Selected rubric level '{level.label}' ({level.mark:g} marks) for "
        f"criterion {criterion.criterion_id}. Supporting concepts: {concepts_text}. "
        f"Evidence sentence IDs: {evidence_text}. The proposed result is based on "
        "the rubric requirements and deterministic lexical evidence."
    )


def evaluate_criterion(
    criterion: RubricCriterion,
    analysis: AnswerAnalysisResponse,
) -> CriterionMarkingResult:
    """Select the highest rubric level supported by Function 1 evidence.

    This evaluator never converts a percentage of concepts into marks. Marks
    come only from the selected scoring level supplied by the rubric.
    """
    # Order the levels from the highest mark down (ties keep the rubric's own order).
    ordered_levels = sorted(
        enumerate(criterion.scoring_levels),
        key=lambda item: (-item[1].mark, item[0]),
    )
    # Walk down the ladder; the first supported level with a positive mark wins and its mark is awarded.
    for _, level in ordered_levels:
        if level.mark <= 0.0:
            continue
        evidence = _level_evidence(criterion, level, analysis)
        if evidence.supported:
            return _result_for_level(criterion, level, evidence, [])

    # Nothing positive was supported: fall back to the lowest level (usually 0 marks) and say so in a warning.
    lowest_level = min(
        criterion.scoring_levels,
        key=lambda level: level.mark,
    )
    warnings = [
        f"No positive scoring level was supported for criterion {criterion.criterion_id}; "
        f"selected lowest rubric level '{lowest_level.level_id}'."
    ]
    evidence = _level_evidence(criterion, lowest_level, analysis)
    return _result_for_level(criterion, lowest_level, evidence, warnings)


def _result_for_level(
    criterion: RubricCriterion,
    level: ScoringLevel,
    evidence: LevelEvidence,
    warnings: list[str],
) -> CriterionMarkingResult:
    """Package the chosen level as the criterion's result. awarded_mark is simply the level's rubric mark."""
    return CriterionMarkingResult(
        criterion_id=criterion.criterion_id,
        criterion_description=criterion.description,
        selected_level_id=level.level_id,
        selected_level_label=level.label,
        rubric_descriptor=level.descriptor,
        awarded_mark=level.mark,
        max_marks=criterion.max_marks,
        evidence_sentence_ids=evidence.sentence_ids,
        supporting_concepts=evidence.concepts,
        explanation=_explanation(criterion, level, evidence, warnings),
        warnings=warnings,
    )
