"""Focused software smoke tests for se-supervised-sim-v0 (not full Colab training)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training_se_supervised.contract import PASS_THRESHOLD, PRIMARY_SCENARIO, frozen_contract_dict
from training_se_supervised.export_bundle import verify_manifest
from training_se_supervised.features_exam import build_exam_feature_table, exam_feature_names
from training_se_supervised.features_response import (
    build_response_feature_table,
    response_feature_names,
)
from training_se_supervised.generate import generate_all_scenarios, generate_scenario_dataset
from training_se_supervised.inventory import inventory_local_se_exports
from training_se_supervised.leakage import run_leakage_suite
from training_se_supervised.models_exam import load_exam_bundle, predict_exam_bundle
from training_se_supervised.models_response import load_response_bundle, predict_response_bundle
from training_se_supervised.pipeline import reload_run, run_final_evaluation, run_training_and_validation
from training_se_supervised.splits import split_learner_ids


@pytest.fixture(scope="module")
def smoke_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("se_supervised_smoke")
    result = run_training_and_validation(
        root,
        mode="smoke",
        master_seed=42,
        c4_root=C4_ROOT,
    )
    return Path(result["run_dir"]), result


def test_inventory_documents_synthetic_path():
    inv = inventory_local_se_exports(C4_ROOT)
    assert "decision" in inv
    # Workspace has no authorized SE exports; expect synthetic path.
    if not inv["real_se_exports_available"]:
        assert "synthetic" in inv["decision"].lower()


def test_frozen_contract_declares_pass_threshold_and_scenarios():
    c = frozen_contract_dict(mode="smoke", master_seed=42)
    assert c["contract"]["pass_threshold"] == PASS_THRESHOLD
    assert set(c["contract"]["scenarios"]) == {"baseline", "high_noise", "easy_bank"}
    assert c["synthetic"] is True
    assert c["real_exam_validation"] is False


def test_deterministic_generation(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate_scenario_dataset(a, mode="smoke", scenario_name="baseline", master_seed=7)
    generate_scenario_dataset(b, mode="smoke", scenario_name="baseline", master_seed=7)
    pa = pd.read_csv(a / "scenarios" / "baseline" / "practice_attempts.csv")
    pb = pd.read_csv(b / "scenarios" / "baseline" / "practice_attempts.csv")
    assert pa["correct"].tolist() == pb["correct"].tolist()
    assert pa["question_id"].tolist() == pb["question_id"].tolist()
    ea = pd.read_csv(a / "scenarios" / "baseline" / "mock_exams.csv")
    eb = pd.read_csv(b / "scenarios" / "baseline" / "mock_exams.csv")
    assert ea["y_exam_score"].tolist() == eb["y_exam_score"].tolist()


def test_learner_disjoint_and_leakage(tmp_path):
    generate_all_scenarios(tmp_path, mode="smoke", master_seed=42)
    practice = pd.read_csv(tmp_path / "scenarios" / PRIMARY_SCENARIO / "practice_attempts.csv")
    exams = pd.read_csv(tmp_path / "scenarios" / PRIMARY_SCENARIO / "mock_exams.csv")
    learners = pd.read_csv(tmp_path / "scenarios" / PRIMARY_SCENARIO / "learners.csv")
    id_sets = split_learner_ids(learners["learner_id"], master_seed=42)
    resp = build_response_feature_table(practice, max_rows_per_learner=12)
    exam_f = build_exam_feature_table(practice, exams)
    report = run_leakage_suite(practice, exams, resp, exam_f, id_sets)
    assert report["ok"] is True
    assert id_sets["train"].isdisjoint(id_sets["validation"])
    assert id_sets["train"].isdisjoint(id_sets["test"])


def test_response_features_exclude_target_and_future():
    # Construct a tiny hand sequence
    rows = []
    for step, correct in enumerate([1, 0, 1]):
        rows.append(
            {
                "event_id": f"e{step}",
                "learner_id": "L0",
                "timestamp_utc": f"2024-01-01T0{step}:00:00",
                "step": step,
                "topic": "normalization",
                "topic_index": 3,
                "module_code": "SE3060",
                "question_id": f"q{step}",
                "difficulty": 0.1,
                "correct": correct,
                "scenario": "baseline",
            }
        )
    practice = pd.DataFrame(rows)
    feats = build_response_feature_table(practice)
    assert feats.loc[0, "topic_prior_attempts"] == 0
    assert feats.loc[0, "global_prior_attempts"] == 0
    # After first correct, second row sees prior_correct=1
    assert feats.loc[1, "topic_prior_attempts"] == 1
    assert feats.loc[1, "topic_prior_correct"] == 1
    # Target column exists but is not in feature name list
    assert "y_correct" not in response_feature_names()
    assert "learner_id" not in response_feature_names()


def test_exam_features_exclude_exam_answers_and_latents(tmp_path):
    generate_scenario_dataset(tmp_path, mode="smoke", scenario_name="baseline", master_seed=3)
    practice = pd.read_csv(tmp_path / "scenarios" / "baseline" / "practice_attempts.csv")
    exams = pd.read_csv(tmp_path / "scenarios" / "baseline" / "mock_exams.csv")
    exam_f = build_exam_feature_table(practice, exams)
    names = set(exam_feature_names())
    assert "y_exam_score" not in names
    assert "y_pass" not in names
    assert "latent_ability" not in names
    assert "exam_n_correct" not in names
    assert ((exam_f["y_exam_score"] >= 0) & (exam_f["y_exam_score"] <= 1)).all()
    assert set(exam_f["y_pass"].unique()).issubset({0, 1})


def test_smoke_pipeline_save_load_and_checksums(smoke_run):
    run_dir, result = smoke_run
    assert (run_dir / "SELECTION_FROZEN.json").is_file()
    assert (run_dir / "models" / "response_selected.joblib").is_file()
    assert (run_dir / "models" / "exam_score_selected.joblib").is_file()
    assert (run_dir / "export_bundle" / "manifest.json").is_file()

    # Preprocessing fitted on train only is implied by scaler saved from train fit;
    # verify predict consistency after reload.
    practice = pd.read_csv(
        run_dir / "synthetic_data" / "scenarios" / PRIMARY_SCENARIO / "practice_attempts.csv"
    )
    exams = pd.read_csv(
        run_dir / "synthetic_data" / "scenarios" / PRIMARY_SCENARIO / "mock_exams.csv"
    )
    split = json.loads((run_dir / "split_ids.json").read_text(encoding="utf-8"))
    id_sets = {k: set(v) for k, v in split["learner_ids"].items()}
    from training_se_supervised.splits import assign_split_column

    resp = assign_split_column(build_response_feature_table(practice, max_rows_per_learner=24), id_sets)
    exam_f = assign_split_column(build_exam_feature_table(practice, exams), id_sets)
    val_resp = resp[resp["split"] == "validation"].head(20)
    val_exam = exam_f[exam_f["split"] == "validation"].head(20)

    rb = load_response_bundle(run_dir / "models" / "response_selected.joblib")
    eb = load_exam_bundle(run_dir / "models" / "exam_score_selected.joblib")
    p1 = predict_response_bundle(rb, val_resp)
    p2 = predict_response_bundle(rb, val_resp)
    assert np.allclose(p1, p2)
    e1 = predict_exam_bundle(eb, val_exam)
    e2 = predict_exam_bundle(eb, val_exam)
    assert np.allclose(e1, e2)

    man = verify_manifest(run_dir / "export_bundle")
    assert man["ok"] is True
    assert man["n"] > 5

    reloaded = reload_run(run_dir)
    assert reloaded["selection"]["response"]["name"] == result["selection"]["response"]["name"]


def test_saved_config_required_for_final(smoke_run):
    run_dir, _ = smoke_run
    # Gated without flag
    with pytest.raises(RuntimeError, match="gated"):
        run_final_evaluation(run_dir, run_final=False)
    # With flag loads frozen config (no defaults)
    out = run_final_evaluation(run_dir, run_final=True)
    assert out["response_test"]["n"] > 0
    assert out["exam_score_test"]["n"] > 0
    assert (run_dir / "final_test" / "final_test_metrics.json").is_file()


def test_full_training_gated(tmp_path):
    with pytest.raises(RuntimeError, match="gated"):
        run_training_and_validation(tmp_path, mode="full", run_full=False)
