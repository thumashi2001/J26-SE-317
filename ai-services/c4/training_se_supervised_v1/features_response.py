"""Next-attempt correctness features (strictly pre-attempt)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .catalogue import N_TOPICS, ORDERED_TOPICS

# Numeric feature columns used by models (topic one-hots appended dynamically).
BASE_FEATURE_NAMES: tuple[str, ...] = (
    "difficulty",
    "topic_prior_attempts",
    "topic_prior_correct",
    "topic_prior_accuracy",
    "topic_prior_streak",
    "global_prior_attempts",
    "global_prior_accuracy",
    "learner_step",
)


def response_feature_names() -> list[str]:
    return list(BASE_FEATURE_NAMES) + [f"topic_oh_{t}" for t in ORDERED_TOPICS]


@dataclass
class FeatureScaler:
    means: dict[str, float]
    stds: dict[str, float]
    feature_names: list[str]

    def transform_matrix(self, df: pd.DataFrame) -> np.ndarray:
        cols = []
        for name in self.feature_names:
            mu = self.means[name]
            sd = self.stds[name] if self.stds[name] > 1e-8 else 1.0
            cols.append(((df[name].astype(float) - mu) / sd).to_numpy())
        return np.column_stack(cols).astype(np.float64)

    def to_dict(self) -> dict[str, Any]:
        return {
            "means": self.means,
            "stds": self.stds,
            "feature_names": list(self.feature_names),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FeatureScaler":
        return cls(
            means={k: float(v) for k, v in d["means"].items()},
            stds={k: float(v) for k, v in d["stds"].items()},
            feature_names=list(d["feature_names"]),
        )


def fit_scaler(df: pd.DataFrame, feature_names: list[str] | None = None) -> FeatureScaler:
    names = feature_names or response_feature_names()
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for name in names:
        col = df[name].astype(float)
        means[name] = float(col.mean())
        stds[name] = float(col.std(ddof=0))
    return FeatureScaler(means=means, stds=stds, feature_names=list(names))


def build_response_feature_table(
    practice: pd.DataFrame,
    *,
    max_rows_per_learner: int | None = None,
) -> pd.DataFrame:
    """Build one row per practice attempt with features from history BEFORE that attempt."""
    practice = practice.sort_values(["learner_id", "step"], kind="mergesort").reset_index(drop=True)
    records: list[dict[str, Any]] = []

    for lid, g in practice.groupby("learner_id", sort=False):
        topic_attempts = np.zeros(N_TOPICS, dtype=np.int64)
        topic_correct = np.zeros(N_TOPICS, dtype=np.int64)
        topic_streak = np.zeros(N_TOPICS, dtype=np.int64)
        global_attempts = 0
        global_correct = 0
        rows_kept = 0
        for _, row in g.iterrows():
            t_idx = int(row["topic_index"])
            ta = int(topic_attempts[t_idx])
            tc = int(topic_correct[t_idx])
            acc = (tc / ta) if ta > 0 else 0.5
            g_acc = (global_correct / global_attempts) if global_attempts > 0 else 0.5
            feat: dict[str, Any] = {
                "event_id": row["event_id"],
                "learner_id": str(lid),
                "timestamp_utc": row["timestamp_utc"],
                "topic": row["topic"],
                "topic_index": t_idx,
                "question_id": row["question_id"],
                "difficulty": float(row["difficulty"]),
                "topic_prior_attempts": ta,
                "topic_prior_correct": tc,
                "topic_prior_accuracy": float(acc),
                "topic_prior_streak": int(topic_streak[t_idx]),
                "global_prior_attempts": int(global_attempts),
                "global_prior_accuracy": float(g_acc),
                "learner_step": int(row["step"]),
                "y_correct": int(row["correct"]),
                "scenario": row.get("scenario", ""),
                "synthetic": True,
            }
            for k, topic in enumerate(ORDERED_TOPICS):
                feat[f"topic_oh_{topic}"] = 1.0 if k == t_idx else 0.0

            if max_rows_per_learner is None or rows_kept < max_rows_per_learner:
                records.append(feat)
                rows_kept += 1

            # Update AFTER recording features (no target leakage into this row).
            topic_attempts[t_idx] += 1
            topic_correct[t_idx] += int(row["correct"])
            if int(row["correct"]) == 1:
                topic_streak[t_idx] += 1
            else:
                topic_streak[t_idx] = 0
            global_attempts += 1
            global_correct += int(row["correct"])

    return pd.DataFrame(records)


FORBIDDEN_RESPONSE_COLS = frozenset(
    {
        "correct",
        "true_p_correct",
        "latent_ability",
        "generator_noise",
        "effective_ability_topic",
        "topic_practice_gain",
        "exam_score",
        "y_exam_score",
        "y_pass",
    }
)


def assert_response_features_safe(df: pd.DataFrame) -> None:
    names = set(response_feature_names())
    overlap = set(df.columns) & FORBIDDEN_RESPONSE_COLS
    if overlap:
        raise AssertionError(f"Forbidden columns present in response frame: {overlap}")
    missing = names - set(df.columns)
    if missing:
        raise AssertionError(f"Missing response feature columns: {missing}")
    # First attempt per learner must have zero priors.
    first = df.groupby("learner_id", sort=False).head(1)
    if not (first["topic_prior_attempts"] == 0).all():
        raise AssertionError("First-row topic_prior_attempts must be 0")
    if not (first["global_prior_attempts"] == 0).all():
        raise AssertionError("First-row global_prior_attempts must be 0")
