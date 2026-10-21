"""Regression checks for the inactive this-quiz pass pipeline."""

from training_practice_quiz_v1.generate import features_from_history, generate_rows
from training_practice_quiz_v1.protocol import (
    FEATURE_NAMES,
    INCOMPATIBLE_ARTIFACT,
    PRODUCT_SCORE_TARGET,
)
from training_practice_quiz_v1.smoke_runner import run_smoke
from training_practice_quiz_v1.train import split_rows


def test_features_use_pre_start_history_only():
    features = features_from_history("Y3S2", {}, ["ds_rpc_messaging"] * 3)
    assert tuple(features) == FEATURE_NAMES
    assert features["cold_start"] == 1.0
    assert features["mean_prior_accuracy"] == 0.5
    assert features["semester_y3s1"] == 0.0
    assert "y_score" not in features
    assert "latent_ability" not in features


def test_splits_are_learner_disjoint_and_cover_both_semesters():
    rows = generate_rows(11, 40)
    parts = split_rows(rows)
    ids = []
    semesters = set()
    for group in parts.values():
        ids.extend(row.learner_id for row in group)
        semesters.update(row.semester for row in group)
    assert len(ids) == len(set(ids)) == 40
    assert semesters == {"Y3S1", "Y3S2"}
    assert all(row.y_pass == int(row.y_score >= PRODUCT_SCORE_TARGET) for row in rows)


def test_smoke_stays_inactive_and_rejects_the_synthetic_exam_model(tmp_path):
    report = run_smoke(learners=40, seed=21)
    assert report["activation_allowed"] is False
    assert report["activation_blocker"] == "real_student_learner_disjoint_validation_required"
    assert report["serves_students"] is False
    assert report["incompatible_live_artifact"] == INCOMPATIBLE_ARTIFACT
    assert report["product_score_target"] == 0.6
    assert report["selected_on"] == "validation"
    assert 0.0 <= report["test_brier"] <= 1.0
    assert report["test_calibration_bins"]
    from training_practice_quiz_v1.serving import assess_bundle, export_inactive_bundle

    export_inactive_bundle(report, tmp_path)
    assessed = assess_bundle(tmp_path)
    assert assessed["usable"] is False
    assert assessed["code"] == "not_activated"
