"""Optional semantic concept layer: off by default, flagged when it acts, fails soft, never touches marking code."""

import numpy as np
import pytest

from app.schemas.analysis import AnswerAnalysisRequest
from services.semantic import analyzer, semantic_matcher
from services.semantic.semantic_matcher import SemanticMatcher

REQ = dict(question_id="Q", question_text="Explain architecture.", reference_answer="Components use interfaces.",
           expected_concepts=["components", "interfaces"], answer_type="short")
PARAPHRASE = "The parts of the system talk to each other. They expose contracts."


class FakeMatcher:
    """Pretends the first sentence means 'components' (0.9) and nothing means 'interfaces' (0.1)."""

    def similarities(self, concepts, sentences):
        m = np.full((len(concepts), len(sentences)), 0.1)
        m[0, 0] = 0.9
        return m


@pytest.fixture(autouse=True)
def _off(monkeypatch):
    monkeypatch.delenv(semantic_matcher.ENV_SWITCH, raising=False)


def _analyse(text):
    return analyzer.analyze_answer(AnswerAnalysisRequest(student_answer=text, **REQ))


def test_off_by_default_paraphrase_is_not_demonstrated():
    r = _analyse(PARAPHRASE)
    assert r.analysis_version == "baseline-v1"
    assert all(m.status == "not_demonstrated" and m.match_method == "lexical" and m.semantic_score is None for m in r.concept_matches)


def test_semantic_layer_upgrades_and_flags(monkeypatch):
    monkeypatch.setattr(analyzer, "get_matcher", lambda: FakeMatcher())
    r = _analyse(PARAPHRASE)
    by = {m.concept: m for m in r.concept_matches}
    assert by["components"].status == "demonstrated" and by["components"].match_method == "semantic"
    assert by["components"].evidence_sentence_ids == [1] and by["components"].semantic_score == 0.9
    assert by["interfaces"].status == "not_demonstrated" and by["interfaces"].match_method == "lexical"
    assert r.analysis_version == "semantic-v1"


def test_lexical_hit_is_never_relabelled_semantic(monkeypatch):
    monkeypatch.setattr(analyzer, "get_matcher", lambda: FakeMatcher())
    r = _analyse("The components expose interfaces.")
    assert all(m.status == "demonstrated" and m.match_method == "lexical" for m in r.concept_matches)


def test_unavailable_matcher_falls_back_to_lexical(monkeypatch):
    class Broken:
        def similarities(self, *_):
            return None

    monkeypatch.setattr(analyzer, "get_matcher", lambda: Broken())
    r = _analyse(PARAPHRASE)
    assert r.analysis_version == "baseline-v1" and all(m.status == "not_demonstrated" for m in r.concept_matches)


def test_switch_controls_registry(monkeypatch):
    assert semantic_matcher.get_matcher() is None
    monkeypatch.setenv(semantic_matcher.ENV_SWITCH, "local")
    assert isinstance(semantic_matcher.get_matcher(), SemanticMatcher)


def test_empty_inputs_return_none():
    assert SemanticMatcher().similarities([], ["a"]) is None
    assert SemanticMatcher().similarities(["a"], []) is None


def test_bad_threshold_env_uses_default(monkeypatch):
    monkeypatch.setenv(semantic_matcher.ENV_THRESHOLD, "abc")
    assert semantic_matcher.semantic_threshold() == semantic_matcher.DEFAULT_THRESHOLD
