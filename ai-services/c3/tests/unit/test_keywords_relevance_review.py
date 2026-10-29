"""Keywords (FR-C3-017), off-topic flag (FR-C3-020/095), disconnected concepts (FR-C3-073) and the review rules
(FR-C3-079/093).

All of these are deterministic word-level rules. The tests check that the rules behave as written and that none of them
changes a mark; they do not claim the rules agree with human judgement.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.assessment import AssessmentRequest
from services.assessment.orchestrator import assess_answer
from services.assessment.review_rules import RULES, active_rules
from services.mindmap.generator import find_disconnected_concepts
from services.semantic.keywords import extract_keywords
from services.semantic.relevance import check_relevance, off_topic_threshold

client = TestClient(app)

RUBRIC = {"rubric_id": "R1", "title": "Components", "criteria": [{
    "criterion_id": "C1", "description": "Explain components", "max_marks": 4,
    "required_concepts": ["components", "interfaces"],
    "scoring_levels": [
        {"level_id": "L4", "label": "Full", "mark": 4.0, "descriptor": "both",
         "required_concepts": ["components", "interfaces"]},
        {"level_id": "L2", "label": "Part", "mark": 2.0, "descriptor": "one", "required_concepts": ["components"]},
        {"level_id": "L0", "label": "None", "mark": 0.0, "descriptor": "nothing"},
    ],
}]}


def _request(answer, concepts=("components", "interfaces")):
    return AssessmentRequest.model_validate({
        "question_id": "Q1", "question_text": "Explain software components and their interfaces.",
        "student_answer": answer,
        "reference_answer": "Components are parts of a system that communicate through interfaces.",
        "expected_concepts": list(concepts), "answer_type": "short", "rubric": RUBRIC,
    })


# ------------------------------------------------------------------------------------------------ keywords

def test_keywords_count_content_words_and_skip_filler():
    found = extract_keywords(["The cache stores data.", "The cache speeds up the data access."])
    terms = {k.term: k for k in found}
    assert "the" not in terms and "up" not in terms
    assert terms["cache"].count == 2 and terms["cache"].kind == "word" and terms["cache"].sentence_ids == [1, 2]
    assert terms["data"].count == 2


def test_repeated_adjacent_pair_is_a_phrase_but_a_single_pair_is_not():
    sentences = ["Load balancer spreads traffic.", "A load balancer helps uptime."]
    found = {k.term: k.kind for k in extract_keywords(sentences)}
    assert found["load balancer"] == "phrase"
    single = {k.term for k in extract_keywords(["Traffic passes through one load balancer."])}
    assert "load balancer" not in single


def test_keywords_are_deterministic_ranked_and_limited():
    text = [" ".join(f"word{i} " * (i % 3 + 1) for i in range(30))]
    first, second = extract_keywords(text), extract_keywords(text)
    assert first == second and len(first) == 10
    counts = [k.count for k in first]
    assert counts == sorted(counts, reverse=True)
    assert extract_keywords([]) == [] and extract_keywords([""]) == []


# ------------------------------------------------------------------------------------------------ relevance

def test_on_topic_answer_is_relevant_and_unrelated_answer_is_flagged():
    q, ref = "Explain software components and interfaces.", "Components communicate through interfaces."
    concepts = ["components"]
    on = check_relevance("Components expose interfaces so other components can communicate.", q, ref, concepts)
    off = check_relevance("My holiday in the mountains was relaxing with great weather and food.", q, ref, concepts)
    assert on.status == "relevant" and on.shared_ratio >= 0.1
    assert off.status == "off_topic" and off.shared_ratio < 0.1


def test_too_short_answer_or_empty_topic_is_not_assessed():
    assert check_relevance("components", "Explain components.", "x", ["components"]).status == "not_assessed"
    assert check_relevance("holiday mountains weather food relax", "", None, []).status == "not_assessed"


def test_plural_and_singular_count_as_the_same_word():
    question = "Explain components, interfaces, modules, services."
    result = check_relevance("component interface module service", question, None, [])
    assert result.status == "relevant" and result.shared_ratio == 1.0


def test_off_topic_threshold_is_configurable_and_validated(monkeypatch):
    monkeypatch.delenv("C3_OFF_TOPIC_BELOW", raising=False)
    assert off_topic_threshold() == 0.10
    monkeypatch.setenv("C3_OFF_TOPIC_BELOW", "0.5")
    assert off_topic_threshold() == 0.5
    for bad in ("1.5", "-0.1", "abc"):
        monkeypatch.setenv("C3_OFF_TOPIC_BELOW", bad)
        with pytest.raises(ValueError):
            off_topic_threshold()


def test_off_topic_answer_gets_a_warning_flag_and_review_but_the_mark_follows_the_rubric_only():
    off_topic = _request("My holiday in the mountains was relaxing with great weather and good food.")
    result = assess_answer(off_topic)
    assert result.analysis.relevance.status == "off_topic"
    assert any("Possible off-topic" in w for w in result.warnings)
    assert result.review.needs_review and any(r.startswith("off_topic") for r in result.review.reasons)
    # the rubric gave zero because no concept was found, not because of the flag
    assert result.total_awarded_marks == 0.0


def test_on_topic_marks_are_identical_to_the_rubric_level_rule():
    result = assess_answer(_request("Components are parts of a system and they communicate through interfaces."))
    assert result.total_awarded_marks == 4.0
    assert result.analysis.relevance.status == "relevant"
    assert not result.review.needs_review and result.review.reasons == []


# ------------------------------------------------------------------------------------------------ mind map

def test_disconnected_concepts_are_credited_concepts_without_a_concept_link():
    result = assess_answer(_request("Components exist. Interfaces exist."))
    assert result.mindmap.summary.disconnected_concepts == ["components", "interfaces"]
    linked = assess_answer(_request("Components depend on interfaces."))
    assert linked.mindmap.summary.disconnected_concepts == []


def test_fewer_than_two_credited_concepts_never_disconnected():
    assert find_disconnected_concepts([], []) == []
    result = assess_answer(_request("Components exist in every system we build."))
    assert result.mindmap.summary.disconnected_concepts == []


def test_disconnected_concepts_do_not_add_warnings_or_change_marks():
    unlinked = assess_answer(_request("Components exist. Interfaces exist."))
    assert not any("not linked" in w for w in unlinked.warnings)


# ------------------------------------------------------------------------------------------------ review rules

def test_each_review_rule_fires_in_its_own_situation(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "warn_only")
    fired = lambda answer: {r.split(":")[0] for r in assess_answer(_request(answer)).review.reasons}  # noqa: E731
    assert "very_short" in fired("ok")
    assert "no_evidence" in fired("The weather today is sunny and warm across the whole region.")
    assert "zero_marks" in fired("The weather today is sunny and warm across the whole region.")
    assert "contradiction" in fired("Components do not have interfaces in this design at all.")
    assert fired("Components are parts of a system and they communicate through interfaces.") == set()


def test_review_rules_are_configurable_and_unknown_names_are_rejected(monkeypatch):
    monkeypatch.setenv("C3_REVIEW_RULES", "very_short")
    assert active_rules() == ["very_short"]
    result = assess_answer(_request("The weather today is sunny and warm across the whole region."))
    assert result.review.rules_applied == ["very_short"] and not result.review.needs_review
    monkeypatch.setenv("C3_REVIEW_RULES", "very_short,not_a_rule")
    with pytest.raises(ValueError, match="not_a_rule"):
        active_rules()
    monkeypatch.delenv("C3_REVIEW_RULES")
    assert active_rules() == list(RULES)


def test_review_flag_never_changes_the_mark(monkeypatch):
    answer = "The weather today is sunny and warm across the whole region."
    monkeypatch.setenv("C3_REVIEW_RULES", "very_short")
    quiet = assess_answer(_request(answer))
    monkeypatch.delenv("C3_REVIEW_RULES")
    loud = assess_answer(_request(answer))
    assert loud.review.needs_review and not quiet.review.needs_review
    assert loud.total_awarded_marks == quiet.total_awarded_marks


def test_new_fields_are_returned_by_the_http_endpoint():
    body = _request("Components are parts of a system and they communicate through interfaces.").model_dump()
    data = client.post("/c3/assess", json=body).json()
    assert data["analysis"]["keywords"] and data["analysis"]["relevance"]["status"] == "relevant"
    assert data["review"]["needs_review"] is False and data["review"]["rules_version"] == "review-rules-v1"
    assert "disconnected_concepts" in data["mindmap"]["summary"]
