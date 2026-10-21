"""Separately named mask-aware RL experiment (sb3-contrib MaskablePPO).

Verified API (sb3-contrib MaskablePPO):
- Environment exposes ``action_masks()`` returning a boolean array (True = valid), OR
  wrap with ``ActionMasker``.
- Train with ``model.learn(..., use_masking=True)`` (default True).
- Evaluate / predict with ``model.predict(obs, action_masks=masks, deterministic=True)``.
- Use ``sb3_contrib.common.maskable.evaluation.evaluate_policy`` for masked eval helpers.

This is **not** inference-only remapping of invalid actions onto valid ones for vanilla PPO.
Vanilla DQN/PPO remain unmasked penalty-based comparators elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .baselines import rollout_policy
from .config import EnvConfig
from .environment import make_env
from .paths import ensure_dir
from .protocol import ENV_PROTOCOL_VERSION, val_episode_seed
from .simulator import Simulator


def maskable_ppo_available() -> bool:
    try:
        import sb3_contrib  # noqa: F401

        return True
    except ImportError:
        return False


def train_maskable_ppo(
    simulator: Simulator,
    env_config: EnvConfig,
    out_dir: Path,
    *,
    timesteps: int,
    seed: int,
    device: str,
    checkpoint_freq: int,
) -> Path:
    if not maskable_ppo_available():
        raise ImportError(
            "sb3-contrib is required for maskable_ppo. "
            "Install via requirements-training.txt (sb3-contrib)."
        )
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.monitor import Monitor

    ensure_dir(out_dir)
    # Env implements action_masks(); MaskablePPO uses them during learn when use_masking=True.
    env = Monitor(make_env(simulator, env_config, seed=seed, scenario="sim_train"))
    assert hasattr(env.unwrapped, "action_masks")
    model = MaskablePPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=min(256, max(64, timesteps // 4)),
        batch_size=64,
        n_epochs=5,
        gamma=0.99,
        verbose=0,
        seed=seed,
        device=device,
    )
    ckpt = CheckpointCallback(
        save_freq=max(1, checkpoint_freq),
        save_path=str(out_dir / "checkpoints"),
        name_prefix="maskable_ppo",
    )
    model.learn(total_timesteps=timesteps, callback=ckpt, use_masking=True)
    path = out_dir / "maskable_ppo_final.zip"
    model.save(str(path))
    env.close()
    from .provenance import write_json

    write_json(
        out_dir / "maskable_ppo_meta.json",
        {
            "algorithm": "maskable_ppo",
            "api": "sb3_contrib.MaskablePPO",
            "masking_train": True,
            "masking_eval_required": True,
            "env_protocol_version": ENV_PROTOCOL_VERSION,
            "not_inference_only_remap": True,
        },
    )
    return path


def rollout_maskable_ppo(
    model_path: Path,
    env,
    *,
    episodes: int,
    train_seed: int,
) -> list[dict]:
    from sb3_contrib import MaskablePPO

    model = MaskablePPO.load(str(model_path))

    class MaskedPolicy:
        uses_action_mask = True

        def predict(self, observation, action_mask=None):
            masks = action_mask if action_mask is not None else env.action_masks()
            action, _ = model.predict(observation, deterministic=True, action_masks=masks)
            return int(action)

        def reset_episode(self):
            return None

        def observe_transition(self, info):
            return None

    return rollout_policy(
        env,
        MaskedPolicy(),
        episodes=episodes,
        seed=0,
        seed_fn=lambda ep: val_episode_seed(train_seed, ep),
    )


def maskable_experiment_note() -> dict[str, Any]:
    return {
        "name": "maskable_ppo",
        "status": "implemented_opt_in",
        "dependency": "sb3-contrib",
        "train_masking": "MaskablePPO.learn(use_masking=True) + env.action_masks()",
        "eval_masking": "predict(..., action_masks=env.action_masks())",
        "not": "inference-only remapping for vanilla PPO/DQN",
    }
