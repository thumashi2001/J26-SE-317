"""Validation-only diagnostic rollouts for existing checkpoints.

Never treat these outputs as final-test evaluation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .environment import AdaptivePracticeEnv, make_env
from .paths import ensure_dir
from .protocol import ENV_PROTOCOL_VERSION, diag_episode_seed, protocol_manifest
from .provenance import utc_now, write_json
from .simulator import Simulator


def _load_sb3(model_path: Path):
    from stable_baselines3 import DQN, PPO

    name = model_path.name.lower()
    parent = str(model_path.parent).lower()
    if "maskable" in name or "maskable" in parent:
        from sb3_contrib import MaskablePPO

        return MaskablePPO.load(str(model_path)), "maskable_ppo"
    if "ppo" in name:
        return PPO.load(str(model_path)), "ppo"
    return DQN.load(str(model_path)), "dqn"


def diagnostic_rollout(
    env: AdaptivePracticeEnv,
    *,
    model_path: str | Path | None = None,
    policy=None,
    train_seed: int = 0,
    episodes: int = 3,
    deterministic: bool = True,
    use_action_masks_for_predict: bool = False,
) -> dict[str, Any]:
    """
    Step-level diagnostic trace.

    Labels output as validation-only. Does not write into final-test metrics.
    """
    model = None
    algo = None
    if policy is None:
        if model_path is None:
            raise ValueError("Provide model_path or policy")
        model, algo = _load_sb3(Path(model_path))
    traces = []
    for ep in range(episodes):
        ep_seed = diag_episode_seed(train_seed, ep)
        obs, info = env.reset(seed=ep_seed)
        steps = []
        consecutive_invalid = 0
        done = False
        while not done:
            mask = info.get("action_mask")
            if policy is not None:
                action = int(policy.predict(obs, mask))
            else:
                assert model is not None
                if use_action_masks_for_predict and hasattr(env, "action_masks"):
                    action, _ = model.predict(
                        obs, deterministic=deterministic, action_masks=env.action_masks()
                    )
                else:
                    # Vanilla comparator path: no mask at predict-time.
                    action, _ = model.predict(obs, deterministic=deterministic)
                action = int(action)
            valid = bool(mask[action]) if mask is not None and 0 <= action < len(mask) else False
            obs, reward, terminated, truncated, info = env.step(action)
            if info.get("invalid_action"):
                consecutive_invalid += 1
            else:
                consecutive_invalid = 0
            steps.append(
                {
                    "t": int(info.get("elapsed_env_steps", len(steps) + 1)),
                    "action": action,
                    "action_label": info.get("action_label"),
                    "valid": (not bool(info.get("invalid_action"))),
                    "mask_said_valid": valid,
                    "consecutive_invalid": consecutive_invalid,
                    "elapsed_env_steps": info.get("elapsed_env_steps"),
                    "learner_interaction_count": info.get("learner_interaction_count"),
                    "reward": float(reward),
                    "terminated": bool(terminated),
                    "truncated": bool(truncated),
                    "selected_skill_mastery_gain": info.get("selected_skill_mastery_gain"),
                }
            )
            done = terminated or truncated
        traces.append(
            {
                "episode": ep,
                "episode_seed": ep_seed,
                "n_steps": len(steps),
                "invalid_action_rate": float(np.mean([not s["valid"] for s in steps])) if steps else 0.0,
                "steps": steps,
            }
        )
    return {
        "purpose": "validation_diagnostics_only",
        "not_final_test_evaluation": True,
        "env_protocol_version": ENV_PROTOCOL_VERSION,
        "algorithm": algo,
        "model_path": str(model_path) if model_path else None,
        "use_action_masks_for_predict": use_action_masks_for_predict,
        "created_at_utc": utc_now(),
        "protocol": protocol_manifest(),
        "episodes": traces,
    }


def run_checkpoint_diagnostics(
    simulator: Simulator,
    env_config,
    model_path: str | Path,
    out_json: str | Path,
    *,
    train_seed: int = 0,
    episodes: int = 3,
    scenario: str = "sim_val",
    use_action_masks_for_predict: bool = False,
) -> Path:
    env = make_env(simulator, env_config, scenario=scenario, seed=train_seed)
    report = diagnostic_rollout(
        env,
        model_path=model_path,
        train_seed=train_seed,
        episodes=episodes,
        use_action_masks_for_predict=use_action_masks_for_predict,
    )
    path = Path(out_json)
    ensure_dir(path.parent)
    write_json(path, report)
    return path
