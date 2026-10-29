"""Possible off-topic answer flag (FR-C3-020, FR-C3-095): how many of the answer's words belong to the question's topic.

SIMPLE ENGLISH
    The "topic vocabulary" is every content word in the question, the model answer and the expected concepts. If an
    answer of reasonable length uses almost none of those words, it is flagged as possibly off-topic so a lecturer
    looks at it. This is a word-overlap heuristic: an answer that is correct but phrased with completely different
    words can be flagged too, and an off-topic answer that happens to reuse the question's words is not. The flag is
    information and a warning only; it never changes a mark. The threshold is a design choice that has not been
    measured against human judgements.
"""
import os

from app.schemas.analysis import RelevanceCheck
from services.preprocessing.text_normalizer import tokenize
from services.semantic.keywords import is_content_word

RELEVANCE_CHECK = "topic-vocabulary-overlap-v1"
MIN_ANSWER_WORDS = 4          # shorter answers are not assessed: too little text to judge
DEFAULT_OFF_TOPIC_BELOW = 0.10  # share of the answer's distinct content words found in the topic vocabulary


def off_topic_threshold() -> float:
    """C3_OFF_TOPIC_BELOW (0..1) overrides the default share; an invalid value is rejected, not ignored."""
    raw = os.getenv("C3_OFF_TOPIC_BELOW", "").strip()
    if not raw:
        return DEFAULT_OFF_TOPIC_BELOW
    value = float(raw)  # ValueError for a non-number
    if not 0.0 <= value <= 1.0:
        raise ValueError("C3_OFF_TOPIC_BELOW must be between 0 and 1")
    return value


def _stem(token: str) -> str:
    """Very light plural folding so 'components' and 'component' count as the same word."""
    return token[:-1] if len(token) > 3 and token.endswith("s") and not token.endswith("ss") else token


def _vocabulary(texts: list[str]) -> set[str]:
    """Distinct content words (lightly stemmed) of the given texts."""
    return {_stem(t) for text in texts for t in tokenize(text) if is_content_word(t)}


def check_relevance(
    student_answer: str, question_text: str, reference_answer: str | None, concepts: list[str]
) -> RelevanceCheck:
    """Compare the answer's content words with the topic vocabulary and report relevant / off_topic / not_assessed."""
    answer_words = _vocabulary([student_answer])
    topic = _vocabulary([question_text, reference_answer or "", *concepts])
    if len(answer_words) < MIN_ANSWER_WORDS:
        return RelevanceCheck(status="not_assessed", content_words=len(answer_words), shared_ratio=None,
                              basis=f"{RELEVANCE_CHECK}: fewer than {MIN_ANSWER_WORDS} distinct content words")
    if not topic:
        return RelevanceCheck(status="not_assessed", content_words=len(answer_words), shared_ratio=None,
                              basis=f"{RELEVANCE_CHECK}: no topic vocabulary available")
    ratio = round(len(answer_words & topic) / len(answer_words), 4)
    status = "off_topic" if ratio < off_topic_threshold() else "relevant"
    return RelevanceCheck(status=status, content_words=len(answer_words), shared_ratio=ratio,
                          basis=f"{RELEVANCE_CHECK}: {ratio:.0%} of the answer's content words are in the topic words")
