"""Final evaluation on reserved test scenarios + sensitivity checks."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from .baselines import (
    COMPARISON_LABELS,
    RandomValidBaseline,
    RecentPerformanceBaseline,
    WeakestMasteryBaseline,
    rollout_policy,
)
from .config import EnvConfig, normalize_algorithm_key
from .environment import make_env
from .paths import ensure_dir
from .protocol import ENV_PROTOCOL_VERSION, final_test_episode_seed, protocol_manifest
from .provenance import write_json
from .simulator import Simulator
from .train_rl import summarise


def evaluate_on_test(
    simulator: Simulator,
    env_config: EnvConfig,
    *,
    selected_algorithm: str,
    model_path: str | Path | None,
    episodes: int,
    seed: int,
    scenario: str = "sim_test",
) -> dict[str, Any]:
    """
    Final-test evaluation only. Uses TEST episode seed band (disjoint from validation).
    Do not use diagnostics seeds here.
    """
    algo = normalize_algorithm_key(selected_algorithm)
    env = make_env(simulator, env_config, scenario=scenario, seed=seed)
    seed_fn = lambda ep: final_test_episode_seed(seed, ep)

    if algo == "weakest_mastery":
        policy: Any = WeakestMasteryBaseline(simulator.n_skills)
        rolls = rollout_policy(env, policy, episodes=episodes, seed=0, seed_fn=seed_fn)
    elif algo == "random_valid":
        policy = RandomValidBaseline(seed=seed + 300)
        rolls = rollout_policy(env, policy, episodes=episodes, seed=0, seed_fn=seed_fn)
    elif algo == "recent_performance":
        policy = RecentPerformanceBaseline(simulator.n_skills)
        rolls = rollout_policy(env, policy, episodes=episodes, seed=0, seed_fn=seed_fn)
    elif algo == "maskable_ppo":
        from .maskable_rl import rollout_maskable_ppo

        path = Path(model_path) if model_path else None
        if path is None or not path.exists():
            raise FileNotFoundError(f"maskable_ppo model missing: {model_path}")
        # Reuse val helper but with test seeds via temporary override — call predict loop here.
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(path))

        class Masked:
            def predict(self, observation, action_mask=None):
                masks = action_mask if action_mask is not None else env.action_masks()
                action, _ = model.predict(observation, deterministic=True, action_masks=masks)
                return int(action)

            def reset_episode(self):
                return None

            def observe_transition(self, info):
                return None

        rolls = rollout_policy(env, Masked(), episodes=episodes, seed=0, seed_fn=seed_fn)
    else:
        from stable_baselines3 import DQN, PPO

        path = Path(model_path) if model_path else None
        if path is None or not path.exists():
            raise FileNotFoundError(
                f"Model path required for {algo}: {model_path}\n"
                "Run notebook 03 first and pass the selected checkpoint."
            )
        try:
            model = PPO.load(str(path))
        except Exception:  # noqa: BLE001
            model = DQN.load(str(path))

        class Wrap:
            def predict(self, observation, action_mask=None):
                action, _ = model.predict(observation, deterministic=True)
                return int(action)

            def reset_episode(self):
                return None

            def observe_transition(self, info):
                return None

        rolls = rollout_policy(env, Wrap(), episodes=episodes, seed=0, seed_fn=seed_fn)

    return {
        "scenario": scenario,
        "algorithm": algo,
        "label": COMPARISON_LABELS.get(algo, algo),
        "eval_split": "final_test",
        "env_protocol_version": ENV_PROTOCOL_VERSION,
        "protocol": protocol_manifest(),
        "summary": summarise(rolls),
        "episodes": rolls,
        "disclaimer": (
            "Test metrics are from the simulator + ASSISTments-fitted response model. "
            "They are not evidence of SLIIT SE learning gains. "
            "Scenario names only set prior_strength presets, not held-out real learners."
        ),
    }


def sensitivity_to_assumptions(
    simulator: Simulator,
    base_env: EnvConfig,
    *,
    policy_name: str,
    model_path: str | Path | None,
    episodes: int,
    seed: int,
) -> dict[str, Any]:
    variants = {
        "base": base_env,
        "low_gain": replace(
            base_env,
            assumed_mastery_gain_correct=base_env.assumed_mastery_gain_correct * 0.5,
            assumed_mastery_gain_incorrect=base_env.assumed_mastery_gain_incorrect * 0.5,
        ),
        "high_gain": replace(
            base_env,
            assumed_mastery_gain_correct=base_env.assumed_mastery_gain_correct * 1.5,
            assumed_mastery_gain_incorrect=base_env.assumed_mastery_gain_incorrect * 1.5,
        ),
        "no_forgetting": replace(base_env, assumed_forgetting_per_step=0.0),
    }
    out = {}
    for name, cfg in variants.items():
        sim = Simulator(
            response_model=simulator.response_model,
            skill_list=simulator.skill_list,
            env_config=cfg,
            parent_real_checksum=simulator.parent_real_checksum,
        )
        out[name] = evaluate_on_test(
            sim,
            cfg,
            selected_algorithm=policy_name,
            model_path=model_path,
            episodes=episodes,
            seed=seed,
            scenario=f"sensitivity_{name}",
        )["summary"]
    return {
        "variants": out,
        "env_protocol_version": ENV_PROTOCOL_VERSION,
        "note": "Sensitivity explores simulator assumptions; not real SE A/B effects.",
    }


def aggregate_seed_variability(seed_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    if not seed_summaries:
        return {}
    keys = [
        "return",
        "selected_skill_mastery_gain_sum",
        "mean_mastery_delta_final_minus_initial",
        "total_mastery_delta_final_minus_initial",
        "path_efficiency",
        "invalid_action_rate",
    ]
    agg = {}
    for k in keys:
        means = [s.get(k, {}).get("mean") for s in seed_summaries if s.get(k)]
        means = [m for m in means if m is not None]
        if not means:
            continue
        arr = np.asarray(means, dtype=float)
        agg[k] = {"across_seed_mean": float(arr.mean()), "across_seed_std": float(arr.std(ddof=0))}
    return agg


def save_evaluation(report: dict[str, Any], path: Path) -> Path:
    ensure_dir(path.parent)
    write_json(path, report)
    return path
