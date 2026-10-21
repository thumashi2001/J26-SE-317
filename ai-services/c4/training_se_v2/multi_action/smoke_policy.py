"""Tiny masked linear policy for local smoke only. Not the full MaskablePPO run."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .contract import N_ACTIONS, OBS_DIM, PROTOCOL, observation_schema
from .environment import MultiActionSimEnv


def train_smoke(out_dir: Path, *, episodes: int = 2, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    weights = rng.normal(0.0, 0.01, size=(N_ACTIONS, OBS_DIM)).astype(np.float32)
    env = MultiActionSimEnv(semester="Y3S1", seed=seed)
    returns = []
    for _ep in range(episodes):
        obs = env.reset()
        done = False
        total = 0.0
        while not done:
            mask = env.mask()
            scores = weights @ obs
            scores = np.where(mask, scores, -1e9)
            action = int(np.argmax(scores))
            prev = obs
            obs, reward, done, _info = env.step(action)
            weights[action] += (0.05 * reward * prev).astype(np.float32)
            total += reward
        returns.append(total)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(out_dir / "policy_smoke.npz", weights=weights)
    manifest = {
        "protocol": PROTOCOL,
        "training_mode": "smoke",
        "algorithm": "masked_linear_reinforce_smoke",
        "activation_allowed": False,
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "schema": observation_schema(),
        "episodes": episodes,
        "seed": seed,
        "mean_return": float(np.mean(returns)),
        "note": "Smoke artifact. Do not activate in the student app. Full run is MaskablePPO in Colab.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_and_predict(out_dir: Path, obs: np.ndarray, mask: np.ndarray) -> int:
    blob = np.load(out_dir / "policy_smoke.npz")
    weights = blob["weights"]
    if weights.shape != (N_ACTIONS, OBS_DIM):
        raise RuntimeError(f"weight shape {weights.shape}")
    if obs.shape != (OBS_DIM,) or mask.shape != (N_ACTIONS,):
        raise RuntimeError("obs/mask shape mismatch")
    if not mask.any():
        raise RuntimeError("no eligible actions")
    scores = weights @ obs.astype(np.float32)
    scores = np.where(mask, scores, -1e9)
    return int(np.argmax(scores))
