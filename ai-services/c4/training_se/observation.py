"""Reusable observation construction for train-time and inference-time.

Layout (fixed, dim = 2*N + 4 = 28 for N=12)
-------------------------------------------
[ mastery_0 .. mastery_{N-1},
  avail_0   .. avail_{N-1},
  mean_mastery,          # mean over *available* topics only (0 if none)
  frac_mastered,         # fraction of available topics with mastery >= threshold
  elapsed_env_step_frac, # includes invalid-action transitions
  prior_strength ]

Missing mastery: avail_i = 0 and mastery_i = 0.
Genuine zero mastery: avail_i = 1 and mastery_i = 0.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .catalogue import N_TOPICS, ORDERED_TOPICS
from .config import SeEnvConfig

OBS_DIM = 2 * N_TOPICS + 4


def observation_schema(cfg: SeEnvConfig | None = None) -> dict[str, Any]:
    cfg = cfg or SeEnvConfig()
    names = (
        [f"mastery::{t}" for t in ORDERED_TOPICS]
        + [f"available::{t}" for t in ORDERED_TOPICS]
        + ["mean_mastery", "frac_mastered", "elapsed_env_step_frac", "prior_strength"]
    )
    return {
        "dim": OBS_DIM,
        "dtype": "float32",
        "range": [0.0, 1.0],
        "order": names,
        "n_topics": N_TOPICS,
        "mastery_slice": [0, N_TOPICS],
        "availability_slice": [N_TOPICS, 2 * N_TOPICS],
        "extras_slice": [2 * N_TOPICS, OBS_DIM],
        "missing_vs_zero": (
            "Unavailable topics use available=0 and mastery=0; "
            "available topics may have mastery=0 (genuine zero)."
        ),
        "mastery_threshold_for_frac": cfg.mastery_threshold,
    }


def build_observation(
    mastery: np.ndarray,
    available: np.ndarray,
    *,
    elapsed_env_steps: int,
    max_episode_steps: int,
    prior_strength: float,
    mastery_threshold: float,
) -> np.ndarray:
    mastery = np.asarray(mastery, dtype=np.float32).reshape(N_TOPICS)
    available = np.asarray(available, dtype=np.float32).reshape(N_TOPICS)
    if mastery.shape != (N_TOPICS,) or available.shape != (N_TOPICS,):
        raise ValueError(f"expected shape ({N_TOPICS},)")
    # Force mastery to 0 where unavailable so missing ≠ leak of latent values
    mastery = np.where(available > 0.5, mastery, 0.0).astype(np.float32)
    avail_bool = available > 0.5
    if avail_bool.any():
        mean_m = float(mastery[avail_bool].mean())
        frac_m = float((mastery[avail_bool] >= mastery_threshold).mean())
    else:
        mean_m = 0.0
        frac_m = 0.0
    step_frac = float(min(1.0, elapsed_env_steps / max(1, max_episode_steps)))
    extras = np.asarray(
        [mean_m, frac_m, step_frac, float(prior_strength)], dtype=np.float32
    )
    obs = np.concatenate([mastery, available.astype(np.float32), extras], axis=0)
    if obs.shape != (OBS_DIM,):
        raise RuntimeError(f"obs dim {obs.shape} != {OBS_DIM}")
    if not np.isfinite(obs).all():
        raise RuntimeError("non-finite observation")
    if (obs < 0.0).any() or (obs > 1.0).any():
        raise RuntimeError("observation out of [0,1] bounds")
    return obs


def mastery_from_obs(obs: np.ndarray) -> np.ndarray:
    return np.asarray(obs, dtype=np.float32)[:N_TOPICS]


def availability_from_obs(obs: np.ndarray) -> np.ndarray:
    return np.asarray(obs, dtype=np.float32)[N_TOPICS : 2 * N_TOPICS]
