"""Train DQN / PPO with Stable-Baselines3 and compare to baselines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .baselines import (
    COMPARISON_LABELS,
    COMPARISON_NOTES,
    RandomValidBaseline,
    RecentPerformanceBaseline,
    WeakestMasteryBaseline,
    rollout_policy,
)
from .config import EnvConfig, TrainConfig, config_to_dict, normalize_algorithm_key
from .environment import AdaptivePracticeEnv, make_env
from .paths import ensure_dir
from .protocol import (
    ENV_PROTOCOL_VERSION,
    assert_eval_seeds_disjoint,
    protocol_manifest,
    val_episode_seed,
)
from .provenance import utc_now, write_json
from .simulator import Simulator


def resolve_device(requested: str) -> str:
    if requested == "cpu":
        return "cpu"
    if requested == "cuda":
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:  # noqa: BLE001
            return "cpu"
    return "cpu"


def train_dqn(
    simulator: Simulator,
    env_config: EnvConfig,
    out_dir: Path,
    *,
    timesteps: int,
    seed: int,
    device: str,
    checkpoint_freq: int,
) -> Path:
    from stable_baselines3 import DQN
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.monitor import Monitor

    ensure_dir(out_dir)
    env = Monitor(make_env(simulator, env_config, seed=seed, scenario="sim_train"))
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=1e-3,
        buffer_size=50_000,
        learning_starts=min(1_000, max(100, timesteps // 10)),
        batch_size=64,
        gamma=0.99,
        train_freq=4,
        target_update_interval=250,
        verbose=0,
        seed=seed,
        device=device,
    )
    ckpt = CheckpointCallback(
        save_freq=max(1, checkpoint_freq),
        save_path=str(out_dir / "checkpoints"),
        name_prefix="dqn",
    )
    model.learn(total_timesteps=timesteps, callback=ckpt)
    path = out_dir / "dqn_final.zip"
    model.save(str(path))
    env.close()
    return path


def train_ppo(
    simulator: Simulator,
    env_config: EnvConfig,
    out_dir: Path,
    *,
    timesteps: int,
    seed: int,
    device: str,
    checkpoint_freq: int,
) -> Path:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.monitor import Monitor

    ensure_dir(out_dir)
    env = Monitor(make_env(simulator, env_config, seed=seed, scenario="sim_train"))
    model = PPO(
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
        name_prefix="ppo",
    )
    model.learn(total_timesteps=timesteps, callback=ckpt)
    path = out_dir / "ppo_final.zip"
    model.save(str(path))
    env.close()
    return path


def _sb3_rollouts(
    model_path: Path,
    env: AdaptivePracticeEnv,
    episodes: int,
    train_seed: int,
) -> list[dict]:
    from stable_baselines3 import DQN, PPO

    name = model_path.name.lower()
    if "maskable" in name:
        from .maskable_rl import rollout_maskable_ppo

        return rollout_maskable_ppo(model_path, env, episodes=episodes, train_seed=train_seed)
    if "ppo" in name:
        model = PPO.load(str(model_path))
    else:
        model = DQN.load(str(model_path))

    class Wrap:
        def predict(self, observation, action_mask=None):
            # Unmasked comparator: do not remap invalid actions.
            action, _ = model.predict(observation, deterministic=True)
            return int(action)

        def reset_episode(self):
            return None

        def observe_transition(self, info):
            return None

    return rollout_policy(
        env,
        Wrap(),
        episodes=episodes,
        seed=0,
        seed_fn=lambda ep: val_episode_seed(train_seed, ep),
    )


def summarise(rollouts: list[dict]) -> dict[str, Any]:
    if not rollouts:
        return {}
    keys = [
        "return",
        "valid_practice_count",
        "selected_skill_mastery_gain_sum",
        "mean_mastery_delta_final_minus_initial",
        "total_mastery_delta_final_minus_initial",
        "path_efficiency",
        "time_cost_proxy_steps",
        "invalid_action_rate",
    ]
    out: dict[str, Any] = {"n_episodes": len(rollouts), "env_protocol_version": ENV_PROTOCOL_VERSION}
    for k in keys:
        vals = np.asarray([r[k] for r in rollouts], dtype=float)
        out[k] = {
            "mean": float(vals.mean()),
            "std": float(vals.std(ddof=0)),
            "min": float(vals.min()),
            "max": float(vals.max()),
        }
    # Legacy key for older readers of JSON (same as selected-skill sum).
    out["mastery_gain_sum"] = out["selected_skill_mastery_gain_sum"]
    out["mean_mastery_delta"] = out["mean_mastery_delta_final_minus_initial"]
    return out


def run_training_comparison(
    simulator: Simulator,
    env_config: EnvConfig,
    train_config: TrainConfig,
    output_root: Path,
    *,
    scenario_train: str = "sim_train",
    scenario_val: str = "sim_val",
) -> dict[str, Any]:
    cfg = train_config.resolved()
    device = resolve_device(cfg.device)
    assert_eval_seeds_disjoint(cfg.seeds, cfg.eval_episodes)

    # New folder only — never overwrite historical train_* outputs.
    run_dir = ensure_dir(
        output_root / f"train_{cfg.mode}_{ENV_PROTOCOL_VERSION}_{utc_now().replace(':', '').replace('-', '')}"
    )
    write_json(
        run_dir / "train_config.json",
        {
            "train": config_to_dict(cfg),
            "env": config_to_dict(env_config),
            "device_resolved": device,
            "created_at_utc": utc_now(),
            "versions": _versions(),
            "env_protocol_version": ENV_PROTOCOL_VERSION,
            "protocol": protocol_manifest(),
            "comparison_labels": {k: COMPARISON_LABELS.get(k, k) for k in cfg.algorithms},
            "comparison_notes": COMPARISON_NOTES,
            "rewards_penalties_unchanged": True,
            "invalid_action_policy": "penalty_no_remap",
            "scenario_note": (
                "scenario_train/val names select prior_strength presets only; "
                "they are not held-out real-learner partitions."
            ),
            "scenarios": {"train": scenario_train, "validation": scenario_val},
        },
    )

    all_results: dict[str, Any] = {
        "seeds": {},
        "device": device,
        "mode": cfg.mode,
        "env_protocol_version": ENV_PROTOCOL_VERSION,
        "comparison_labels": {k: COMPARISON_LABELS.get(k, k) for k in cfg.algorithms},
        "comparison_notes": COMPARISON_NOTES,
        "protocol": protocol_manifest(),
    }
    for seed in cfg.seeds:
        seed_dir = ensure_dir(run_dir / f"seed_{seed}")
        seed_metrics: dict[str, Any] = {}

        if "dqn" in cfg.algorithms:
            dqn_path = train_dqn(
                simulator,
                env_config,
                seed_dir / "dqn",
                timesteps=cfg.timesteps,
                seed=seed,
                device=device,
                checkpoint_freq=cfg.checkpoint_freq,
            )
            env = make_env(simulator, env_config, scenario=scenario_val, seed=seed)
            rolls = _sb3_rollouts(dqn_path, env, cfg.eval_episodes, seed)
            seed_metrics["dqn"] = {
                "label": COMPARISON_LABELS["dqn"],
                "uses_action_mask": False,
                "path": str(dqn_path),
                "val": summarise(rolls),
                "episodes": rolls,
                "eval_split": "validation_only",
            }

        if "ppo" in cfg.algorithms:
            ppo_device = device if cfg.device == "cuda" else "cpu"
            ppo_path = train_ppo(
                simulator,
                env_config,
                seed_dir / "ppo",
                timesteps=cfg.timesteps,
                seed=seed,
                device=ppo_device,
                checkpoint_freq=cfg.checkpoint_freq,
            )
            env = make_env(simulator, env_config, scenario=scenario_val, seed=seed)
            rolls = _sb3_rollouts(ppo_path, env, cfg.eval_episodes, seed)
            seed_metrics["ppo"] = {
                "label": COMPARISON_LABELS["ppo"],
                "uses_action_mask": False,
                "path": str(ppo_path),
                "val": summarise(rolls),
                "episodes": rolls,
                "eval_split": "validation_only",
            }

        if "maskable_ppo" in cfg.algorithms:
            from .maskable_rl import train_maskable_ppo

            mp_device = device if cfg.device == "cuda" else "cpu"
            mp_path = train_maskable_ppo(
                simulator,
                env_config,
                seed_dir / "maskable_ppo",
                timesteps=cfg.timesteps,
                seed=seed,
                device=mp_device,
                checkpoint_freq=cfg.checkpoint_freq,
            )
            env = make_env(simulator, env_config, scenario=scenario_val, seed=seed)
            rolls = _sb3_rollouts(mp_path, env, cfg.eval_episodes, seed)
            seed_metrics["maskable_ppo"] = {
                "label": COMPARISON_LABELS["maskable_ppo"],
                "uses_action_mask": True,
                "masking_train_and_eval": True,
                "path": str(mp_path),
                "val": summarise(rolls),
                "episodes": rolls,
                "eval_split": "validation_only",
            }

        if "weakest_mastery" in cfg.algorithms:
            env = make_env(simulator, env_config, scenario=scenario_val, seed=seed)
            policy = WeakestMasteryBaseline(simulator.n_skills)
            rolls = rollout_policy(
                env,
                policy,
                episodes=cfg.eval_episodes,
                seed=0,
                seed_fn=lambda ep, s=seed: val_episode_seed(s, ep),
            )
            seed_metrics["weakest_mastery"] = {
                "label": COMPARISON_LABELS["weakest_mastery"],
                "uses_action_mask": True,
                "val": summarise(rolls),
                "episodes": rolls,
                "eval_split": "validation_only",
            }

        if "random_valid" in cfg.algorithms:
            env = make_env(simulator, env_config, scenario=scenario_val, seed=seed)
            policy = RandomValidBaseline(seed=seed + 300)
            rolls = rollout_policy(
                env,
                policy,
                episodes=cfg.eval_episodes,
                seed=0,
                seed_fn=lambda ep, s=seed: val_episode_seed(s, ep),
            )
            seed_metrics["random_valid"] = {
                "label": COMPARISON_LABELS["random_valid"],
                "uses_action_mask": True,
                "policy_seed": seed + 300,
                "val": summarise(rolls),
                "episodes": rolls,
                "eval_split": "validation_only",
            }

        if "recent_performance" in cfg.algorithms:
            env = make_env(simulator, env_config, scenario=scenario_val, seed=seed)
            policy = RecentPerformanceBaseline(simulator.n_skills)
            rolls = rollout_policy(
                env,
                policy,
                episodes=cfg.eval_episodes,
                seed=0,
                seed_fn=lambda ep, s=seed: val_episode_seed(s, ep),
            )
            seed_metrics["recent_performance"] = {
                "label": COMPARISON_LABELS["recent_performance"],
                "uses_action_mask": True,
                "val": summarise(rolls),
                "episodes": rolls,
                "eval_split": "validation_only",
                "note": COMPARISON_NOTES["recent_performance_defined"],
            }

        write_json(seed_dir / "val_metrics.json", seed_metrics)
        all_results["seeds"][str(seed)] = seed_metrics

    write_json(run_dir / "comparison_val.json", all_results)
    selection = select_policy_from_val(all_results)
    write_json(run_dir / "selection_val.json", selection)
    all_results["selection"] = selection
    all_results["run_dir"] = str(run_dir)
    return all_results


def select_policy_from_val(all_results: dict[str, Any]) -> dict[str, Any]:
    scores: dict[str, list[float]] = {}
    for _seed, methods in all_results.get("seeds", {}).items():
        for name, payload in methods.items():
            key = normalize_algorithm_key(name)
            mean_r = payload.get("val", {}).get("return", {}).get("mean")
            if mean_r is None:
                continue
            scores.setdefault(key, []).append(float(mean_r))
    if not scores:
        return {"selected": None, "reason": "no_validation_scores"}
    summary = {k: float(np.mean(v)) for k, v in scores.items()}
    best = max(summary, key=summary.get)
    return {
        "selected": best,
        "selected_label": COMPARISON_LABELS.get(best, best),
        "mean_val_return_by_algorithm": summary,
        "comparison_notes": COMPARISON_NOTES,
        "env_protocol_version": ENV_PROTOCOL_VERSION,
        "note": "Selection uses validation only; do not tune on final test.",
    }


def _versions() -> dict[str, str]:
    out = {}
    for name in ("numpy", "pandas", "sklearn", "gymnasium", "torch", "stable_baselines3", "sb3_contrib"):
        try:
            mod = __import__(name if name != "sklearn" else "sklearn")
            out[name] = getattr(mod, "__version__", "unknown")
        except Exception:  # noqa: BLE001
            out[name] = "not_installed"
    return out


def resume_instructions(checkpoint_dir: Path) -> str:
    return (
        "Resume example (DQN):\n"
        "  from stable_baselines3 import DQN\n"
        f"  model = DQN.load(r'{checkpoint_dir / 'dqn_XXXXX_steps.zip'}')\n"
        "  model.set_env(env)\n"
        "  model.learn(total_timesteps=additional_steps, reset_num_timesteps=False)\n"
        "MaskablePPO: from sb3_contrib import MaskablePPO; learn(..., use_masking=True).\n"
        "Same pattern for vanilla PPO with PPO.load(...)."
    )
