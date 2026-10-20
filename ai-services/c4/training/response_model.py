"""Interpretable learner-response model (logistic regression on historical features).

Predicted correctness ≠ measured causal knowledge gain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from .features import FEATURE_NAMES, FeatureScaler, fit_scaler


@dataclass
class ResponseModelBundle:
    model: LogisticRegression
    scaler: FeatureScaler
    skill_index: dict[str, int]
    train_metrics: dict[str, float]
    val_metrics: dict[str, float] | None
    fitted_parameters: dict[str, Any]
    assumed_parameters: dict[str, Any]

    def predict_proba(self, feature_df: pd.DataFrame) -> np.ndarray:
        x = self.scaler.transform_matrix(feature_df)
        return self.model.predict_proba(x)[:, 1]

    def to_disk(self, path: str) -> None:
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler.to_dict(),
                "skill_index": self.skill_index,
                "train_metrics": self.train_metrics,
                "val_metrics": self.val_metrics,
                "fitted_parameters": self.fitted_parameters,
                "assumed_parameters": self.assumed_parameters,
                "feature_names": list(FEATURE_NAMES),
            },
            path,
        )

    @classmethod
    def from_disk(cls, path: str) -> "ResponseModelBundle":
        obj = joblib.load(path)
        return cls(
            model=obj["model"],
            scaler=FeatureScaler.from_dict(obj["scaler"]),
            skill_index=obj["skill_index"],
            train_metrics=obj["train_metrics"],
            val_metrics=obj.get("val_metrics"),
            fitted_parameters=obj["fitted_parameters"],
            assumed_parameters=obj["assumed_parameters"],
        )


def _metrics(y_true: np.ndarray, p: np.ndarray) -> dict[str, float]:
    y_hat = (p >= 0.5).astype(int)
    out = {
        "accuracy": float(accuracy_score(y_true, y_hat)),
        "brier": float(brier_score_loss(y_true, p)),
        "log_loss": float(log_loss(y_true, np.clip(p, 1e-6, 1 - 1e-6))),
        "n": int(len(y_true)),
        "positive_rate": float(np.mean(y_true)),
    }
    if len(np.unique(y_true)) > 1:
        out["roc_auc"] = float(roc_auc_score(y_true, p))
    else:
        out["roc_auc"] = float("nan")
    return out


def fit_response_model(
    train_features: pd.DataFrame,
    val_features: pd.DataFrame | None = None,
    *,
    seed: int = 42,
) -> ResponseModelBundle:
    scaler = fit_scaler(train_features)
    x_train = scaler.transform_matrix(train_features)
    y_train = train_features["y_correct"].astype(int).to_numpy()

    model = LogisticRegression(
        max_iter=500,
        solver="lbfgs",
        random_state=seed,
        class_weight="balanced",
    )
    model.fit(x_train, y_train)
    train_p = model.predict_proba(x_train)[:, 1]
    train_metrics = _metrics(y_train, train_p)

    val_metrics = None
    if val_features is not None and len(val_features):
        x_val = scaler.transform_matrix(val_features)
        y_val = val_features["y_correct"].astype(int).to_numpy()
        val_p = model.predict_proba(x_val)[:, 1]
        val_metrics = _metrics(y_val, val_p)

    skills = sorted(train_features["primary_skill"].astype(str).unique())
    skill_index = {s: i for i, s in enumerate(skills)}

    fitted = {
        "model_family": "sklearn.linear_model.LogisticRegression",
        "feature_names": list(FEATURE_NAMES),
        "coefficients": {
            name: float(coef)
            for name, coef in zip(FEATURE_NAMES, model.coef_.ravel(), strict=True)
        },
        "intercept": float(model.intercept_.ravel()[0]),
        "scaler_means": scaler.means,
        "scaler_stds": scaler.stds,
        "n_train_rows": int(len(train_features)),
        "note": "Coefficients describe association with next-step correctness, not causal learning gains.",
    }
    assumed = {
        "mastery_state_dynamics": "assumed in simulator/env; not identified from ASSISTments A/B treatments",
        "multi_skill_credit": "outcome credited to all tagged skills when updating histories after prediction",
    }
    return ResponseModelBundle(
        model=model,
        scaler=scaler,
        skill_index=skill_index,
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        fitted_parameters=fitted,
        assumed_parameters=assumed,
    )


def evaluate_response_model(bundle: ResponseModelBundle, feature_df: pd.DataFrame) -> dict[str, float]:
    p = bundle.predict_proba(feature_df)
    y = feature_df["y_correct"].astype(int).to_numpy()
    return _metrics(y, p)
