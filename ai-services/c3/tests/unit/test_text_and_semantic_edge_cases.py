"""Edge-case tests for text_normalizer, semantic analyzer and baseline."""
import pytest

from app.schemas.analysis import AnswerAnalysisRequest
from services.preprocessing.text_normalizer import (
    extract_sentences,
    normalize_text,
    process_text,
    tokenize,
)
from services.semantic.analyzer import analyze_answer
from services.semantic.baseline import lexical_cosine_similarity, token_overlap_score


def request(answer: str, concepts=None, reference=None) -> AnswerAnalysisRequest:
    return AnswerAnalysisRequest(
        question_id="Q1",
        question_text="Q?",
        student_answer=answer,
        reference_answer=reference,
        expected_concepts=concepts,
        answer_type="short",
    )


# ------------------------------------------------------------ text_normalizer
def test_empty_string() -> None:
    processed = process_text("")
    assert processed.normalized_text == "" and processed.sentences == [] and processed.tokens == []


@pytest.mark.parametrize("text", [" ", "  \n\t  ", "  "])
def test_whitespace_only(text) -> None:
    processed = process_text(text)
    assert processed.normalized_text == ""
    assert processed.sentences == []
    assert processed.tokens == []


def test_whitespace_is_collapsed() -> None:
    assert normalize_text("  a \n\n b\t\tc ") == "a b c"


def test_decimal_number_does_not_split_sentence() -> None:
    assert extract_sentences(normalize_text("It scores 3.5 marks. Good.")) == ["It scores 3.5 marks.", "Good."]


def test_version_number_does_not_split_sentence() -> None:
    assert extract_sentences("Version 2.0 is out. ok") == ["Version 2.0 is out.", "ok"]


def test_terminal_punctuation_variants_split() -> None:
    assert extract_sentences("Is it? Yes! Fine.") == ["Is it?", "Yes!", "Fine."]


def test_no_terminal_punctuation_is_single_sentence() -> None:
    assert extract_sentences("no punctuation here") == ["no punctuation here"]


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-N1: 'Use e.g. a cache. It is fast.' is split into ['Use e.g.', 'a cache.', 'It is fast.'] "
    "(text_normalizer.py:5 splits on any [.!?] + whitespace); expected 2 sentences",
)
def test_abbreviation_eg_does_not_split_sentence() -> None:
    assert extract_sentences("Use e.g. a cache. It is fast.") == ["Use e.g. a cache.", "It is fast."]


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-N1: 'Dr. Smith said so. Yes.' is split after 'Dr.' giving 3 sentences "
    "(text_normalizer.py:5); expected 2",
)
def test_abbreviation_title_does_not_split_sentence() -> None:
    assert extract_sentences("Dr. Smith said so. Yes.") == ["Dr. Smith said so.", "Yes."]


def test_unicode_tokens_casefolded() -> None:
    assert tokenize("Straße Ünïcode 数据库") == ["strasse", "ünïcode", "数据库"]


def test_tokenizer_keeps_hyphen_apostrophe_and_drops_underscore() -> None:
    assert tokenize("high-level don't a_b") == ["high-level", "don't", "a", "b"]


def test_unicode_sentence_split() -> None:
    assert extract_sentences("Café open. Naïve yes!") == ["Café open.", "Naïve yes!"]


def test_very_long_input_is_handled_quickly_and_correctly() -> None:
    text = "Security matters. " * 20000
    processed = process_text(text)
    assert len(processed.sentences) == 20000
    assert len(processed.tokens) == 40000


def test_very_long_single_token() -> None:
    assert tokenize("a" * 100000) == ["a" * 100000]


# ------------------------------------------------------------ semantic
def test_empty_answer_analysis() -> None:
    result = analyze_answer(request("", ["security"]))
    assert result.sentence_count == 0 and result.token_count == 0
    assert result.reference_similarity == 0.0
    assert result.concept_matches[0].status == "not_demonstrated"
    assert result.concept_matches[0].evidence_sentence_ids == []
    assert "student_answer is empty or contains only whitespace" in result.warnings


def test_whitespace_answer_analysis_matches_empty() -> None:
    assert analyze_answer(request("   \n ", ["x"])).warnings == analyze_answer(request("", ["x"])).warnings


@pytest.mark.parametrize("concepts", [None, []])
def test_missing_expected_concepts(concepts) -> None:
    result = analyze_answer(request("Some answer text here.", concepts))
    assert result.concept_matches == []
    assert "expected_concepts were not provided" in result.warnings


def test_short_answer_warning() -> None:
    assert "student_answer is very short" in analyze_answer(request("Hi there", ["x"])).warnings


def test_single_stopword_concept_matches_on_stopword_token() -> None:
    """There is no stopword list: a concept consisting only of 'the' is 'demonstrated' by any answer containing it."""
    match = analyze_answer(request("The cat sat.", ["the"])).concept_matches[0]
    assert match.status == "demonstrated" and match.overlap_score == 1.0


def test_concept_status_thresholds() -> None:
    result = analyze_answer(request("Access is logged.", ["access control", "access", "encryption"]))
    statuses = {m.concept: (m.status, m.overlap_score) for m in result.concept_matches}
    assert statuses["access control"] == ("partial", 0.5)
    assert statuses["access"] == ("demonstrated", 1.0)
    assert statuses["encryption"] == ("not_demonstrated", 0.0)


def test_concept_evidence_sentence_ids_are_one_based() -> None:
    result = analyze_answer(request("Nothing here. Encryption is used.", ["encryption"]))
    assert result.concept_matches[0].evidence_sentence_ids == [2]


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-S1: negation not detected - 'The system does not cover encryption.' marks concept "
    "'encryption' as demonstrated with overlap 1.0 (analyzer.py:19-33, baseline.py:33-39 pure token overlap); "
    "expected not demonstrated",
)
def test_negated_mention_is_not_demonstrated() -> None:
    match = analyze_answer(request("The system does not cover encryption.", ["encryption"])).concept_matches[0]
    assert match.status != "demonstrated"


def test_analysis_is_deterministic() -> None:
    first = analyze_answer(request("Security is key. Speed too.", ["security", "speed"], "Security and speed."))
    assert first == analyze_answer(request("Security is key. Speed too.", ["security", "speed"], "Security and speed."))


# ------------------------------------------------------------ baseline
def test_cosine_similarity_edges() -> None:
    assert lexical_cosine_similarity("", "") == 0.0
    assert lexical_cosine_similarity("a b", "") == 0.0
    assert lexical_cosine_similarity("a b", "A  B") == pytest.approx(1.0)
    assert lexical_cosine_similarity("a", "b") == 0.0


def test_token_overlap_empty_concept_or_answer() -> None:
    assert token_overlap_score("", ["a"]) == 0.0
    assert token_overlap_score("!!!", ["a"]) == 0.0
    assert token_overlap_score("a", []) == 0.0
    assert token_overlap_score("a b", ["a"]) == 0.5
