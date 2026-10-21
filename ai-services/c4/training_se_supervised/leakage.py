"""Leakage and data-quality checks for synthetic supervised tables."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .features_exam import FORBIDDEN_EXAM_COLS, assert_exam_features_safe, exam_feature_names
from .features_response import (
    FORBIDDEN_RESPONSE_COLS,
    assert_response_features_safe,
    response_feature_names,
)


def assert_learner_disjoint(id_sets: dict[str, set[str]]) -> None:
    keys = list(id_sets)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            if id_sets[a] & id_sets[b]:
                raise AssertionError(f"Learner overlap between {a} and {b}")


def assert_chronology(practice: pd.DataFrame) -> None:
    for lid, g in practice.groupby("learner_id", sort=False):
        steps = g["step"].to_numpy()
        if not np.all(steps[1:] >= steps[:-1]):
            raise AssertionError(f"Non-monotonic steps for {lid}")
        ts = pd.to_datetime(g["timestamp_utc"]).to_numpy()
        if not np.all(ts[1:] >= ts[:-1]):
            raise AssertionError(f"Non-monotonic timestamps for {lid}")


def assert_exam_after_practice(practice: pd.DataFrame, exams: pd.DataFrame) -> None:
    last = practice.groupby("learner_id")["timestamp_utc"].max()
    for _, row in exams.iterrows():
        lid = row["learner_id"]
        cutoff = pd.Timestamp(row["prediction_cutoff_utc"])
        exam_start = pd.Timestamp(row["exam_start_utc"])
        last_ts = pd.Timestamp(last[lid])
        if cutoff != last_ts:
            raise AssertionError(f"Cutoff must equal last practice for {lid}")
        if not (exam_start > cutoff):
            raise AssertionError(f"Exam must start after cutoff for {lid}")


def assert_no_audit_in_model_matrix(feature_df: pd.DataFrame, kind: str) -> None:
    forbidden = FORBIDDEN_RESPONSE_COLS if kind == "response" else FORBIDDEN_EXAM_COLS
    present = set(feature_df.columns) & set(forbidden)
    # y_* targets are allowed on the frame but not as model inputs.
    present -= {"y_correct", "y_exam_score", "y_pass"}
    if present:
        raise AssertionError(f"Audit/leak columns in {kind} frame: {present}")


def assert_identifiers_not_features(feature_names: list[str]) -> None:
    bad = {"learner_id", "user_id", "event_id", "question_id"}
    if bad & set(feature_names):
        raise AssertionError(f"Identifiers must not be predictive features: {bad & set(feature_names)}")


def run_leakage_suite(
    practice: pd.DataFrame,
    exams: pd.DataFrame,
    response_feats: pd.DataFrame,
    exam_feats: pd.DataFrame,
    id_sets: dict[str, set[str]],
) -> dict[str, Any]:
    assert_learner_disjoint(id_sets)
    assert_chronology(practice)
    assert_exam_after_practice(practice, exams)
    assert_response_features_safe(response_feats)
    assert_exam_features_safe(exam_feats)
    assert_no_audit_in_model_matrix(response_feats, "response")
    assert_no_audit_in_model_matrix(exam_feats, "exam")
    assert_identifiers_not_features(response_feature_names())
    assert_identifiers_not_features(exam_feature_names())

    # Target ranges
    if not set(response_feats["y_correct"].unique()).issubset({0, 1}):
        raise AssertionError("y_correct must be binary")
    if not ((exam_feats["y_exam_score"] >= 0).all() and (exam_feats["y_exam_score"] <= 1).all()):
        raise AssertionError("y_exam_score must be in [0,1]")
    if not set(exam_feats["y_pass"].unique()).issubset({0, 1}):
        raise AssertionError("y_pass must be binary")

    return {
        "ok": True,
        "n_response_rows": int(len(response_feats)),
        "n_exam_rows": int(len(exam_feats)),
        "response_prevalence": float(response_feats["y_correct"].mean()),
        "exam_score_mean": float(exam_feats["y_exam_score"].mean()),
        "pass_prevalence": float(exam_feats["y_pass"].mean()),
        "checks": [
            "learner_disjoint",
            "chronology",
            "exam_after_practice",
            "response_pre_attempt_features",
            "exam_pre_exam_features",
            "no_audit_latents_in_features",
            "no_identifiers_as_features",
            "target_ranges",
        ],
    }
