"""Next-attempt correctness model comparison (compact)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from .features_response import FeatureScaler, fit_scaler, response_feature_names
from .metrics import calibration_bins, classification_metrics


class _ProbModel(Protocol):
    def predict_proba_positive(self, x: np.ndarray) -> np.ndarray: ...


@dataclass
class ConstantPrevalence:
    prevalence: float

    def predict_proba_positive(self, x: np.ndarray) -> np.ndarray:
        return np.full(shape=(len(x),), fill_value=self.prevalence, dtype=np.float64)


@dataclass
class SklearnProbWrapper:
    model: Any

    def predict_proba_positive(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)[:, 1]


@dataclass
class FittedResponseCandidate:
    name: str
    model: Any
    scaler: FeatureScaler
    train_metrics: dict[str, Any]
    val_metrics: dict[str, Any]
    val_calibration: list[dict[str, Any]]


def _xy(df: pd.DataFrame, scaler: FeatureScaler) -> tuple[np.ndarray, np.ndarray]:
    x = scaler.transform_matrix(df)
    y = df["y_correct"].astype(int).to_numpy()
    return x, y


def fit_response_candidates(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    *,
    seed: int = 42,
) -> list[FittedResponseCandidate]:
    names = response_feature_names()
    scaler = fit_scaler(train_df, feature_names=names)
    x_tr, y_tr = _xy(train_df, scaler)
    x_va, y_va = _xy(val_df, scaler)
    prevalence = float(np.mean(y_tr))

    specs: list[tuple[str, Any]] = [
        ("constant_train_prevalence", ConstantPrevalence(prevalence)),
        (
            "logistic_regression",
            SklearnProbWrapper(
                LogisticRegression(max_iter=500, solver="lbfgs", random_state=seed)
            ),
        ),
        (
            "hist_gradient_boosting_classifier",
            SklearnProbWrapper(
                HistGradientBoostingClassifier(
                    max_depth=4,
                    learning_rate=0.08,
                    max_iter=120,
                    random_state=seed,
                )
            ),
        ),
    ]

    # Fit sklearn models
    for name, wrapper in specs:
        if name == "constant_train_prevalence":
            continue
        wrapper.model.fit(x_tr, y_tr)

    fitted: list[FittedResponseCandidate] = []
    for name, model in specs:
        p_tr = model.predict_proba_positive(x_tr)
        p_va = model.predict_proba_positive(x_va)
        fitted.append(
            FittedResponseCandidate(
                name=name,
                model=model,
                scaler=scaler,
                train_metrics=classification_metrics(y_tr, p_tr),
                val_metrics=classification_metrics(y_va, p_va),
                val_calibration=calibration_bins(y_va, p_va),
            )
        )
    return fitted


def select_best_response(
    candidates: list[FittedResponseCandidate],
    *,
    primary: str = "log_loss",
) -> FittedResponseCandidate:
    # Lower is better for log_loss / brier; higher for roc_auc.
    higher_better = primary in {"roc_auc"}
    def key(c: FittedResponseCandidate) -> float:
        v = c.val_metrics.get(primary)
        if v is None:
            return float("inf") if not higher_better else float("-inf")
        return float(v) if higher_better else float(v)

    if higher_better:
        return max(candidates, key=key)
    return min(candidates, key=key)


def save_response_bundle(path: str | Any, candidate: FittedResponseCandidate, meta: dict) -> None:
    joblib.dump(
        {
            "name": candidate.name,
            "model": candidate.model,
            "scaler": candidate.scaler.to_dict(),
            "feature_names": response_feature_names(),
            "train_metrics": candidate.train_metrics,
            "val_metrics": candidate.val_metrics,
            "meta": meta,
        },
        path,
    )


def load_response_bundle(path: str | Any) -> dict[str, Any]:
    return joblib.load(path)


def predict_response_bundle(bundle: dict[str, Any], df: pd.DataFrame) -> np.ndarray:
    scaler = FeatureScaler.from_dict(bundle["scaler"])
    x = scaler.transform_matrix(df)
    return bundle["model"].predict_proba_positive(x)
