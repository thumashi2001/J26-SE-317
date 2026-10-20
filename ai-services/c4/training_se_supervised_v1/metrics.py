"""Evaluation metrics (no invented accuracy thresholds)."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)


def classification_metrics(
    y_true: np.ndarray,
    p: np.ndarray,
    *,
    prob_threshold: float = 0.5,
) -> dict[str, Any]:
    """Report accuracy/log_loss/Brier/ROC-AUC.

    ``prob_threshold`` is the hard-class operating point on predicted probabilities
    and is independent of the synthetic exam-score cutoff used to define y_pass.
    """
    from .contract import CLASSIFICATION_PROB_THRESHOLD

    y_true = np.asarray(y_true).astype(int)
    p = np.clip(np.asarray(p).astype(float), 1e-6, 1.0 - 1e-6)
    thr = float(prob_threshold if prob_threshold is not None else CLASSIFICATION_PROB_THRESHOLD)
    y_hat = (p >= thr).astype(int)
    out: dict[str, Any] = {
        "n": int(len(y_true)),
        "prevalence": float(np.mean(y_true)),
        "pred_mean": float(np.mean(p)),
        "accuracy": float(np.mean(y_hat == y_true)),
        "classification_prob_threshold": thr,
        "log_loss": float(log_loss(y_true, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y_true, p)),
    }
    if len(np.unique(y_true)) > 1:
        out["roc_auc"] = float(roc_auc_score(y_true, p))
    else:
        out["roc_auc"] = None
        out["roc_auc_note"] = "undefined_single_class"
    return out


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    y_true = np.asarray(y_true).astype(float)
    y_pred = np.asarray(y_pred).astype(float)
    return {
        "n": int(len(y_true)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "y_mean": float(np.mean(y_true)),
        "y_std": float(np.std(y_true, ddof=1)) if len(y_true) > 1 else 0.0,
        "pred_mean": float(np.mean(y_pred)),
        "pred_std": float(np.std(y_pred, ddof=1)) if len(y_pred) > 1 else 0.0,
    }


def calibration_bins(
    y_true: np.ndarray,
    p: np.ndarray,
    *,
    n_bins: int = 10,
) -> list[dict[str, Any]]:
    """Reliability-style bins with sample counts (for plots / cards)."""
    y_true = np.asarray(y_true).astype(float)
    p = np.asarray(p).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows: list[dict[str, Any]] = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if i == n_bins - 1:
            mask = (p >= lo) & (p <= hi)
        else:
            mask = (p >= lo) & (p < hi)
        n = int(mask.sum())
        rows.append(
            {
                "bin": i,
                "p_lo": float(lo),
                "p_hi": float(hi),
                "n": n,
                "mean_pred": float(p[mask].mean()) if n else None,
                "mean_outcome": float(y_true[mask].mean()) if n else None,
            }
        )
    return rows
