"""Supervised v1 catalogue features, semester exam coverage, leakage smoke."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training_se_supervised import PROTOCOL_VERSION as V0
from training_se_supervised_v1 import PROTOCOL_VERSION as V1
from training_se_supervised_v1.catalogue import N_TOPICS, Y3S1_TOPICS, Y3S2_TOPICS
from training_se_supervised_v1.contract import (
    CLASSIFICATION_PROB_THRESHOLD,
    PASS_THRESHOLD,
    frozen_contract_dict,
)
from training_se_supervised_v1.features_exam import exam_feature_names
from training_se_supervised_v1.features_response import response_feature_names
from training_se_supervised_v1.generate import generate_scenario_dataset
from training_se_supervised_v1.leakage import assert_no_audit_in_model_matrix
from training_se_supervised_v1.metrics import classification_metrics, regression_metrics


def test_protocols_isolated():
    assert V0 == "se-supervised-sim-v0"
    assert V1 == "se-supervised-sim-v1"


def test_feature_dims_match_catalogue():
    resp = response_feature_names()
    exam = exam_feature_names()
    assert N_TOPICS == 46
    assert sum(1 for n in resp if n.startswith("topic_oh_")) == 46
    assert sum(1 for n in exam if n.startswith("topic_attempts_")) == 46
    assert sum(1 for n in exam if n.startswith("topic_accuracy_")) == 46


def test_pass_vs_prob_thresholds_distinct():
    assert PASS_THRESHOLD == 0.55
    assert CLASSIFICATION_PROB_THRESHOLD == 0.5
    assert PASS_THRESHOLD != CLASSIFICATION_PROB_THRESHOLD


def test_frozen_contract_semester_exam_sizes():
    d = frozen_contract_dict(mode="smoke", master_seed=7)
    c = d["contract"]
    assert c["n_topics"] == 46
    assert c["exam_n_items_y3s1"] == 2 * len(Y3S1_TOPICS)
    assert c["exam_n_items_y3s2"] == 2 * len(Y3S2_TOPICS)
    assert "classification_prob_threshold" in c


def test_generate_smoke_semester_coverage_and_no_latents():
    with tempfile.TemporaryDirectory() as td:
        meta = generate_scenario_dataset(
            Path(td), mode="smoke", scenario_name="baseline", master_seed=11
        )
        assert meta["n_learners"] == 60
        import pandas as pd

        from training_se_supervised_v1.catalogue import TOPIC_SEMESTER
        from training_se_supervised_v1.features_exam import build_exam_feature_table
        from training_se_supervised_v1.features_response import build_response_feature_table

        practice = pd.read_csv(Path(td) / "scenarios/baseline/practice_attempts.csv")
        exams = pd.read_csv(Path(td) / "scenarios/baseline/mock_exams.csv")
        assert set(practice["semester"].unique()) == {"Y3S1", "Y3S2"}

        for _, row in practice.sample(min(20, len(practice)), random_state=0).iterrows():
            assert TOPIC_SEMESTER[row["topic"]] == row["semester"]
        for _, ex in exams.iterrows():
            n_topics = len(Y3S1_TOPICS) if ex["semester"] == "Y3S1" else len(Y3S2_TOPICS)
            assert int(ex["exam_n_items"]) == 2 * n_topics
        assert "latent_ability" not in practice.columns
        assert "latent_ability" not in exams.columns
        # Leakage check is on *feature* frames (targets y_* allowed; audit/latents forbidden).
        resp_feats = build_response_feature_table(practice, max_rows_per_learner=20)
        exam_feats = build_exam_feature_table(practice, exams)
        assert_no_audit_in_model_matrix(resp_feats, "response")
        assert_no_audit_in_model_matrix(exam_feats, "exam")


def test_metrics_include_accuracy_mae_rmse():
    y = np.array([0, 1, 1, 0, 1])
    p = np.array([0.1, 0.8, 0.6, 0.4, 0.9])
    cm = classification_metrics(y, p, prob_threshold=0.5)
    assert "accuracy" in cm and "log_loss" in cm and "brier" in cm and "roc_auc" in cm
    rm = regression_metrics(np.array([0.2, 0.5, 0.9]), np.array([0.3, 0.4, 0.8]))
    assert "mae" in rm and "rmse" in rm
