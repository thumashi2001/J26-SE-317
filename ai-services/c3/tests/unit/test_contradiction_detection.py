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

def test_withhold_credit_policy_only_negated_mentions_become_contradicted_and_lose_credit(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "withhold_credit")
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


def test_withhold_credit_policy_semantic_layer_never_rescues_a_contradicted_concept(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "withhold_credit")
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


def test_withhold_credit_policy_denied_concept_earns_no_rubric_credit_while_affirmed_words_do(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "withhold_credit")
    affirmed = _assess("It defines the high-level structure. It organizes components and their relationships.")
    denied = _assess("It has no high-level structure. It does not organize components and has no relationships.")
    assert affirmed["total_awarded_marks"] == 4.0
    assert denied["total_awarded_marks"] == 0.0
    statuses = {c["concept"]: c["status"] for c in denied["analysis"]["concept_matches"]}
    assert set(statuses.values()) == {"not_demonstrated"}
    assert all(c["contradicted"] for c in denied["analysis"]["concept_matches"])


def test_withhold_credit_policy_feedback_names_contradicted_concepts_and_warns(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "withhold_credit")
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


# ------------------------------------------------------------ policy: warn_only (default) or withhold_credit

def test_default_when_the_variable_is_unset_is_warn_only(monkeypatch):
    from services.semantic.negation import contradiction_policy

    monkeypatch.delenv("C3_CONTRADICTION_POLICY", raising=False)
    assert contradiction_policy() == "warn_only"
    result = _analyse("The system does not cover encryption.", ["encryption"])
    match = result.concept_matches[0]
    assert match.contradicted and match.status == "demonstrated"  # flag only: status untouched
    assert result.contradiction_check == "negation-cue-v1/warn_only"  # the active policy is recorded
    assert any("NOT withheld" in w for w in result.warnings)


def test_warn_only_marks_equal_the_marks_of_an_analysis_without_the_check(monkeypatch):
    # The flag must not move the mark: compare against the same answer with the rule neutralised.
    monkeypatch.delenv("C3_CONTRADICTION_POLICY", raising=False)
    answer = "It has no high-level structure. It does not organize components and has no relationships."
    flagged = _assess(answer)
    assert any(c["contradicted"] for c in flagged["analysis"]["concept_matches"])
    monkeypatch.setattr("services.semantic.analyzer.sentence_negates", lambda *_: False)
    unflagged = _assess(answer)
    assert not any(c["contradicted"] for c in unflagged["analysis"]["concept_matches"])
    assert flagged["total_awarded_marks"] == unflagged["total_awarded_marks"] == 4.0
    # everything that decides the mark is identical; only the warning text differs
    assert flagged["marking"]["criteria_results"] == unflagged["marking"]["criteria_results"]
    fb = flagged["feedback"]["criteria_feedback"][0]
    assert set(fb["contradicted_concepts"]) == {"high-level structure", "components", "relationships"}
    assert not fb["missing_concepts"] and any("Credit was not withheld" in w for w in fb["warnings"])


def test_normal_rubric_marking_is_the_same_under_both_policies_for_affirmative_answers(monkeypatch):
    answer = "It defines the high-level structure. It organizes components and their relationships."
    results = {}
    for policy in ("warn_only", "withhold_credit"):
        monkeypatch.setenv("C3_CONTRADICTION_POLICY", policy)
        data = _assess(answer)
        assert not any(c["contradicted"] for c in data["analysis"]["concept_matches"])
        results[policy] = data["marking"]
    assert results["warn_only"] == results["withhold_credit"]
    assert _assess(answer)["total_awarded_marks"] == 4.0


def test_withhold_credit_is_an_explicit_opt_in_recorded_in_the_analysis(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", " Withhold_Credit ")  # case and spaces are tolerated
    result = _analyse("The system does not cover encryption.", ["encryption"])
    assert result.concept_matches[0].status == "not_demonstrated"
    assert result.contradiction_check == "negation-cue-v1/withhold_credit"


def test_unknown_policy_value_falls_back_to_warn_only(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "delete_everything")
    match = _analyse("The system does not cover encryption.", ["encryption"]).concept_matches[0]
    assert match.contradicted and match.status == "demonstrated"


def test_withhold_credit_marks_and_lecturer_table_agree(monkeypatch):
    monkeypatch.setenv("C3_CONTRADICTION_POLICY", "withhold_credit")
    data = _assess("It organizes components. It has no relationships between them.")
    statuses = {c["concept"]: c for c in data["analysis"]["concept_matches"]}
    assert statuses["relationships"]["contradicted"] and statuses["relationships"]["status"] == "not_demonstrated"
    fb = data["feedback"]["criteria_feedback"][0]
    assert fb["contradicted_concepts"] == ["relationships"] and "relationships" in fb["missing_concepts"]
    assert data["total_awarded_marks"] == data["marking"]["total_awarded_marks"] == fb["awarded_mark"]
