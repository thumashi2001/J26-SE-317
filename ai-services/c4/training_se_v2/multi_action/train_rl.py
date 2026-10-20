"""MaskablePPO trainer for se-path-multi-v1.

learn(..., use_masking=True) reads env.action_masks() on every rollout step.
This module does not write activation_allowed=true.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract import N_ACTIONS, OBS_DIM, PROTOCOL, observation_schema
from .gym_env import MultiActionGymEnv

FULL_TIMESTEPS = 80_000
FULL_SEEDS = (0, 1, 2)
# Local parity only. Not a product policy and not a full run.
PARITY_TIMESTEPS = 128


def maskable_ppo_available() -> bool:
    try:
        import sb3_contrib  # noqa: F401

        return True
    except ImportError:
        return False


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
    semester: str = "Y3S1",
    device: str = "cpu",
) -> dict[str, Any]:
    if not maskable_ppo_available():
        raise ImportError("sb3-contrib required for MaskablePPO")
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.monitor import Monitor

    out_dir.mkdir(parents=True, exist_ok=True)
    env = Monitor(MultiActionGymEnv(semester=semester, seed=seed))
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
    if type(model).__name__ != "MaskablePPO":
        raise RuntimeError(f"expected MaskablePPO, got {type(model).__name__}")
    before = int(getattr(env.unwrapped, "mask_calls", 0))
    model.learn(total_timesteps=int(timesteps), use_masking=True)
    after = int(getattr(env.unwrapped, "mask_calls", 0))
    if after <= before:
        raise RuntimeError("MaskablePPO.learn did not call env.action_masks(); use_masking was not applied")
    path = out_dir / "maskable_ppo_final.zip"
    model.save(str(path))
    actual = int(getattr(model, "num_timesteps", timesteps))
    env.close()
    meta = {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "policy": "MlpPolicy",
        "seed": int(seed),
        "semester_reset": semester,
        "requested_timesteps": int(timesteps),
        "actual_timesteps": actual,
        "n_steps": n_steps,
        "device": device,
        "masks_in_training": True,
        "use_masking": True,
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "schema": observation_schema(),
        "checkpoint": path.name,
        "versions": dependency_versions(),
        "activation_allowed": False,
        "note": "Native MaskablePPO zip. Not a linear weight matrix. Not activated by this function.",
    }
    return {"meta": meta, "model": model, "checkpoint": path}
