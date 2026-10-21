from services.preprocessing.text_normalizer import (
    extract_sentences,
    normalize_text,
    process_text,
    tokenize,
)


def test_normalize_text_collapses_whitespace_and_control_characters() -> None:
    assert normalize_text("  Software\n\t architecture  matters. ") == (
        "Software architecture matters."
    )


def test_extract_sentences_preserves_sentence_punctuation() -> None:
    assert extract_sentences("First sentence. Second sentence! Is it clear?") == [
        "First sentence.",
        "Second sentence!",
        "Is it clear?",
    ]


def test_tokenize_handles_punctuation_without_losing_words() -> None:
    assert tokenize("Systems, components, and relationships.") == [
        "systems",
        "components",
        "and",
        "relationships",
    ]


def test_process_text_handles_empty_answer() -> None:
    processed = process_text(" \n\t ")
    assert processed.normalized_text == ""
    assert processed.sentences == []
    assert processed.tokens == []
