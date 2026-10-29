"""Function 1: analyse the student's answer (the evidence source for everything that follows).

SIMPLE ENGLISH
    For every concept the rubric cares about (e.g. "components") this module asks: do the concept's words appear in
    the answer? and in which sentences? The result is a status per concept:
        demonstrated      all of the concept's words appear in the answer      (overlap = 1.0)
        partial           some, but not all, of the words appear               (0 < overlap < 1)
        not_demonstrated  none of the words appear                             (overlap = 0)
    This is plain word matching ("lexical" analysis). On its own it does not understand meaning, so a correct answer
    written in different words (a paraphrase) is reported as not_demonstrated. With C3_SEMANTIC_MATCH=local an optional
    sentence-embedding layer (services/semantic/semantic_matcher.py) upgrades such concepts and flags them "semantic".
        These statuses feed the marking engine.
"""
from app.schemas.analysis import (
    AnswerAnalysisRequest,
    AnswerAnalysisResponse,
    ConceptMatch,
    SentenceAnalysis,
)
from services.preprocessing.text_normalizer import process_text, tokenize
from services.semantic.baseline import lexical_cosine_similarity, token_overlap_score
from services.semantic.keywords import extract_keywords
from services.semantic.negation import WARN_ONLY, contradiction_policy, sentence_mentions, sentence_negates
from services.semantic.relevance import check_relevance
from services.semantic.semantic_matcher import get_matcher, semantic_threshold

ANALYSIS_VERSION = "baseline-v1"
CONTRADICTION_CHECK = "negation-cue-v1"  # recorded on every analysis so stored results show which rule produced them
SEMANTIC_ANALYSIS_VERSION = "semantic-v1"  # used only when the optional semantic layer actually ran


def _concept_status(overlap_score: float) -> str:
    """The runtime threshold: exactly 1.0 = demonstrated, anything above 0 = partial, 0 = not demonstrated."""
    if overlap_score == 1.0:
        return "demonstrated"
    if overlap_score > 0.0:
        return "partial"
    return "not_demonstrated"


def _match_concepts(concepts: list[str], sentences: list[str], answer_tokens: list[str]) -> list[ConceptMatch]:
    """For each concept: overall overlap with the whole answer, and which sentences contain any of its words."""
    matches: list[ConceptMatch] = []
    for concept in concepts:
        overlap_score = token_overlap_score(concept, answer_tokens)
        # Sentence numbers (starting at 1) that share at least one word with the concept = the "evidence".
        evidence_sentence_ids = [
            sentence_id
            for sentence_id, sentence in enumerate(sentences, start=1)
            if token_overlap_score(concept, tokenize(sentence)) > 0.0
        ]
        matches.append(
            ConceptMatch(
                concept=concept,
                status=_concept_status(overlap_score),
                overlap_score=overlap_score,
                evidence_sentence_ids=evidence_sentence_ids,
            )
        )
    return matches


def _flag_contradictions(matches: list[ConceptMatch], sentences: list[str]) -> list[str]:
    """Mark concepts whose only mentions are negated ("... does not hide ..."); return lecturer-facing warnings.

    Every sentence that contains all of a concept's words is either affirming it or negating it (negation cue nearby).
      all such sentences negate  -> contradicted: a flag and a lecturer warning are added. By DEFAULT (warn_only) the
                                    status, and so the mark, are untouched. With C3_CONTRADICTION_POLICY=withhold_credit
                                    the status becomes not_demonstrated, so it earns no credit anywhere
      some affirm, some negate   -> conflicting: status is left alone, the lecturer is warned
    This is a possible contradiction by wording, not a meaning check; a correct negated sentence is flagged too.
    """
    warnings: list[str] = []
    warn_only = contradiction_policy() == WARN_ONLY
    for match in matches:
        mentioning = [i for i, s in enumerate(sentences, start=1) if sentence_mentions(match.concept, s)]
        negated = [i for i in mentioning if sentence_negates(match.concept, sentences[i - 1])]
        if not negated:
            continue
        match.negated_sentence_ids = negated
        if len(negated) == len(mentioning):
            match.contradicted = True
            if warn_only:
                warnings.append(
                    f"Possible contradiction: the answer negates '{match.concept}' (sentence {negated[0]}); "
                    "credit was NOT withheld (warn-only policy), lecturer to check."
                )
            else:
                match.status = "not_demonstrated"
                match.evidence_sentence_ids = negated
                warnings.append(
                    f"Possible contradiction: the answer negates '{match.concept}' (sentence {negated[0]}); "
                    "no credit given, lecturer to check."
                )
        else:
            match.conflicting = True
            warnings.append(
                f"Conflicting statements about '{match.concept}' (negated in sentence {negated[0]}); "
                "lecturer to check."
            )
    return warnings


def _add_semantic_evidence(matches: list[ConceptMatch], sentences: list[str]) -> bool:
    """Optional semantic layer: upgrade a concept to `demonstrated` when a sentence means it (cosine >= threshold).

    Only concepts the word matching did not already fully find are changed, and each change is flagged
    match_method="semantic" with its score. Returns True when the layer ran. Marks are untouched here.
    """
    matcher = get_matcher()
    if matcher is None or not matches:
        return False
    sims = matcher.similarities([m.concept for m in matches], sentences)
    if sims is None:
        return False
    threshold = semantic_threshold()
    for row, match in zip(sims, matches, strict=True):
        match.semantic_score = round(float(row.max()), 4)
        # A negated concept is never rescued by similarity: a sentence that denies a concept is still similar to it.
        if match.status != "demonstrated" and not match.contradicted and match.semantic_score >= threshold:
            match.status = "demonstrated"
            match.match_method = "semantic"
            hits = [i for i, v in enumerate(row, start=1) if v >= threshold]
            match.evidence_sentence_ids = sorted(set(match.evidence_sentence_ids) | set(hits))
    return True


def analyze_answer(request: AnswerAnalysisRequest) -> AnswerAnalysisResponse:
    """Run Function 1's deterministic processing and lexical analysis.

    The result is structured evidence for later C3 stages. It does not award
    marks, assess rubric criteria, or claim genuine semantic understanding.
    """
    # 1) clean and split the answer
    processed_answer = process_text(request.student_answer)
    # 2) how similar are the answer's words to the model answer? (informational only; never changes a mark)
    reference_similarity = lexical_cosine_similarity(
        processed_answer.normalized_text,
        request.reference_answer or "",
    )
    concepts = request.expected_concepts or []
    # 3) warnings the lecturer will see (empty answer, very short answer, missing reference or concepts)
    warnings: list[str] = []
    if not processed_answer.normalized_text:
        warnings.append("student_answer is empty or contains only whitespace")
    elif len(processed_answer.tokens) < 3:
        warnings.append("student_answer is very short")
    if not request.reference_answer or not request.reference_answer.strip():
        warnings.append("reference_answer was not provided")
    if not concepts:
        warnings.append("expected_concepts were not provided")

    concept_matches = _match_concepts(concepts, processed_answer.sentences, processed_answer.tokens)
    warnings.extend(_flag_contradictions(concept_matches, processed_answer.sentences))
    semantic_ran = _add_semantic_evidence(concept_matches, processed_answer.sentences)
    # Descriptive keywords and a possible off-topic flag. Both are information and warnings only; marks never use them.
    relevance = check_relevance(request.student_answer, request.question_text, request.reference_answer, concepts)
    if relevance.status == "off_topic":
        warnings.append(
            "Possible off-topic answer: it shares very little vocabulary with the question, model answer and expected "
            f"concepts ({relevance.shared_ratio:.0%}); lecturer to check."
        )

    # 4) assemble the evidence object used by marking, feedback and the mind map
    return AnswerAnalysisResponse(
        question_id=request.question_id,
        normalized_answer=processed_answer.normalized_text,
        sentence_count=len(processed_answer.sentences),
        token_count=len(processed_answer.tokens),
        sentences=[
            SentenceAnalysis(sentence_id=index, text=sentence)
            for index, sentence in enumerate(processed_answer.sentences, start=1)
        ],
        reference_similarity=reference_similarity,
        concept_matches=concept_matches,
        warnings=warnings,
        analysis_version=SEMANTIC_ANALYSIS_VERSION if semantic_ran else ANALYSIS_VERSION,
        contradiction_check=f"{CONTRADICTION_CHECK}/{contradiction_policy()}",
        keywords=extract_keywords(processed_answer.sentences),
        relevance=relevance,
    )
