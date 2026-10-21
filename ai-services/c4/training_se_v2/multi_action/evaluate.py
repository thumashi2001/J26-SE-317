"""Masked evaluation for se-path-multi-v1.

Selection reads validation return only. Return is the sum of rewards, not accuracy.
"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .baselines import random_valid, recent_performance, weakest_practice
from .contract import PROTOCOL, decode_action
from .gym_env import MultiActionGymEnv

METRIC_DEFINITIONS = {
    "return": "Sum of environment rewards over the episode. Not accuracy.",
    "activity_completion_count": "Steps whose action was inside the mask. Invalid steps are not completions.",
    "invalid_action_rate": "Invalid steps divided by episode steps. All-invalid masks terminate and count as invalid.",
    "mean_mastery_change": "Change in mean mastery on topics that are available at the end of the episode. Synthetic.",
}


def _mean_std(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"mean": 0.0, "std": 0.0}
    if len(vals) == 1:
        return {"mean": float(vals[0]), "std": 0.0}
    return {"mean": float(statistics.mean(vals)), "std": float(statistics.stdev(vals))}


def _policy_action(method: str, model: Any, obs: np.ndarray, mask: np.ndarray, info: dict, rng: np.random.Generator) -> int:
    if method == "maskable_ppo":
        action, _ = model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)
    if method == "random_valid":
        return random_valid(mask, rng)
    if method == "weakest_practice":
        return weakest_practice(info.get("mastery", np.zeros(46)), mask)
    if method == "recent_performance":
        return recent_performance(info.get("recent_by_topic", np.full(46, 0.5)), mask)
    raise ValueError(method)


def rollout(
    method: str,
    *,
    semester: str,
    episodes: int,
    seed_fn: Callable[[int], int],
    model: Any = None,
    rng_seed: int = 0,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(rng_seed)
    rows = []
    for ep in range(episodes):
        env = MultiActionGymEnv(semester=semester, seed=seed_fn(ep))
        obs, info = env.reset(seed=seed_fn(ep))
        total = 0.0
        steps = 0
        invalid = 0
        completed = 0
        start_mastery = None
        done = False
        while not done:
            mask = np.asarray(info["action_mask"], dtype=bool)
            if start_mastery is None and env.core.state is not None:
                avail = env.core.state.available > 0.5
                start_mastery = float(env.core.state.mastery[avail].mean()) if avail.any() else 0.0
            if not mask.any():
                invalid += 1
                steps += 1
                break
            action = _policy_action(method, model, obs, mask, info, rng)
            if not bool(mask[action]):
                invalid += 1
            else:
                completed += 1
                kind, _topic = decode_action(int(action))
                if kind == "coding":
                    raise RuntimeError("evaluation selected a coding action")
            obs, reward, terminated, truncated, info = env.step(int(action))
            total += float(reward)
            steps += 1
            done = bool(terminated or truncated)
        avail = env.core.state.available > 0.5 if env.core.state is not None else np.array([])
        end_mastery = float(env.core.state.mastery[avail].mean()) if getattr(avail, "any", lambda: False)() else 0.0
        rows.append(
            {
                "return": total,
                "activity_completion_count": completed,
                "invalid_action_rate": (invalid / steps) if steps else 0.0,
                "mean_mastery_change": end_mastery - float(start_mastery or 0.0),
                "synthetic": True,
            }
        )
        env.close()
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n_episodes": len(rows),
        "return": _mean_std([float(r["return"]) for r in rows]),
        "activity_completion_count": _mean_std([float(r["activity_completion_count"]) for r in rows]),
        "invalid_action_rate": _mean_std([float(r["invalid_action_rate"]) for r in rows]),
        "mean_mastery_change": _mean_std([float(r["mean_mastery_change"]) for r in rows]),
        "definitions": METRIC_DEFINITIONS,
        "protocol": PROTOCOL,
    }


def load_model(path: Path):
    from sb3_contrib import MaskablePPO

    model = MaskablePPO.load(str(path), device="cpu")
    if type(model).__name__ != "MaskablePPO":
        raise RuntimeError("checkpoint is not MaskablePPO")
    return model


def compare_validation(
    *,
    model_paths: dict[int, Path],
    seeds: tuple[int, ...] = (0, 1, 2),
    episodes: int = 20,
) -> dict[str, Any]:
    methods = ("maskable_ppo", "weakest_practice", "recent_performance", "random_valid")
    by_seed: dict[str, Any] = {}
    ppo_means: dict[int, float] = {}
    for seed in seeds:
        model = load_model(model_paths[seed])
        by_seed[str(seed)] = {}
        sem_means = []
        for semester in ("Y3S1", "Y3S2"):
            by_seed[str(seed)][semester] = {}
            for method in methods:
                rows = rollout(
                    method,
                    semester=semester,
                    episodes=episodes,
                    seed_fn=lambda ep, s=seed: 10_000 + s * 100 + ep,
                    model=model if method == "maskable_ppo" else None,
                    rng_seed=seed + 17,
                )
                summary = summarize(rows)
                by_seed[str(seed)][semester][method] = summary
            sem_means.append(by_seed[str(seed)][semester]["maskable_ppo"]["return"]["mean"])
        ppo_means[seed] = float(statistics.mean(sem_means))
    selected = sorted(ppo_means.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return {
        "protocol": PROTOCOL,
        "split": "validation",
        "test_used_for_selection": False,
        "seeds": list(seeds),
        "selected_seed": int(selected),
        "selection_rule": "highest mean of Y3S1 and Y3S2 validation return; ties use the lowest seed",
        "validation_return_by_seed": {str(k): v for k, v in ppo_means.items()},
        "by_seed": by_seed,
        "metric_definitions": METRIC_DEFINITIONS,
        "note": "return is not accuracy",
    }


def frozen_test(
    *,
    model_path: Path,
    seed: int,
    episodes: int = 20,
) -> dict[str, Any]:
    model = load_model(model_path)
    out: dict[str, Any] = {
        "protocol": PROTOCOL,
        "split": "final_test",
        "used_for_selection": False,
        "seed": int(seed),
        "semesters": {},
    }
    for semester in ("Y3S1", "Y3S2"):
        out["semesters"][semester] = {}
        for method in ("maskable_ppo", "weakest_practice", "recent_performance", "random_valid"):
            rows = rollout(
                method,
                semester=semester,
                episodes=episodes,
                seed_fn=lambda ep, s=seed: 20_000 + s * 100 + ep,
                model=model if method == "maskable_ppo" else None,
                rng_seed=seed + 91,
            )
            out["semesters"][semester][method] = summarize(rows)
    return out
