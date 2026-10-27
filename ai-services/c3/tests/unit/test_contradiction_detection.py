"""Possible-contradiction flag (negation cues): rule behaviour, analyser wiring, marking/feedback consequences, limits.

These tests describe what the RULE does on hand-written sentences. They do not show that contradiction detection is accurate on
real student answers; no accuracy has been measured (that needs human-labelled data).
"""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnswerAnalysisRequest
from services.semantic import analyzer
from services.semantic.negation import sentence_mentions, sentence_negates
from tests.integration.test_assessment_api import base_rubric

client = TestClient(app)


def _analyse(text, concepts):
    return analyzer.analyze_answer(AnswerAnalysisRequest(
        question_id="Q", question_text="Q", student_answer=text, expected_concepts=concepts, answer_type="short"))


# ------------------------------------------------------------------ the rule

@pytest.mark.parametrize("concept,sentence", [
    ("encryption", "The system does not cover encryption."),
    ("components", "A system has no separate parts; architecture does not divide software into components."),
    ("encapsulation", "Encapsulation doesn't hide anything."),
    ("encapsulation", "Encapsulation doesn’t hide anything."),
    ("interfaces", "Good designs never use interfaces."),
    ("components", "The design has no components at all."),
    ("tests", "We ship without tests."),
])
def test_negated_mentions_are_flagged(concept, sentence):
    assert sentence_mentions(concept, sentence) and sentence_negates(concept, sentence)


@pytest.mark.parametrize("concept,sentence", [
    ("atomic values", "1NF requires each attribute to have single atomic values with no repeating groups."),  # "no" scopes a later noun
    ("components", "Components not only hide detail but also expose interfaces."),
    ("components", "The system is no longer a monolith and its components talk through interfaces."),
    ("components", "Architecture divides software into components."),
])
def test_affirmative_or_non_scoping_negation_is_not_flagged(concept, sentence):
    assert not sentence_negates(concept, sentence)


def test_cue_must_be_close_to_the_concept():
    near = "Components are not optional."
    far = "Components are chosen carefully by the whole team after a long discussion, and not rushed."
    assert sentence_negates("components", near)
    assert not sentence_negates("components", far)


def test_all_concept_words_must_be_present():
    assert not sentence_negates("separation of concerns", "There is no separation here.")


# ----------------------------------------------------------------- the analyser

def test_only_negated_mentions_become_contradicted_and_lose_credit():
    result = _analyse("The system does not cover encryption.", ["encryption"])
    match = result.concept_matches[0]
    assert match.contradicted and match.status == "not_demonstrated" and match.negated_sentence_ids == [1]
    assert match.evidence_sentence_ids == [1]  # the lecturer is pointed at the negating sentence
    assert any("Possible contradiction" in w and "encryption" in w for w in result.warnings)
    assert result.contradiction_check == "negation-cue-v1/withhold_credit"


def test_affirmed_and_negated_mentions_are_conflicting_not_contradicted():
    result = _analyse("Encapsulation hides data. Encapsulation does not mean copying.", ["encapsulation"])
    match = result.concept_matches[0]
    assert match.conflicting and not match.contradicted and match.status == "demonstrated"
    assert match.negated_sentence_ids == [2]
    assert any("Conflicting statements" in w for w in result.warnings)


def test_plain_answers_are_unchanged_by_the_check():
    match = _analyse("Components expose interfaces.", ["components", "interfaces"]).concept_matches
    assert [m.status for m in match] == ["demonstrated", "demonstrated"]
    assert not any(m.contradicted or m.conflicting or m.negated_sentence_ids for m in match)


def test_semantic_layer_never_rescues_a_contradicted_concept(monkeypatch):
    class AlwaysSimilar:
        def similarities(self, concepts, sentences):
            return np.full((len(concepts), len(sentences)), 0.99)

    monkeypatch.setattr(analyzer, "get_matcher", lambda: AlwaysSimilar())
    match = _analyse("The system does not cover encryption.", ["encryption"]).concept_matches[0]
    assert match.contradicted and match.status == "not_demonstrated" and match.match_method == "lexical"


# ----------------------------------------------------- marking and feedback path

def _assess(answer):
    payload = {"question_id": "Q-ARCH-01", "question_text": "Explain software architecture and its components.",
               "student_answer": answer, "expected_concepts": ["high-level structure", "components", "relationships"],
               "answer_type": "short", "rubric": base_rubric()}
    response = client.post("/c3/assess", json=payload)
    assert response.status_code == 200
    return response.json()


def test_a_denied_concept_earns_no_rubric_credit_while_the_same_words_affirmed_do():
    affirmed = _assess("It defines the high-level structure. It organizes components and their relationships.")
    denied = _assess("It has no high-level structure. It does not organize components and has no relationships.")
    assert affirmed["total_awarded_marks"] == 4.0
    assert denied["total_awarded_marks"] == 0.0
    statuses = {c["concept"]: c["status"] for c in denied["analysis"]["concept_matches"]}
    assert set(statuses.values()) == {"not_demonstrated"}
    assert all(c["contradicted"] for c in denied["analysis"]["concept_matches"])


def test_feedback_names_contradicted_concepts_and_warns_without_changing_the_mark():
    data = _assess("It organizes components. It has no relationships between them.")
    fb = data["feedback"]["criteria_feedback"][0]
    assert "relationships" in fb["contradicted_concepts"] and "relationships" in fb["missing_concepts"]
    assert any("Possible contradiction" in w and "relationships" in w for w in fb["warnings"])
    assert fb["awarded_mark"] == data["marking"]["criteria_results"][0]["awarded_mark"]
    node = next(n for n in data["mindmap"]["nodes"] if n.get("concept") == "relationships")
    assert node["status"] == "not_demonstrated"


# ---------------------------------------------------------- known limitations

@pytest.mark.parametrize("sentence", [
    "Encapsulation exposes all data directly to other classes.",         # wrong, but no negation word
    "Encapsulation is when a class inherits fields from a parent.",       # related but incorrect
    "Encapsulation of a pharmaceutical capsule uses a gelatin shell.",    # keyword trap
])
def test_wrong_statements_without_a_negation_cue_are_NOT_detected(sentence):
    # Documented limitation, not a goal: these still read as demonstrated by word matching.
    match = _analyse(sentence, ["encapsulation"]).concept_matches[0]
    assert match.status == "demonstrated" and not match.contradicted


def test_a_correct_negated_sentence_is_also_flagged_so_the_result_is_only_a_possible_contradiction():
    match = _analyse("Encapsulation does not mean exposing data.", ["encapsulation"]).concept_matches[0]
    assert match.contradicted  # false positive by design: the lecturer decides


# ------------------------------------------------------------ policy: withhold or warn only

def test_warn_only_policy_flags_but_leaves_status_and_mark_unchanged(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "warn_only")
    result = _analyse("The system does not cover encryption.", ["encryption"])
    match = result.concept_matches[0]
    assert match.contradicted and match.status == "demonstrated"  # flag only
    assert any("NOT withheld" in w for w in result.warnings)
    assert result.contradiction_check == "negation-cue-v1/warn_only"
    data = _assess("It has no high-level structure. It does not organize components and has no relationships.")
    assert data["total_awarded_marks"] == 4.0  # same as an affirmed answer: nothing changed the mark
    fb = data["feedback"]["criteria_feedback"][0]
    assert set(fb["contradicted_concepts"]) == {"high-level structure", "components", "relationships"}
    assert not fb["missing_concepts"]
    assert any("Credit was not withheld" in w for w in fb["warnings"])


def test_unknown_policy_value_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "delete_everything")
    assert _analyse("The system does not cover encryption.", ["encryption"]).concept_matches[0].status == "not_demonstrated"


def test_default_policy_marks_and_lecturer_table_agree():
    data = _assess("It organizes components. It has no relationships between them.")
    statuses = {c["concept"]: c for c in data["analysis"]["concept_matches"]}
    assert statuses["relationships"]["contradicted"] and statuses["relationships"]["status"] == "not_demonstrated"
    fb = data["feedback"]["criteria_feedback"][0]
    assert fb["contradicted_concepts"] == ["relationships"] and "relationships" in fb["missing_concepts"]
    assert data["total_awarded_marks"] == data["marking"]["total_awarded_marks"] == fb["awarded_mark"]
