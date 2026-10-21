"""Train-only preprocessing, validation-only selection, one untouched test report.

Synthetic results do not authorize student serving.
"""

from __future__ import annotations

import math

import numpy as np

from training_practice_quiz_v1.generate import QuizRow
from training_practice_quiz_v1.protocol import ACTIVATION_BLOCKER, FEATURE_NAMES, PRODUCT_SCORE_TARGET


def split_rows(rows: list[QuizRow]) -> dict[str, list[QuizRow]]:
    ordered = sorted(rows, key=lambda row: row.learner_id)
    n = len(ordered)
    train_end = max(1, int(n * 0.6))
    val_end = max(train_end + 1, int(n * 0.8))
    if val_end >= n:
        val_end = n - 1
    parts = {
        "train": ordered[:train_end],
        "validation": ordered[train_end:val_end],
        "test": ordered[val_end:],
    }
    ids = [row.learner_id for row in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("learner ids must be unique")
    seen: set[str] = set()
    for name, group in parts.items():
        if not group:
            raise ValueError(f"{name} split is empty")
        group_ids = {row.learner_id for row in group}
        if seen & group_ids:
            raise ValueError("learner ids overlap across splits")
        seen |= group_ids
    return parts


def matrix(rows: list[QuizRow]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray([[row.features[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1e-8] = 1.0
    y_score = np.asarray([row.y_score for row in rows], dtype=float)
    y_pass = np.asarray([row.y_pass for row in rows], dtype=float)
    return (x - mean) / std, y_score, y_pass


def apply_scale(rows: list[QuizRow], train_rows: list[QuizRow]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    train_x, _, _ = matrix(train_rows)
    raw = np.asarray([[row.features[name] for name in FEATURE_NAMES] for row in rows], dtype=float)
    train_raw = np.asarray([[row.features[name] for name in FEATURE_NAMES] for row in train_rows], dtype=float)
    mean = train_raw.mean(axis=0)
    std = train_raw.std(axis=0)
    std[std < 1e-8] = 1.0
    y_score = np.asarray([row.y_score for row in rows], dtype=float)
    y_pass = np.asarray([row.y_pass for row in rows], dtype=float)
    del train_x
    return (raw - mean) / std, y_score, y_pass


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_logistic(x: np.ndarray, y: np.ndarray, steps: int = 250, lr: float = 0.2) -> np.ndarray:
    bias = np.ones((len(x), 1))
    xb = np.concatenate([bias, x], axis=1)
    weights = np.zeros(xb.shape[1])
    for _ in range(steps):
        prob = _sigmoid(xb @ weights)
        weights += lr * (xb.T @ (y - prob)) / len(y)
    return weights


def predict_logistic(weights: np.ndarray, x: np.ndarray) -> np.ndarray:
    bias = np.ones((len(x), 1))
    xb = np.concatenate([bias, x], axis=1)
    return _sigmoid(xb @ weights)


def fit_score(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    bias = np.ones((len(x), 1))
    xb = np.concatenate([bias, x], axis=1)
    ridge = 1e-3 * np.eye(xb.shape[1])
    return np.linalg.solve(xb.T @ xb + ridge, xb.T @ y)


def predict_score(weights: np.ndarray, x: np.ndarray) -> np.ndarray:
    bias = np.ones((len(x), 1))
    xb = np.concatenate([bias, x], axis=1)
    return np.clip(xb @ weights, 0.0, 1.0)


def brier(prob: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((prob - y) ** 2))


def log_loss(prob: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(prob, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def accuracy(prob: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((prob >= 0.5) == y))


def calibration_bins(prob: np.ndarray, y: np.ndarray, bins: int = 5) -> list[dict]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows = []
    for index in range(bins):
        if index == bins - 1:
            mask = (prob >= edges[index]) & (prob <= edges[index + 1])
        else:
            mask = (prob >= edges[index]) & (prob < edges[index + 1])
        count = int(mask.sum())
        if count == 0:
            continue
        rows.append(
            {
                "bin": index,
                "count": count,
                "mean_predicted": float(prob[mask].mean()),
                "observed_rate": float(y[mask].mean()),
            }
        )
    return rows


def mae(pred: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(np.abs(pred - y)))


def run_selection(parts: dict[str, list[QuizRow]]) -> dict:
    train = parts["train"]
    validation = parts["validation"]
    test = parts["test"]
    x_train, _score_train, y_train = apply_scale(train, train)
    x_val, score_val, y_val = apply_scale(validation, train)
    x_test, score_test, y_test = apply_scale(test, train)
    base_rate = float(np.mean(y_train))
    logistic = fit_logistic(x_train, y_train)
    val_model = predict_logistic(logistic, x_val)
    val_base = np.full(len(y_val), base_rate)
    selected = "logistic" if brier(val_model, y_val) <= brier(val_base, y_val) else "constant_train_rate"
    test_prob = predict_logistic(logistic, x_test) if selected == "logistic" else np.full(len(y_test), base_rate)
    score_weights = fit_score(x_train, _score_train)
    test_score = predict_score(score_weights, x_test)
    mean_score = float(np.mean(_score_train))
    return {
        "protocol": "c4-practice-quiz-pass-v1",
        "product_score_target": PRODUCT_SCORE_TARGET,
        "product_score_target_note": "Product rule, not an institutional pass mark.",
        "selected_on": "validation",
        "selected_pass_model": selected,
        "validation_brier_logistic": brier(val_model, y_val),
        "validation_brier_constant": brier(val_base, y_val),
        "test_accuracy": accuracy(test_prob, y_test),
        "test_brier": brier(test_prob, y_test),
        "test_log_loss": log_loss(test_prob, y_test),
        "test_calibration_bins": calibration_bins(test_prob, y_test),
        "test_score_mae": mae(test_score, score_test),
        "test_score_mae_mean_baseline": mae(np.full(len(score_test), mean_score), score_test),
        "train_learners": len({row.learner_id for row in train}),
        "validation_learners": len({row.learner_id for row in validation}),
        "test_learners": len({row.learner_id for row in test}),
        "activation_allowed": False,
        "activation_blocker": ACTIVATION_BLOCKER,
        "serves_students": False,
        "data": "synthetic_practice_bank_aligned",
        "note": (
            "Synthetic data cannot authorize this-quiz P(pass). "
            "activation_allowed stays false until learner-disjoint real submitted "
            "attempts exist. Do not replace c4-practice-quiz-estimate-v1."
        ),
    }


def finite_report(report: dict) -> None:
    for key in ("test_brier", "test_log_loss", "test_score_mae", "test_accuracy"):
        if not math.isfinite(report[key]):
            raise ValueError(f"{key} is not finite")
