"""
Logic tests for the loader and experiment framework. The tiny release built here exists only to
exercise code paths (hash verification, parsing, metrics, fusion); it is not research data.
"""

import json

import numpy as np
import pandas as pd
import pytest

from datasets.loader import ReleaseError, load_release, sha256_file
from experiments import conditions as cond
from experiments import framework as fw

RUBRIC = {
    "criteria": [
        {
            "criterion_id": "C1",
            "description": "d",
            "max_marks": 4,
            "scoring_levels": [
                {"level_id": "L0", "label": "none", "mark": 0, "descriptor": "x"},
                {"level_id": "L1", "label": "some", "mark": 2, "descriptor": "x"},
                {"level_id": "L2", "label": "full", "mark": 4, "descriptor": "x"},
            ],
        }
    ]
}


def write_tiny_release(root, tamper=False):
    questions = pd.DataFrame(
        [{"question_id": "Q1", "split": "test", "question_text": "q", "max_marks": 4,
          "reference_answer": "ref", "expected_concepts": json.dumps(["a"]), "concept_graph": "[]"}]
    )
    rubrics = pd.DataFrame(
        [{"rubric_id": "R1", "question_id": "Q1", "criterion_id": "C1", "description": "d", "max_marks": 4,
          "scoring_levels": json.dumps(RUBRIC["criteria"][0]["scoring_levels"])}]
    )
    answers = pd.DataFrame(
        [{"answer_id": "A1", "question_id": "Q1", "split": "test", "tier": "FULL", "student_answer": "nan",
          "word_count": 1, "expected_mark": 4, "max_marks": 4, "normalized_mark": 1.0, "needs_review": "False",
          "criterion_marks": "[]", "concept_status": "{}", "incorrect_concepts": "[]", "evidence_spans": "{}",
          "gold_mindmap": "{}"},
         {"answer_id": "A2", "question_id": "Q1", "split": "test", "tier": "EMPTY", "student_answer": "",
          "word_count": 0, "expected_mark": 0, "max_marks": 4, "normalized_mark": 0.0, "needs_review": "True",
          "criterion_marks": "[]", "concept_status": "{}", "incorrect_concepts": "[]", "evidence_spans": "{}",
          "gold_mindmap": "{}"}]
    )
    questions.to_csv(root / "questions.csv", index=False)
    rubrics.to_csv(root / "rubrics.csv", index=False)
    answers.to_csv(root / "answers.csv", index=False)
    files = {n: {"sha256": sha256_file(root / n)} for n in ("questions.csv", "rubrics.csv", "answers.csv")}
    (root / "manifest.json").write_text(json.dumps({"dataset_version": "TEST", "files": files}))
    if tamper:
        (root / "answers.csv").write_text("tampered")


class TestLoader:
    def test_loads_and_preserves_literal_nan_text_and_empty_answers(self, tmp_path):
        write_tiny_release(tmp_path)
        rel = load_release(tmp_path)
        assert rel.version == "TEST"
        answers = rel.split_answers("test")
        assert answers.loc[0, "student_answer"] == "nan"  # text must not be turned into NaN
        assert answers.loc[1, "student_answer"] == ""
        assert len(rel.split_answers("test", include_needs_review=False)) == 1

    def test_rubric_round_trip_matches_api_schema(self, tmp_path):
        write_tiny_release(tmp_path)
        rubric = load_release(tmp_path).rubric_for("Q1")
        assert rubric["criteria"][0]["criterion_id"] == "C1"
        assert rubric["criteria"][0]["scoring_levels"][2]["mark"] == 4

    def test_hash_mismatch_is_rejected(self, tmp_path):
        write_tiny_release(tmp_path, tamper=True)
        with pytest.raises(ReleaseError, match="sha256"):
            load_release(tmp_path)

    def test_missing_release_gives_actionable_error(self, tmp_path):
        with pytest.raises(ReleaseError, match="repaired"):
            load_release(tmp_path / "nope")

    def test_invalid_split_name(self, tmp_path):
        write_tiny_release(tmp_path)
        with pytest.raises(ValueError):
            load_release(tmp_path).split_answers("dev")


class TestParsing:
    def test_level_selection_sums_rubric_marks_only(self):
        mark, chosen = fw.parse_level_selection({"criteria": [{"criterion_id": "C1", "level_id": "L1"}]}, RUBRIC)
        assert mark == 2
        assert chosen[0]["mark"] == 2

    @pytest.mark.parametrize(
        "payload",
        [None, {}, {"criteria": "x"}, {"criteria": [{"criterion_id": "ZZ", "level_id": "L1"}]},
         {"criteria": [{"criterion_id": "C1", "level_id": "L9"}]}, {"criteria": []}],
    )
    def test_invalid_selection_raises(self, payload):
        with pytest.raises(fw.ParseError):
            fw.parse_level_selection(payload, RUBRIC)

    def test_total_mark_is_clamped_and_validated(self):
        assert fw.parse_total_mark({"total_awarded_mark": 99}, 10) == 10
        assert fw.parse_total_mark({"total_awarded_mark": -3}, 10) == 0
        for bad in (None, {}, {"total_awarded_mark": "abc"}, {"total_awarded_mark": float("nan")}):
            with pytest.raises(fw.ParseError):
                fw.parse_total_mark(bad, 10)


def preds(rows):
    return pd.DataFrame(rows, columns=["answer_id", "question_id", "tier", "expected_mark", "max_marks",
                                       "predicted_mark", "failed"])


class TestMetrics:
    def test_failed_rows_are_excluded_and_counted_not_scored_as_zero(self):
        df = preds([["a", "q", "FULL", 10, 10, 8, False], ["b", "q", "FULL", 10, 10, np.nan, True]])
        m = fw.compute_metrics(df)
        assert m["n_failed"] == 1 and m["n_scored"] == 1
        assert m["overall"]["mae"] == 2.0

    def test_metric_values(self):
        df = preds([["a", "q", "FULL", 10, 10, 10, False], ["b", "q", "PARTIAL", 5, 10, 8, False],
                    ["c", "q", "IRRELEVANT", 0, 10, 0, False], ["d", "q", "PARTIAL", 6, 10, 2, False]])
        o = fw.compute_metrics(df)["overall"]
        assert o["mae"] == 1.75
        assert o["rmse"] == round(float(np.sqrt((0 + 9 + 0 + 16) / 4)), 4)
        assert o["within_2_marks_pct"] == 50.0
        assert o["within_10pct_of_max_pct"] == 50.0
        assert set(fw.compute_metrics(df)["by_tier"]) == {"FULL", "PARTIAL", "IRRELEVANT"}

    def test_all_failed_has_no_overall(self):
        m = fw.compute_metrics(preds([["a", "q", "FULL", 1, 1, np.nan, True]]))
        assert m["overall"] is None and m["n_failed"] == 1

    def test_pearson_undefined_for_constant_input(self):
        assert fw.pearson(np.array([1.0, 1.0, 1.0]), np.array([1.0, 2.0, 3.0])) is None


class TestConditionF:
    def make(self, n=40):
        rng = np.random.default_rng(1)
        gold = rng.choice([0.0, 0.25, 0.5, 1.0], size=n)
        return pd.DataFrame(
            {"expected_mark": gold * 10, "max_marks": 10.0, "e_norm": gold, "l_norm": np.clip(gold + 0.1, 0, 1),
             "s_norm": np.clip(gold + rng.normal(0, 0.05, n), 0, 1)}
        )

    def test_fit_chooses_weights_that_sum_to_one_and_fit_well(self):
        params = cond.fit_condition_f(self.make())
        assert abs(params["w_e"] + params["w_l"] + params["w_s"] - 1.0) < 1e-6
        assert params["val_nmae"] < 0.06

    def test_apply_is_bounded_and_uses_gate(self):
        feat = pd.DataFrame({"max_marks": [10.0, 10.0], "e_norm": [0.0, 1.0], "l_norm": [1.0, 1.0],
                             "s_norm": [0.0, 1.0]})
        out = cond.apply_condition_f(feat, {"w_e": 0.2, "w_l": 0.6, "w_s": 0.2, "tau": 0.3})
        assert out[0] == 0.0  # gated: E found nothing and similarity is low
        assert out[1] == 10.0

    def test_results_table_contains_only_supplied_numbers(self):
        from experiments.run_experiments import results_table

        summary = {"condition": "E", "provider": "deterministic", "model": "m",
                   "metrics": fw.compute_metrics(preds([["a", "q", "FULL", 10, 10, 9, False]]))}
        assert "| E | deterministic | m | 1 / 0 | 1.0 |" in results_table([summary])
