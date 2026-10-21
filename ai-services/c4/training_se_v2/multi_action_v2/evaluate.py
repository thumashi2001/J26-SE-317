"""Validation and held-out evaluation for se-path-multi-v2.

Selection uses validation mean mastery change. The held-out function must not
be called while choosing hyperparameters.
"""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

import numpy as np

from .baselines import WeakestMulti, recent_performance, weakest_practice
from .contract import decode_action
from .gym_env import MultiActionGymEnvV2
from .objective import (
    COMPARISON_UNIT,
    COMPLETION_DEFINITION,
    NO_PROGRESS_DEFINITION,
    PRIMARY_DEFINITION,
    PRIMARY_METRIC,
    PROTOCOL,
    RETURN_DEFINITION,
    SELECTION_RULE,
    TEST_EPISODES,
    VAL_EPISODES,
    WEAKEST_TOPIC_DEFINITION,
    TEST_RANDOM_SEED,
    VAL_RANDOM_SEED,
    criterion_met,
    heldout_scenario_seed,
    val_scenario_seed,
)

METHODS = (
    "maskable_ppo",
    "weakest_practice",
    "recent_performance",
    "weakest_multi",
    "random_valid",
)


def _mean_std(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"mean": 0.0, "std": 0.0}
    if len(vals) == 1:
        return {"mean": float(vals[0]), "std": 0.0}
    return {"mean": float(statistics.mean(vals)), "std": float(statistics.stdev(vals))}


def load_model(path: Path):
    from sb3_contrib import MaskablePPO

    model = MaskablePPO.load(str(path), device="cpu")
    if type(model).__name__ != "MaskablePPO":
        raise RuntimeError("checkpoint is not MaskablePPO")
    return model


def _choose(method: str, model: Any, obs: np.ndarray, info: dict, rule: WeakestMulti, rng: np.random.Generator) -> int:
    mask = np.asarray(info["action_mask"], dtype=bool)
    mastery = info["mastery"]
    if method == "maskable_ppo":
        action, _ = model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)
    if method == "weakest_practice":
        return weakest_practice(mastery, mask)
    if method == "recent_performance":
        return recent_performance(info["recent_by_topic"], mask)
    if method == "weakest_multi":
        return rule.action(mastery, mask)
    if method == "random_valid":
        return int(rng.choice(np.flatnonzero(mask)))
    raise ValueError(method)


def rollout(method: str, *, semester: str, episodes: int, seed_fn, model: Any = None, rng_seed: int = 0) -> list[dict]:
    rng = np.random.default_rng(rng_seed)
    rows = []
    for episode in range(episodes):
        env = MultiActionGymEnvV2(semester=semester, seed=seed_fn(episode))
        obs, info = env.reset(seed=seed_fn(episode))
        rule = WeakestMulti()
        start = env.core.initial_mastery.copy()
        available = env.core.state.available.copy()
        total = 0.0
        learning = 0.0
        penalty = 0.0
        steps = 0
        invalid = 0
        zero_progress = 0
        kinds = {"practice": 0, "revision": 0, "quiz": 0, "coding": 0}
        done = False
        while not done:
            mask = np.asarray(info["action_mask"], dtype=bool)
            if not mask.any():
                invalid += 1
                steps += 1
                break
            action = _choose(method, model, obs, info, rule, rng)
            obs, reward, terminated, truncated, info = env.step(int(action))
            parts = info.get("components") or {}
            total += float(reward)
            learning += float(parts.get("learning_delta", 0.0))
            penalty += float(parts.get("invalid_penalty", 0.0))
            steps += 1
            if info.get("invalid"):
                invalid += 1
            else:
                kind, _topic = decode_action(int(action))
                kinds[kind] = kinds.get(kind, 0) + 1
                if abs(float(parts.get("learning_delta", 0.0))) < 1e-8:
                    zero_progress += 1
            done = bool(terminated or truncated)
        end = env.core.state.mastery
        eligible = np.flatnonzero(available > 0.5)
        weakest = int(eligible[np.argmin(start[eligible])])
        rows.append(
            {
                "return": total,
                "learning_delta_sum": learning,
                "invalid_penalty_sum": penalty,
                "correctness_bonus_sum": 0.0,
                "mean_mastery_change": float((end[eligible] - start[eligible]).mean()),
                "weakest_topic_progress": float(end[weakest] - start[weakest]),
                "invalid_action_rate": invalid / steps if steps else 0.0,
                "no_progress_rate": zero_progress / steps if steps else 0.0,
                "valid_steps": steps - invalid,
                "action_counts": kinds,
                "synthetic": True,
            }
        )
        env.close()
    return rows


def summarize(rows: list[dict]) -> dict[str, Any]:
    counts = {"practice": 0, "revision": 0, "quiz": 0, "coding": 0}
    for row in rows:
        for key, value in row["action_counts"].items():
            counts[key] = counts.get(key, 0) + int(value)
    return {
        "n_episodes": len(rows),
        "mean_mastery_change": _mean_std([float(r["mean_mastery_change"]) for r in rows]),
        "weakest_topic_progress": _mean_std([float(r["weakest_topic_progress"]) for r in rows]),
        "return": _mean_std([float(r["return"]) for r in rows]),
        "learning_delta_sum": _mean_std([float(r["learning_delta_sum"]) for r in rows]),
        "invalid_penalty_sum": _mean_std([float(r["invalid_penalty_sum"]) for r in rows]),
        "correctness_bonus_sum": _mean_std([0.0 for _ in rows]),
        "invalid_action_rate": _mean_std([float(r["invalid_action_rate"]) for r in rows]),
        "no_progress_rate": _mean_std([float(r["no_progress_rate"]) for r in rows]),
        "valid_steps": _mean_std([float(r["valid_steps"]) for r in rows]),
        "action_counts": counts,
        "definitions": {
            "primary": PRIMARY_DEFINITION,
            "weakest_topic": WEAKEST_TOPIC_DEFINITION,
            "return": RETURN_DEFINITION,
            "no_progress_rate": NO_PROGRESS_DEFINITION,
            "valid_steps": COMPLETION_DEFINITION,
            "comparison_unit": COMPARISON_UNIT,
        },
        "protocol": PROTOCOL,
        "primary_metric": PRIMARY_METRIC,
    }


def compare_validation(*, model_paths: dict[int, Path], seeds: tuple[int, ...] = (0, 1, 2), episodes: int = VAL_EPISODES) -> dict[str, Any]:
    by_seed: dict[str, Any] = {}
    scores: dict[int, float] = {}
    for seed in seeds:
        model = load_model(model_paths[seed])
        by_seed[str(seed)] = {}
        semester_scores = []
        for semester in ("Y3S1", "Y3S2"):
            by_seed[str(seed)][semester] = {}
            for method in METHODS:
                rows = rollout(
                    method,
                    semester=semester,
                    episodes=episodes,
                    seed_fn=lambda ep, sem=semester: val_scenario_seed(sem, ep),
                    model=model if method == "maskable_ppo" else None,
                    rng_seed=VAL_RANDOM_SEED,
                )
                by_seed[str(seed)][semester][method] = summarize(rows)
            semester_scores.append(by_seed[str(seed)][semester]["maskable_ppo"]["mean_mastery_change"]["mean"])
        scores[seed] = float(statistics.mean(semester_scores))
    selected = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]
    payload = {
        "protocol": PROTOCOL,
        "split": "validation",
        "test_used_for_selection": False,
        "seeds": list(seeds),
        "selected_seed": int(selected),
        "selection_rule": SELECTION_RULE,
        "selection_metric": PRIMARY_METRIC,
        "validation_primary_by_seed": {str(key): value for key, value in scores.items()},
        "by_seed": by_seed,
        "comparison_unit": COMPARISON_UNIT,
        "validation_bank": "Y3S1:81000+episode, Y3S2:82000+episode",
        "validation_bank_shared_across_seeds": True,
    }
    payload["criterion_met"] = criterion_met(payload)
    return payload


def frozen_test(*, model_path: Path, seed: int, episodes: int = TEST_EPISODES) -> dict[str, Any]:
    model = load_model(model_path)
    out: dict[str, Any] = {
        "protocol": PROTOCOL,
        "split": "held_out_simulator",
        "used_for_selection": False,
        "synthetic": True,
        "seed_stream": "common bank Y3S1 91000+episode, Y3S2 92000+episode",
        "not_the_v1_final_test": True,
        "seed": int(seed),
        "semesters": {},
    }
    for semester in ("Y3S1", "Y3S2"):
        out["semesters"][semester] = {}
        for method in METHODS:
            rows = rollout(
                method,
                semester=semester,
                episodes=episodes,
                seed_fn=lambda ep, sem=semester: heldout_scenario_seed(sem, ep),
                model=model if method == "maskable_ppo" else None,
                rng_seed=TEST_RANDOM_SEED,
            )
            out["semesters"][semester][method] = summarize(rows)
    return out
