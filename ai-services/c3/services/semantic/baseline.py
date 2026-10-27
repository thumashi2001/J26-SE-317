"""The two word-matching measures that the live marking path is built on.

IMPORTANT FOR THE VIVA
    These are NOT trained models and NOT embeddings. They are simple, reproducible word-count formulas:
      * token_overlap_score  - "what fraction of the concept's words appear in the answer?"  (drives concept status)
      * lexical_cosine_similarity - word-frequency cosine between two texts (shown as `reference_similarity`;
        it does NOT change the awarded mark)
    A paraphrase that uses different words scores 0 here; that is the main known limitation of the baseline.
"""
import math
from collections import Counter

from services.preprocessing.text_normalizer import tokenize


def lexical_cosine_similarity(first_text: str, second_text: str) -> float:
    """Calculate deterministic token-frequency cosine similarity.

    This lexical overlap is a reproducible baseline, not true semantic
    understanding. It is intentionally lightweight so stronger semantic models
    can be evaluated against it later.
    """
    # Count how often each word occurs in each text.
    first_counts = Counter(tokenize(first_text))
    second_counts = Counter(tokenize(second_text))
    if not first_counts or not second_counts:
        return 0.0

    # Cosine = dot product / (length of vector 1 * length of vector 2), over the shared vocabulary.
    vocabulary = set(first_counts) | set(second_counts)
    dot_product = sum(first_counts[token] * second_counts[token] for token in vocabulary)
    first_norm = math.sqrt(sum(count * count for count in first_counts.values()))
    second_norm = math.sqrt(sum(count * count for count in second_counts.values()))
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0

    # Clamp to [0, 1] to guard against tiny floating-point drift.
    return max(0.0, min(1.0, dot_product / (first_norm * second_norm)))


def token_overlap_score(concept: str, answer_tokens: list[str]) -> float:
    """Measure normalized concept-token coverage in an answer.

    Token overlap provides transparent evidence for a baseline only; it does
    not establish that a student understands or correctly explains a concept.
    """
    # Example: concept "high-level structure" has tokens {high-level, structure}; if the answer contains only
    # "structure" the score is 1/2 = 0.5 ("partial"); if it contains both the score is 1.0 ("demonstrated").
    concept_tokens = set(tokenize(concept))
    if not concept_tokens:
        return 0.0
    answer_token_set = set(answer_tokens)
    return len(concept_tokens & answer_token_set) / len(concept_tokens)
