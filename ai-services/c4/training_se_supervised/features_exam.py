"""Mock-exam score / pass features from practice before exam start only."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .catalogue import N_TOPICS, ORDERED_TOPICS
from .contract import PASS_THRESHOLD
from .features_response import FeatureScaler, fit_scaler

EXAM_FEATURE_NAMES: list[str] = (
    [f"topic_attempts_{t}" for t in ORDERED_TOPICS]
    + [f"topic_accuracy_{t}" for t in ORDERED_TOPICS]
    + [
        "global_attempts",
        "global_accuracy",
        "mean_topic_accuracy",
        "n_topics_practiced",
        "practice_span_hours",
        "last_topic_index",
    ]
)


def exam_feature_names() -> list[str]:
    return list(EXAM_FEATURE_NAMES)


def build_exam_feature_table(
    practice: pd.DataFrame,
    exams: pd.DataFrame,
) -> pd.DataFrame:
    """One row per learner: practice aggregates before prediction_cutoff / exam_start."""
    practice = practice.sort_values(["learner_id", "step"], kind="mergesort")
    exams = exams.set_index("learner_id")
    records: list[dict[str, Any]] = []

    for lid, g in practice.groupby("learner_id", sort=False):
        if lid not in exams.index:
            raise KeyError(f"Missing exam row for learner {lid}")
        exam = exams.loc[lid]
        cutoff = pd.Timestamp(exam["prediction_cutoff_utc"])
        # Enforce chronology: only practice with timestamp <= cutoff (last practice).
        g = g.copy()
        g["_ts"] = pd.to_datetime(g["timestamp_utc"])
        prior = g[g["_ts"] <= cutoff]
        if len(prior) == 0:
            raise RuntimeError(f"No practice before cutoff for {lid}")

        topic_attempts = np.zeros(N_TOPICS, dtype=np.float64)
        topic_correct = np.zeros(N_TOPICS, dtype=np.float64)
        for _, row in prior.iterrows():
            t_idx = int(row["topic_index"])
            topic_attempts[t_idx] += 1
            topic_correct[t_idx] += int(row["correct"])

        topic_acc = np.where(
            topic_attempts > 0,
            topic_correct / np.maximum(topic_attempts, 1.0),
            0.5,
        )
        practiced = topic_attempts > 0
        mean_acc = float(topic_acc[practiced].mean()) if practiced.any() else 0.5
        global_attempts = float(topic_attempts.sum())
        global_correct = float(topic_correct.sum())
        g_acc = (global_correct / global_attempts) if global_attempts > 0 else 0.5
        span_h = (
            (prior["_ts"].max() - prior["_ts"].min()).total_seconds() / 3600.0
            if len(prior) > 1
            else 0.0
        )
        last_topic = int(prior.iloc[-1]["topic_index"])
        y_score = float(exam["y_exam_score"])
        y_pass = int(y_score >= PASS_THRESHOLD)

        feat: dict[str, Any] = {
            "learner_id": str(lid),
            "prediction_cutoff_utc": str(exam["prediction_cutoff_utc"]),
            "exam_start_utc": str(exam["exam_start_utc"]),
            "global_attempts": global_attempts,
            "global_accuracy": g_acc,
            "mean_topic_accuracy": mean_acc,
            "n_topics_practiced": float(practiced.sum()),
            "practice_span_hours": float(span_h),
            "last_topic_index": float(last_topic),
            "y_exam_score": y_score,
            "y_pass": y_pass,
            "scenario": exam.get("scenario", ""),
            "synthetic": True,
        }
        for k, topic in enumerate(ORDERED_TOPICS):
            feat[f"topic_attempts_{topic}"] = float(topic_attempts[k])
            feat[f"topic_accuracy_{topic}"] = float(topic_acc[k])
        records.append(feat)

    return pd.DataFrame(records)


FORBIDDEN_EXAM_COLS = frozenset(
    {
        "exam_n_correct",
        "true_p_correct",
        "latent_ability",
        "generator_noise",
        "effective_ability_topic",
        "topic_practice_gain",
        "exam_true_p",
    }
)


def assert_exam_features_safe(df: pd.DataFrame) -> None:
    names = set(exam_feature_names())
    overlap = set(df.columns) & FORBIDDEN_EXAM_COLS
    if overlap:
        raise AssertionError(f"Forbidden columns in exam frame: {overlap}")
    missing = names - set(df.columns)
    if missing:
        raise AssertionError(f"Missing exam feature columns: {missing}")
    # Labels may exist as targets but must not be in feature name list.
    if "y_exam_score" in names or "y_pass" in names:
        raise AssertionError("Labels must not be listed as exam features")


def fit_exam_scaler(df: pd.DataFrame) -> FeatureScaler:
    return fit_scaler(df, feature_names=exam_feature_names())
