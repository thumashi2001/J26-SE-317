"""Learner-disjoint train/validation/test splits."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .contract import SplitFractions
from .rng_streams import split_rng


def split_learner_ids(
    learner_ids: list[str] | np.ndarray | pd.Series,
    *,
    master_seed: int,
    fractions: SplitFractions | None = None,
) -> dict[str, set[str]]:
    frac = fractions or SplitFractions()
    ids = np.array(sorted(set(str(x) for x in learner_ids)))
    if len(ids) < 3:
        raise ValueError(f"Need at least 3 learners to split; found {len(ids)}")
    rng = split_rng(master_seed)
    rng.shuffle(ids)

    n = len(ids)
    n_train = max(1, int(round(n * frac.train)))
    n_val = max(1, int(round(n * frac.validation)))
    if n_train + n_val >= n:
        n_train = max(1, n - 2)
        n_val = 1
    train_ids = set(ids[:n_train].tolist())
    val_ids = set(ids[n_train : n_train + n_val].tolist())
    test_ids = set(ids[n_train + n_val :].tolist())
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)
    return {"train": train_ids, "validation": val_ids, "test": test_ids}


def assign_split_column(
    df: pd.DataFrame,
    id_sets: dict[str, set[str]],
    id_col: str = "learner_id",
) -> pd.DataFrame:
    out = df.copy()
    inv = {}
    for split, ids in id_sets.items():
        for i in ids:
            inv[i] = split
    out["split"] = out[id_col].astype(str).map(inv)
    if out["split"].isna().any():
        raise RuntimeError("Some rows lack a split assignment")
    return out


def split_meta(id_sets: dict[str, set[str]], master_seed: int) -> dict[str, Any]:
    return {
        "master_seed": master_seed,
        "n_learners": {k: len(v) for k, v in id_sets.items()},
        "learner_ids": {k: sorted(v) for k, v in id_sets.items()},
        "disjoint": True,
    }
