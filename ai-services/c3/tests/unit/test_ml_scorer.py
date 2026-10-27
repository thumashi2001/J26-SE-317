"""Advisory AI score estimate: off by default, never changes marks, fails soft (no model or network needed)."""

import pytest

from app.schemas.assessment import AssessmentRequest
from services.assessment import orchestrator
from services.ml import scorer as scorer_mod
from services.ml.scorer import MLScorer

RUBRIC = {
    "rubric_id": "R", "title": "T",
    "criteria": [{
        "criterion_id": "C1", "description": "Explain components.", "max_marks": 4, "required_concepts": ["components"],
        "scoring_levels": [
            {"level_id": "L0", "label": "None", "mark": 0, "descriptor": "Nothing."},
            {"level_id": "L4", "label": "Full", "mark": 4, "descriptor": "Components named.",
             "required_concepts": ["components"], "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 1}},
        ],
    }],
}


def _request(answer: str, reference: str | None = "Components communicate through interfaces."):
    return AssessmentRequest(question_id="Q", question_text="Explain architecture components.", student_answer=answer,
                             reference_answer=reference, rubric=RUBRIC, expected_concepts=["components"],
                             answer_type="short", max_marks=4)


class FakeScorer:
    model_name = "fake-model"

    def __init__(self, ratio):
        self.ratio = ratio

    def estimate_ratio(self, reference, answer):
        return self.ratio


@pytest.fixture(autouse=True)
def _no_real_model(monkeypatch):
    monkeypatch.delenv(scorer_mod.ENV_DIR, raising=False)


def test_off_by_default_and_marks_unchanged():
    r = orchestrator.assess_answer(_request("The components talk to each other."))
    assert r.ai_estimate is None and r.total_awarded_marks == 4


def test_estimate_is_advisory_and_never_changes_the_mark(monkeypatch):
    base = orchestrator.assess_answer(_request("The components talk to each other."))
    monkeypatch.setattr(orchestrator, "get_scorer", lambda: FakeScorer(0.1))
    r = orchestrator.assess_answer(_request("The components talk to each other."))
    assert r.total_awarded_marks == base.total_awarded_marks == 4
    est = r.ai_estimate
    assert est.advisory and est.model == "fake-model" and est.rubric_ratio == 1.0
    assert est.estimated_marks == 0.4 and est.needs_review is True
    assert any("lecturer review" in w for w in r.warnings)


def test_agreement_does_not_flag_review(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_scorer", lambda: FakeScorer(0.9))
    r = orchestrator.assess_answer(_request("The components talk to each other."))
    assert r.ai_estimate.needs_review is False and not any("AI score estimate" in w for w in r.warnings)


def test_no_reference_answer_means_no_estimate(monkeypatch):
    monkeypatch.setattr(orchestrator, "get_scorer", lambda: FakeScorer(0.5))
    assert orchestrator.assess_answer(_request("components", reference=None)).ai_estimate is None


def test_unconfigured_or_broken_scorer_returns_none(tmp_path):
    assert MLScorer(None).estimate_ratio("ref", "ans") is None
    (tmp_path / "model.pt").write_bytes(b"not a checkpoint")
    broken = MLScorer(tmp_path)
    assert broken.configured() and broken.estimate_ratio("ref", "ans") is None
    assert broken.status()["failure"]  # failure is recorded, nothing raised


def test_registry_follows_the_environment_variable(monkeypatch, tmp_path):
    first = scorer_mod.get_scorer()
    monkeypatch.setenv(scorer_mod.ENV_DIR, str(tmp_path))
    assert scorer_mod.get_scorer() is not first
