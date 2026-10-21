"""Mock-exam score regression and optional pass classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge

from .contract import PASS_MIN_CLASS_COUNT, PASS_THRESHOLD
from .features_exam import exam_feature_names, fit_exam_scaler
from .features_response import FeatureScaler
from .metrics import calibration_bins, classification_metrics, regression_metrics
from .models_response import ConstantPrevalence, SklearnProbWrapper


@dataclass
class TrainMeanRegressor:
    mean: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.full(shape=(len(x),), fill_value=self.mean, dtype=np.float64)


@dataclass
class SklearnRegWrapper:
    model: Any

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x).astype(np.float64)


@dataclass
class FittedExamCandidate:
    name: str
    model: Any
    scaler: FeatureScaler
    train_metrics: dict[str, Any]
    val_metrics: dict[str, Any]


@dataclass
class FittedPassCandidate:
    name: str
    model: Any
    scaler: FeatureScaler
    train_metrics: dict[str, Any]
    val_metrics: dict[str, Any]
    val_calibration: list[dict[str, Any]]


def _xy_reg(df: pd.DataFrame, scaler: FeatureScaler) -> tuple[np.ndarray, np.ndarray]:
    x = scaler.transform_matrix(df)
    y = df["y_exam_score"].astype(float).to_numpy()
    return x, y


def fit_exam_score_candidates(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    *,
    seed: int = 42,
) -> list[FittedExamCandidate]:
    scaler = fit_exam_scaler(train_df)
    x_tr, y_tr = _xy_reg(train_df, scaler)
    x_va, y_va = _xy_reg(val_df, scaler)
    mean = float(np.mean(y_tr))

    specs: list[tuple[str, Any]] = [
        ("train_mean", TrainMeanRegressor(mean)),
        ("ridge_regression", SklearnRegWrapper(Ridge(alpha=1.0))),
        (
            "hist_gradient_boosting_regressor",
            SklearnRegWrapper(
                HistGradientBoostingRegressor(
                    max_depth=4,
                    learning_rate=0.08,
                    max_iter=120,
                    random_state=seed,
                )
            ),
        ),
    ]
    for name, wrapper in specs:
        if name == "train_mean":
            continue
        wrapper.model.fit(x_tr, y_tr)

    out: list[FittedExamCandidate] = []
    for name, model in specs:
        out.append(
            FittedExamCandidate(
                name=name,
                model=model,
                scaler=scaler,
                train_metrics=regression_metrics(y_tr, model.predict(x_tr)),
                val_metrics=regression_metrics(y_va, model.predict(x_va)),
            )
        )
    return out


def select_best_exam(
    candidates: list[FittedExamCandidate],
    *,
    primary: str = "mae",
) -> FittedExamCandidate:
    return min(candidates, key=lambda c: float(c.val_metrics[primary]))


def pass_enabled(train_df: pd.DataFrame) -> dict[str, Any]:
    y = train_df["y_pass"].astype(int).to_numpy()
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    enabled = n_pos >= PASS_MIN_CLASS_COUNT and n_neg >= PASS_MIN_CLASS_COUNT
    return {
        "enabled": enabled,
        "pass_threshold": PASS_THRESHOLD,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "min_class_count": PASS_MIN_CLASS_COUNT,
        "reason": (
            "both classes meet minimum count"
            if enabled
            else "insufficient class support — pass models skipped"
        ),
    }


def fit_pass_candidates(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    *,
    seed: int = 42,
) -> list[FittedPassCandidate]:
    info = pass_enabled(train_df)
    if not info["enabled"]:
        return []
    scaler = fit_exam_scaler(train_df)
    x_tr = scaler.transform_matrix(train_df)
    y_tr = train_df["y_pass"].astype(int).to_numpy()
    x_va = scaler.transform_matrix(val_df)
    y_va = val_df["y_pass"].astype(int).to_numpy()
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
    for name, wrapper in specs:
        if name == "constant_train_prevalence":
            continue
        wrapper.model.fit(x_tr, y_tr)

    out: list[FittedPassCandidate] = []
    for name, model in specs:
        p_tr = model.predict_proba_positive(x_tr)
        p_va = model.predict_proba_positive(x_va)
        out.append(
            FittedPassCandidate(
                name=name,
                model=model,
                scaler=scaler,
                train_metrics=classification_metrics(y_tr, p_tr),
                val_metrics=classification_metrics(y_va, p_va),
                val_calibration=calibration_bins(y_va, p_va),
            )
        )
    return out


def select_best_pass(
    candidates: list[FittedPassCandidate],
    *,
    primary: str = "log_loss",
) -> FittedPassCandidate:
    return min(candidates, key=lambda c: float(c.val_metrics[primary]))


def save_exam_bundle(path: Any, candidate: FittedExamCandidate, meta: dict) -> None:
    joblib.dump(
        {
            "name": candidate.name,
            "model": candidate.model,
            "scaler": candidate.scaler.to_dict(),
            "feature_names": exam_feature_names(),
            "train_metrics": candidate.train_metrics,
            "val_metrics": candidate.val_metrics,
            "meta": meta,
        },
        path,
    )


def save_pass_bundle(path: Any, candidate: FittedPassCandidate, meta: dict) -> None:
    joblib.dump(
        {
            "name": candidate.name,
            "model": candidate.model,
            "scaler": candidate.scaler.to_dict(),
            "feature_names": exam_feature_names(),
            "train_metrics": candidate.train_metrics,
            "val_metrics": candidate.val_metrics,
            "meta": meta,
        },
        path,
    )


def load_exam_bundle(path: Any) -> dict[str, Any]:
    return joblib.load(path)


def predict_exam_bundle(bundle: dict[str, Any], df: pd.DataFrame) -> np.ndarray:
    scaler = FeatureScaler.from_dict(bundle["scaler"])
    x = scaler.transform_matrix(df)
    return bundle["model"].predict(x)


def predict_pass_bundle(bundle: dict[str, Any], df: pd.DataFrame) -> np.ndarray:
    scaler = FeatureScaler.from_dict(bundle["scaler"])
    x = scaler.transform_matrix(df)
    return bundle["model"].predict_proba_positive(x)
