"""Historical (pre-response) features for the learner-response model.

Leakage rule: features for predicting interaction t may use only information
strictly before t. Current-row correctness, hints, and response time are targets
or post-decision signals and must not enter X for that same row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

FEATURE_NAMES = (
    "skill_prior_attempts",
    "skill_prior_correct",
    "skill_prior_accuracy",
    "skill_prior_consecutive_correct",
    "global_prior_attempts",
    "global_prior_accuracy",
    "learner_step",
)


@dataclass
class FeatureScaler:
    means: dict[str, float]
    stds: dict[str, float]
    feature_names: tuple[str, ...] = FEATURE_NAMES

    def transform_row(self, values: dict[str, float]) -> np.ndarray:
        out = []
        for name in self.feature_names:
            mu = self.means[name]
            sd = self.stds[name] if self.stds[name] > 1e-8 else 1.0
            out.append((float(values[name]) - mu) / sd)
        return np.asarray(out, dtype=np.float32)

    def transform_matrix(self, df: pd.DataFrame) -> np.ndarray:
        mats = []
        for name in self.feature_names:
            mu = self.means[name]
            sd = self.stds[name] if self.stds[name] > 1e-8 else 1.0
            mats.append(((df[name].astype(float) - mu) / sd).to_numpy())
        return np.column_stack(mats).astype(np.float32)

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
            feature_names=tuple(d["feature_names"]),
        )


def build_historical_features(interactions: pd.DataFrame) -> pd.DataFrame:
    """Vectorised-enough historical features; O(N) per learner group."""
    records: list[dict[str, Any]] = []
    for user_id, g in interactions.groupby("user_id", sort=False):
        skill_attempts: dict[str, int] = {}
        skill_correct: dict[str, int] = {}
        skill_streak: dict[str, int] = {}
        global_attempts = 0
        global_correct = 0
        for _, row in g.iterrows():
            skill = str(row["primary_skill"])
            sa = skill_attempts.get(skill, 0)
            sc = skill_correct.get(skill, 0)
            st = skill_streak.get(skill, 0)
            feat = {
                "user_id": str(user_id),
                "order_id": int(row["order_id"]),
                "learner_step": int(row["learner_step"]),
                "primary_skill": skill,
                "skill_tokens": list(row["skill_tokens"]) if isinstance(row["skill_tokens"], list) else [],
                "y_correct": int(row["correct"]),
                "skill_prior_attempts": float(sa),
                "skill_prior_correct": float(sc),
                "skill_prior_accuracy": float(sc / sa) if sa > 0 else 0.5,
                "skill_prior_consecutive_correct": float(st),
                "global_prior_attempts": float(global_attempts),
                "global_prior_accuracy": float(global_correct / global_attempts) if global_attempts > 0 else 0.5,
            }
            records.append(feat)
            # Update AFTER emitting features (no leakage of current outcome).
            y = int(row["correct"])
            # Credit all tagged skills with the outcome for state tracking, but
            # prediction features above used primary_skill history only.
            tokens = feat["skill_tokens"] or [skill]
            for tok in tokens:
                skill_attempts[tok] = skill_attempts.get(tok, 0) + 1
                skill_correct[tok] = skill_correct.get(tok, 0) + y
                skill_streak[tok] = (skill_streak.get(tok, 0) + 1) if y == 1 else 0
            global_attempts += 1
            global_correct += y
    return pd.DataFrame.from_records(records)


def fit_scaler(feature_df: pd.DataFrame) -> FeatureScaler:
    means = {}
    stds = {}
    for name in FEATURE_NAMES:
        col = feature_df[name].astype(float)
        means[name] = float(col.mean())
        stds[name] = float(col.std(ddof=0))
    return FeatureScaler(means=means, stds=stds)


def assert_no_current_outcome_leakage(feature_df: pd.DataFrame) -> None:
    """Software check: feature columns must not include current-response fields."""
    banned = {
        "correct",
        "hint_count",
        "hint_total",
        "ms_first_response",
        "attempt_count",
        "bottom_hint",
        "first_action",
        "overlap_time",
        "answer_text",
    }
    overlap = banned & set(feature_df.columns)
    if overlap:
        raise AssertionError(f"Potential leakage columns present in features: {sorted(overlap)}")
    if "y_correct" not in feature_df.columns:
        raise AssertionError("Expected target column y_correct")
