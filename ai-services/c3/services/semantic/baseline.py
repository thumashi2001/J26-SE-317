from collections import Counter
import math

from services.preprocessing.text_normalizer import tokenize


def lexical_cosine_similarity(first_text: str, second_text: str) -> float:
    """Calculate deterministic token-frequency cosine similarity.

    This lexical overlap is a reproducible baseline, not true semantic
    understanding. It is intentionally lightweight so stronger semantic models
    can be evaluated against it later.
    """
    first_counts = Counter(tokenize(first_text))
    second_counts = Counter(tokenize(second_text))
    if not first_counts or not second_counts:
        return 0.0

    vocabulary = set(first_counts) | set(second_counts)
    dot_product = sum(first_counts[token] * second_counts[token] for token in vocabulary)
    first_norm = math.sqrt(sum(count * count for count in first_counts.values()))
    second_norm = math.sqrt(sum(count * count for count in second_counts.values()))
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0

    return max(0.0, min(1.0, dot_product / (first_norm * second_norm)))


def token_overlap_score(concept: str, answer_tokens: list[str]) -> float:
    """Measure normalized concept-token coverage in an answer.

    Token overlap provides transparent evidence for a baseline only; it does
    not establish that a student understands or correctly explains a concept.
    """
    concept_tokens = set(tokenize(concept))
    if not concept_tokens:
        return 0.0
    answer_token_set = set(answer_tokens)
    return len(concept_tokens & answer_token_set) / len(concept_tokens)
