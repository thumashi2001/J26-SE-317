"""Learner-level train/validation/test splits with chronology preserved."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .config import SplitConfig


def split_learners(
    interactions: pd.DataFrame,
    config: SplitConfig | None = None,
) -> dict[str, pd.DataFrame]:
    cfg = config or SplitConfig()
    cfg.validate()
    learners = np.array(sorted(interactions["user_id"].astype(str).unique()))
    rng = np.random.default_rng(cfg.seed)
    rng.shuffle(learners)

    n = len(learners)
    if n < 3:
        raise ValueError(f"Need at least 3 learners to split; found {n}")

    n_train = max(1, int(round(n * cfg.train_frac)))
    n_val = max(1, int(round(n * cfg.val_frac)))
    if n_train + n_val >= n:
        n_train = max(1, n - 2)
        n_val = 1
    n_test = n - n_train - n_val

    train_ids = set(learners[:n_train])
    val_ids = set(learners[n_train : n_train + n_val])
    test_ids = set(learners[n_train + n_val :])

    def subset(ids: Iterable[str]) -> pd.DataFrame:
        # Chronology already encoded by prior sort; keep mergesort-stable order.
        part = interactions[interactions["user_id"].astype(str).isin(ids)].copy()
        return part.sort_values(["user_id", "order_id"], kind="mergesort").reset_index(drop=True)

    splits = {
        "train": subset(train_ids),
        "validation": subset(val_ids),
        "test": subset(test_ids),
    }
    # Sanity: no learner overlap
    sets = {k: set(v["user_id"].astype(str)) for k, v in splits.items()}
    if sets["train"] & sets["validation"] or sets["train"] & sets["test"] or sets["validation"] & sets["test"]:
        raise RuntimeError("Learner leakage across splits detected")
    meta = {
        "seed": cfg.seed,
        "fractions": {
            "train": cfg.train_frac,
            "validation": cfg.val_frac,
            "test": cfg.test_frac,
        },
        "n_learners": {"train": len(train_ids), "validation": len(val_ids), "test": len(test_ids)},
        "n_interactions": {k: int(len(v)) for k, v in splits.items()},
        "actual_test_learners": n_test,
    }
    splits["_meta"] = meta  # type: ignore[assignment]
    return splits


def drop_meta(splits: dict) -> dict[str, pd.DataFrame]:
    return {k: v for k, v in splits.items() if k != "_meta"}
