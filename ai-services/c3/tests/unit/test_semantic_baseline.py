from services.semantic.baseline import (
    lexical_cosine_similarity,
    token_overlap_score,
)


def test_similar_answers_have_high_similarity() -> None:
    score = lexical_cosine_similarity(
        "Software architecture defines system structure.",
        "Software architecture defines the system structure.",
    )
    assert 0.8 < score <= 1.0


def test_different_answers_have_zero_similarity() -> None:
    assert lexical_cosine_similarity("Database indexing", "User interface design") == 0.0


def test_empty_reference_is_safe() -> None:
    assert lexical_cosine_similarity("A student answer", "") == 0.0


def test_concept_overlap_is_deterministic() -> None:
    assert token_overlap_score("high-level structure", ["the", "high-level", "structure"]) == 1.0
    assert token_overlap_score("components relationships", ["components"]) == 0.5
    assert token_overlap_score("components", ["architecture"]) == 0.0
