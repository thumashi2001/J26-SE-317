from app.schemas.analysis import (
    AnswerAnalysisRequest,
    AnswerAnalysisResponse,
    ConceptMatch,
    SentenceAnalysis,
)
from services.preprocessing.text_normalizer import process_text, tokenize
from services.semantic.baseline import lexical_cosine_similarity, token_overlap_score


ANALYSIS_VERSION = "baseline-v1"


def _concept_status(overlap_score: float) -> str:
    if overlap_score == 1.0:
        return "demonstrated"
    if overlap_score > 0.0:
        return "partial"
    return "not_demonstrated"


def _match_concepts(concepts: list[str], sentences: list[str], answer_tokens: list[str]) -> list[ConceptMatch]:
    matches: list[ConceptMatch] = []
    for concept in concepts:
        overlap_score = token_overlap_score(concept, answer_tokens)
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


def analyze_answer(request: AnswerAnalysisRequest) -> AnswerAnalysisResponse:
    """Run Function 1's deterministic processing and lexical analysis.

    The result is structured evidence for later C3 stages. It does not award
    marks, assess rubric criteria, or claim genuine semantic understanding.
    """
    processed_answer = process_text(request.student_answer)
    reference_similarity = lexical_cosine_similarity(
        processed_answer.normalized_text,
        request.reference_answer or "",
    )
    concepts = request.expected_concepts or []
    warnings: list[str] = []
    if not processed_answer.normalized_text:
        warnings.append("student_answer is empty or contains only whitespace")
    elif len(processed_answer.tokens) < 3:
        warnings.append("student_answer is very short")
    if not request.reference_answer or not request.reference_answer.strip():
        warnings.append("reference_answer was not provided")
    if not concepts:
        warnings.append("expected_concepts were not provided")

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
        concept_matches=_match_concepts(
            concepts,
            processed_answer.sentences,
            processed_answer.tokens,
        ),
        warnings=warnings,
        analysis_version=ANALYSIS_VERSION,
    )
