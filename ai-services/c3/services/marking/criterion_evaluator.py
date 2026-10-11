from dataclasses import dataclass

from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.marking import CriterionMarkingResult, RubricCriterion, ScoringLevel
from services.semantic.baseline import token_overlap_score
from services.preprocessing.text_normalizer import tokenize


@dataclass(frozen=True)
class LevelEvidence:
    supported: bool
    concepts: list[str]
    sentence_ids: list[int]
    reasons: list[str]


def _concept_matches(analysis: AnswerAnalysisResponse) -> dict[str, object]:
    return {match.concept.casefold(): match for match in analysis.concept_matches}


def _effective_concepts(criterion: RubricCriterion, level: ScoringLevel) -> list[str]:
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


def _level_evidence(
    criterion: RubricCriterion,
    level: ScoringLevel,
    analysis: AnswerAnalysisResponse,
) -> LevelEvidence:
    matches = _concept_matches(analysis)
    effective_required_concepts = _effective_concepts(criterion, level)
    concepts: list[str] = []
    sentence_ids: set[int] = set()
    reasons: list[str] = []

    if level.mark == 0.0 and level.evidence_rule is None and not level.required_concepts and not level.evidence_requirements:
        for required_concept in effective_required_concepts:
            match = matches.get(required_concept.casefold())
            if match and match.status == "demonstrated":
                concepts.append(required_concept)
                sentence_ids.update(match.evidence_sentence_ids)
        return LevelEvidence(
            supported=True,
            concepts=concepts,
            sentence_ids=sorted(sentence_ids),
            reasons=[],
        )

    if level.evidence_rule is None:
        for required_concept in effective_required_concepts:
            match = matches.get(required_concept.casefold())
            if match is None:
                reasons.append(
                    f"required concept not supplied by analysis: {required_concept}"
                )
                continue
            if match.status != "demonstrated":
                reasons.append(
                    f"required concept is not fully demonstrated by lexical evidence: {required_concept}"
                )
                continue
            concepts.append(required_concept)
            sentence_ids.update(match.evidence_sentence_ids)
    else:
        demonstrated_count = 0
        partial_count = 0
        for required_concept in effective_required_concepts:
            match = matches.get(required_concept.casefold())
            if match is None:
                reasons.append(
                    f"required concept not supplied by analysis: {required_concept}"
                )
                continue
            if match.status == "demonstrated":
                demonstrated_count += 1
                concepts.append(required_concept)
                sentence_ids.update(match.evidence_sentence_ids)
            elif match.status == "partial":
                partial_count += 1
                if level.evidence_rule.allow_partial:
                    concepts.append(required_concept)
                    sentence_ids.update(match.evidence_sentence_ids)

        if demonstrated_count < level.evidence_rule.minimum_demonstrated:
            reasons.append(
                "demonstrated concept count is below the evidence-rule minimum"
            )
        if partial_count < level.evidence_rule.minimum_partial:
            reasons.append(
                "partial concept count is below the evidence-rule minimum"
            )

    answer_tokens = tokenize(analysis.normalized_answer)
    for requirement in level.evidence_requirements:
        if token_overlap_score(requirement, answer_tokens) == 0.0:
            reasons.append(f"evidence requirement not supported by lexical overlap: {requirement}")
            continue
        requirement_sentence_ids = [
            sentence_id
            for sentence_id, sentence in enumerate(analysis.sentences, start=1)
            if token_overlap_score(requirement, tokenize(sentence.text)) > 0.0
        ]
        sentence_ids.update(requirement_sentence_ids)

    has_requirements = bool(
        effective_required_concepts
        or level.evidence_requirements
        or level.evidence_rule
    )
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
    ordered_levels = sorted(
        enumerate(criterion.scoring_levels),
        key=lambda item: (-item[1].mark, item[0]),
    )
    for _, level in ordered_levels:
        if level.mark <= 0.0:
            continue
        evidence = _level_evidence(criterion, level, analysis)
        if evidence.supported:
            return _result_for_level(criterion, level, evidence, [])

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
