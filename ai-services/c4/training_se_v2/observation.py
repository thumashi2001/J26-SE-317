"""Observation construction for se-path-sim-v2 (dim = 2*N + 4 = 96 for N=46).

Layout
------
[ mastery_0 .. mastery_{N-1},
  avail_0   .. avail_{N-1},
  mean_mastery,
  frac_mastered,
  elapsed_env_step_frac,
  episode_init_mean_mastery ]   # OBSERVABLE freeze — replaces v1 prior_strength latent

Do not load se-path-sim-v1 weights with this schema.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from training_se_v1.catalogue import N_TOPICS, ORDERED_TOPICS
from training_se_v1.config import SeEnvConfig

OBS_DIM = 2 * N_TOPICS + 4  # 96
PROTOCOL = "se-path-sim-v2"


def observation_schema(cfg: SeEnvConfig | None = None) -> dict[str, Any]:
    cfg = cfg or SeEnvConfig()
    extras_names = [
        "mean_mastery",
        "frac_mastered",
        "elapsed_env_step_frac",
        "episode_init_mean_mastery",
    ]
    names = (
        [f"mastery::{t}" for t in ORDERED_TOPICS]
        + [f"available::{t}" for t in ORDERED_TOPICS]
        + extras_names
    )
    return {
        "protocol": PROTOCOL,
        "dim": OBS_DIM,
        "dtype": "float32",
        "range": [0.0, 1.0],
        "order": names,
        "extras_names": extras_names,
        "n_topics": N_TOPICS,
        "n_actions": N_TOPICS,
        "mastery_slice": [0, N_TOPICS],
        "availability_slice": [N_TOPICS, 2 * N_TOPICS],
        "extras_slice": [2 * N_TOPICS, OBS_DIM],
        "replaces_v1_slot": {
            "v1": "prior_strength",
            "v2": "episode_init_mean_mastery",
            "note": "New weights required; do not reshape v1 observations under v2 schema.",
        },
        "missing_vs_zero": (
            "Unavailable topics use available=0 and mastery=0; "
            "available topics may have mastery=0 (genuine zero)."
        ),
        "mastery_threshold_for_frac": cfg.mastery_threshold,
        "step_semantics": (
            "elapsed_env_step_frac = practice_attempts / max_episode_steps; "
            "one attempt per step; Mark done never counted."
        ),
    }


def build_observation(
    mastery: np.ndarray,
    available: np.ndarray,
    *,
    elapsed_env_steps: int,
    max_episode_steps: int,
    episode_init_mean_mastery: float,
    mastery_threshold: float,
) -> np.ndarray:
    mastery = np.asarray(mastery, dtype=np.float32).reshape(N_TOPICS)
    available = np.asarray(available, dtype=np.float32).reshape(N_TOPICS)
    mastery = np.where(available > 0.5, mastery, 0.0).astype(np.float32)
    avail_bool = available > 0.5
    if avail_bool.any():
        mean_m = float(mastery[avail_bool].mean())
        frac_m = float((mastery[avail_bool] >= mastery_threshold).mean())
    else:
        mean_m = 0.0
        frac_m = 0.0
    step_frac = float(min(1.0, elapsed_env_steps / max(1, max_episode_steps)))
    init_mean = float(np.clip(episode_init_mean_mastery, 0.0, 1.0))
    extras = np.asarray(
        [mean_m, frac_m, step_frac, init_mean], dtype=np.float32
    )
    obs = np.concatenate([mastery, available.astype(np.float32), extras], axis=0)
    if obs.shape != (OBS_DIM,):
        raise RuntimeError(f"obs dim {obs.shape} != {OBS_DIM}")
    if not np.isfinite(obs).all():
        raise RuntimeError("non-finite observation")
    return obs
