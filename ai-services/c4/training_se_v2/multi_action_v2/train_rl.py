"""MaskablePPO for se-path-multi-v2. Masks are used in learn()."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contract import N_ACTIONS, OBS_DIM, observation_schema
from .gym_env import MultiActionGymEnvV2
from .objective import (
    PROTOCOL,
    SMOKE_TIMESTEPS,
    TRAINING_REVISION,
    TRAINING_SCHEDULE,
    coverage_complete,
)


def dependency_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in ("numpy", "gymnasium", "stable_baselines3", "sb3_contrib", "torch"):
        try:
            mod = __import__(name)
            out[name] = getattr(mod, "__version__", "unknown")
        except ImportError:
            out[name] = "missing"
    return out


def train_maskable_ppo(
    out_dir: Path,
    *,
    timesteps: int,
    seed: int,
    device: str = "cpu",
) -> dict[str, Any]:
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.monitor import Monitor

    out_dir.mkdir(parents=True, exist_ok=True)
    env = Monitor(
        MultiActionGymEnvV2(schedule_training=True, train_seed=int(seed), seed=int(seed))
    )
    assert hasattr(env.unwrapped, "action_masks")
    n_steps = min(256, max(64, int(timesteps) // 4))
    model = MaskablePPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=n_steps,
        batch_size=64,
        n_epochs=5,
        gamma=0.99,
        verbose=0,
        seed=seed,
        device=device,
    )
    before = int(env.unwrapped.mask_calls)
    model.learn(total_timesteps=int(timesteps), use_masking=True)
    if int(env.unwrapped.mask_calls) <= before:
        raise RuntimeError("learn() did not call action_masks()")
    path = out_dir / "maskable_ppo_final.zip"
    model.save(str(path))
    coverage = {
        name: {"episodes": int(counts["episodes"]), "steps": int(counts["steps"])}
        for name, counts in env.unwrapped.coverage.items()
    }
    env.close()
    if not coverage_complete(coverage):
        raise RuntimeError(f"seed {seed} did not train on both Y3S1 and Y3S2: {coverage}")
    record = {
        "protocol": PROTOCOL,
        "training_revision": TRAINING_REVISION,
        "training_schedule": TRAINING_SCHEDULE,
        "seed": int(seed),
        "semesters": coverage,
    }
    (out_dir / "training_coverage.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {
        "protocol": PROTOCOL,
        "training_revision": TRAINING_REVISION,
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "seed": int(seed),
        "requested_timesteps": int(timesteps),
        "actual_timesteps": int(getattr(model, "num_timesteps", timesteps)),
        "masks_in_training": True,
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "schema": observation_schema(),
        "checkpoint": path.name,
        "semester_coverage": coverage,
        "versions": dependency_versions(),
        "activation_allowed": False,
        "model": model,
        "smoke_budget": SMOKE_TIMESTEPS,
    }
