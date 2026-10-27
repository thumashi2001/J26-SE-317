"""Multi-LLM comparison harness: identical inputs, failure accounting, quota stop, BLOCKED artefact (stub providers only)."""

import json

import pandas as pd

from experiments import multi_llm_comparison as m
from services.llm.base import BaseLLMProvider, LLMResponse


class Stub(BaseLLMProvider):
    """Test double returning a fixed rubric-valid JSON mark ratio, or a failure. No network."""

    def __init__(self, name, ratio=0.5, fail=None):
        super().__init__(name)
        self.ratio, self.fail, self.calls = ratio, fail, 0

    def is_available(self):
        return True

    def health_check(self):
        return {}

    def generate(self, request):
        self.calls += 1
        if self.fail:
            return LLMResponse(raw_content="", model_identifier="stub", provider_name=self.provider_name,
                               is_success=False, error_message=self.fail)
        marks = round(10 * self.ratio, 2)
        body = {"criteria": [{"criterion_id": "C1", "awarded_marks": marks, "evidence": "e", "reasoning": "r"}],
                "concepts": {}, "feedback": "f"}
        return LLMResponse(raw_content=json.dumps(body), parsed_json=body, model_identifier="stub",
                           provider_name=self.provider_name, is_real_execution=True)


def _answers(n=4):
    return pd.DataFrame([{"answer_id": f"A{i}", "question_id": f"Q{i}", "split": "test", "max_marks": "10",
                          "expected_mark": str(i * 2.5), "answer_quality": "t", "question_text": "q",
                          "reference_answer": "r", "student_answer": "s"} for i in range(n)])


def test_select_answers_is_deterministic_and_split_scoped():
    df = pd.concat([_answers(6), _answers(2).assign(split="validation", answer_id=["V0", "V1"])])
    a, b = m.select_answers(df, "test", 3), m.select_answers(df, "test", 3)
    assert list(a["answer_id"]) == list(b["answer_id"]) and set(a["split"]) == {"test"} and len(a) == 3


def test_providers_get_identical_inputs_and_metrics():
    ans, rows_all = _answers(), []
    for name, ratio in (("p1", 0.5), ("p2", 0.8)):
        rows, st = m.run_provider(name, Stub(name, ratio), ans, None, ("no_rag",), 3, 0.2)
        assert st["stopped"] is None
        rows_all += rows
    df = pd.DataFrame(rows_all)
    assert df.groupby("provider")["answer_id"].apply(tuple).nunique() == 1
    summ = m.summarise(df)
    assert summ["p1|no_rag"]["n_ok"] == 4 and summ["p1|no_rag"]["n_failed"] == 0
    assert abs(m.pairwise_agreement(df)[0]["mean_abs_diff"] - 0.3) < 1e-9


def test_failed_calls_are_excluded_not_scored_zero():
    rows, _ = m.run_provider("bad", Stub("bad", fail="HTTP 500 boom"), _answers(2), None, ("no_rag",), 3, 0.2)
    summ = m.summarise(pd.DataFrame(rows))["bad|no_rag"]
    assert summ["n_ok"] == 0 and summ["n_failed"] == 2 and "nmae" not in summ


def test_quota_errors_stop_the_provider():
    stub = Stub("q", fail="HTTP 429 quota exceeded")
    rows, st = m.run_provider("q", stub, _answers(10), None, ("no_rag",), 3, 0.2)
    assert st["stopped"] == "quota_exhausted" and len(rows) == m.MAX_CONSECUTIVE_QUOTA_ERRORS


def test_blocked_artefact_without_live_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "get_llm_provider", lambda n: Stub(n))
    assert m.main(["--out", str(tmp_path), "--providers", "x,y", "--conditions", "no_rag", "--limit", "3"]) == 0
    art = json.loads((tmp_path / "multi_llm_status.json").read_text(encoding="utf-8"))
    assert art["status"] == "BLOCKED" and not (tmp_path / "multi_llm_predictions.csv").exists()
