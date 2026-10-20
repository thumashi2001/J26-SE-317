"""Validation comparison and optional final-test evaluation (se-path-sim-v0)."""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .baselines import (
    COMPARISON_LABELS,
    RandomValidBaseline,
    RecentPerformanceBaseline,
    WeakestStoredMasteryV1SimBaseline,
    rollout_policy,
)
from .config import SeEnvConfig
from .environment import make_env
from .protocol import (
    PROTOCOL_VERSION,
    assert_eval_seeds_disjoint,
    baseline_rng_seed,
    final_test_episode_seed,
    val_episode_seed,
)
from .provenance import synthetic_banner, write_json


class MaskablePpoAdapter:
    def __init__(self, model: Any):
        self.model = model

    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int:
        action, _ = self.model.predict(
            observation, action_masks=action_mask, deterministic=True
        )
        return int(action)

    def reset_episode(self) -> None:
        return None

    def observe_transition(self, info: dict) -> None:
        return None


def _summarize(episodes: list[dict]) -> dict[str, Any]:
    def col(key: str) -> list[float]:
        return [float(e[key]) for e in episodes]

    def mean_std(vals: list[float]) -> dict[str, float]:
        if not vals:
            return {"mean": 0.0, "std": 0.0}
        if len(vals) == 1:
            return {"mean": vals[0], "std": 0.0}
        return {"mean": float(statistics.mean(vals)), "std": float(statistics.stdev(vals))}

    return {
        "n_episodes": len(episodes),
        "return": mean_std(col("return")),
        "selected_topic_mastery_gain_sum": mean_std(col("selected_topic_mastery_gain_sum")),
        "net_total_mastery_change": mean_std(col("net_total_mastery_change")),
        "net_mean_mastery_change": mean_std(col("net_mean_mastery_change")),
        "valid_practice_count": mean_std(col("valid_practice_count")),
        "invalid_action_rate": mean_std(col("invalid_action_rate")),
    }


def _seed_mean_return(episodes: list[dict]) -> float:
    return float(statistics.mean(e["return"] for e in episodes))


def evaluate_method(
    method: str,
    *,
    train_seed: int,
    n_episodes: int,
    split: str,
    cfg: SeEnvConfig,
    model_path: Path | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    if split == "validation":
        scenario = scenario or "sim_val"
        seed_fn: Callable[[int], int] = lambda e: val_episode_seed(train_seed, e)
    elif split == "final_test":
        scenario = scenario or "sim_test"
        seed_fn = lambda e: final_test_episode_seed(train_seed, e)
    else:
        raise ValueError(split)

    env = make_env(cfg, scenario=scenario, seed=train_seed)
    if method == "weakest_stored_mastery_v1_sim":
        policy: Any = WeakestStoredMasteryV1SimBaseline()
    elif method == "random_valid":
        policy = RandomValidBaseline(seed=baseline_rng_seed(train_seed))
    elif method == "recent_performance":
        policy = RecentPerformanceBaseline()
    elif method == "maskable_ppo":
        if model_path is None or not Path(model_path).is_file():
            raise FileNotFoundError(f"MaskablePPO checkpoint missing: {model_path}")
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(model_path), device="cpu")
        policy = MaskablePpoAdapter(model)
    else:
        raise ValueError(f"unknown method {method}")

    episodes = rollout_policy(env, policy, episodes=n_episodes, seed_fn=seed_fn)
    env.close()
    return {
        "method": method,
        "label": COMPARISON_LABELS.get(method, method),
        "train_seed": train_seed,
        "split": split,
        "scenario": scenario,
        "uses_action_mask": True,
        "episodes": episodes,
        "summary": _summarize(episodes),
        **synthetic_banner(),
    }


def compare_validation(
    *,
    run_dir: Path,
    train_seeds: list[int],
    n_episodes: int,
    cfg: SeEnvConfig,
    model_paths: dict[int, Path],
) -> dict[str, Any]:
    assert_eval_seeds_disjoint(train_seeds, n_episodes)
    methods = [
        "maskable_ppo",
        "weakest_stored_mastery_v1_sim",
        "random_valid",
        "recent_performance",
    ]
    per_seed: dict[str, Any] = {}
    mean_by_method: dict[str, list[float]] = {m: [] for m in methods}

    for s in train_seeds:
        per_seed[str(s)] = {}
        for m in methods:
            mp = model_paths.get(s) if m == "maskable_ppo" else None
            result = evaluate_method(
                m,
                train_seed=s,
                n_episodes=n_episodes,
                split="validation",
                cfg=cfg,
                model_path=mp,
            )
            per_seed[str(s)][m] = result
            mean_by_method[m].append(_seed_mean_return(result["episodes"]))

    def across_seeds(vals: list[float]) -> dict[str, float]:
        if len(vals) == 1:
            return {"mean": vals[0], "sample_sd": 0.0}
        return {
            "mean": float(statistics.mean(vals)),
            "sample_sd": float(statistics.stdev(vals)),  # ddof=1
        }

    mean_val_return = {m: across_seeds(v) for m, v in mean_by_method.items()}
    # Selection: highest mean validation return; lowest method name tie-break only if equal means
    selected = max(
        methods,
        key=lambda m: (mean_val_return[m]["mean"], -methods.index(m)),
    )
    # Prefer maskable if tied with same mean — actually use explicit: max mean, then prefer order
    best_mean = max(mean_val_return[m]["mean"] for m in methods)
    candidates = [m for m in methods if abs(mean_val_return[m]["mean"] - best_mean) < 1e-12]
    selected = candidates[0]  # stable order as listed (maskable first among ties)

    payload = synthetic_banner(
        comparison_labels=COMPARISON_LABELS,
        env_protocol_version=PROTOCOL_VERSION,
        note="Selection uses validation only; do not tune on final test.",
        mean_val_return_by_algorithm=mean_val_return,
        selected=selected,
        seeds=per_seed,
        train_seeds=train_seeds,
        n_episodes=n_episodes,
    )
    write_json(run_dir / "selection_val.json", payload)
    write_json(run_dir / "comparison_val.json", payload)
    return payload


def final_test_evaluation(
    *,
    run_dir: Path,
    train_seeds: list[int],
    n_episodes: int,
    cfg: SeEnvConfig,
    model_paths: dict[int, Path],
    selection_path: Path,
) -> dict[str, Any]:
    """Requires an existing frozen selection_val.json — separate explicit step."""
    import json

    if not selection_path.is_file():
        raise FileNotFoundError(
            f"Frozen selection missing: {selection_path}. "
            "Run validation selection and freeze it before final evaluation."
        )
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    assert_eval_seeds_disjoint(train_seeds, n_episodes)
    methods = [
        "maskable_ppo",
        "weakest_stored_mastery_v1_sim",
        "random_valid",
        "recent_performance",
    ]
    rows = []
    for s in train_seeds:
        for m in methods:
            mp = model_paths.get(s) if m == "maskable_ppo" else None
            result = evaluate_method(
                m,
                train_seed=s,
                n_episodes=n_episodes,
                split="final_test",
                cfg=cfg,
                model_path=mp,
            )
            write_json(run_dir / "final_simulator_test" / f"seed_{s}_{m}.json", result)
            rows.append(
                {
                    "seed": s,
                    "method": m,
                    "return": result["summary"]["return"]["mean"],
                    "selected_topic_gain": result["summary"]["selected_topic_mastery_gain_sum"][
                        "mean"
                    ],
                    "net_total_mastery_change": result["summary"]["net_total_mastery_change"][
                        "mean"
                    ],
                    "invalid_action_rate": result["summary"]["invalid_action_rate"]["mean"],
                }
            )

    # Aggregate sample SD across seeds
    import csv

    out_dir = run_dir / "final_simulator_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "test_per_seed.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary_rows = []
    for m in methods:
        rets = [r["return"] for r in rows if r["method"] == m]
        gains = [r["selected_topic_gain"] for r in rows if r["method"] == m]
        nets = [r["net_total_mastery_change"] for r in rows if r["method"] == m]
        inv = [r["invalid_action_rate"] for r in rows if r["method"] == m]

        def ms(vals: list[float]) -> tuple[float, float]:
            if len(vals) == 1:
                return vals[0], 0.0
            return float(statistics.mean(vals)), float(statistics.stdev(vals))

        rm, rs = ms(rets)
        gm, gs = ms(gains)
        nm, ns = ms(nets)
        im, iss = ms(inv)
        summary_rows.append(
            {
                "method": m,
                "return_mean": rm,
                "return_sample_sd": rs,
                "selected_skill_gain_mean": gm,
                "selected_skill_gain_sample_sd": gs,
                "net_total_mastery_change_mean": nm,
                "net_total_mastery_change_sample_sd": ns,
                "invalid_action_rate_mean": im,
                "invalid_action_rate_sample_sd": iss,
            }
        )
    with (out_dir / "test_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)

    plan = synthetic_banner(
        selection_frozen_from=str(selection_path),
        selected_on_validation=selection.get("selected"),
        train_seeds=train_seeds,
        n_episodes=n_episodes,
        note="Final simulator test reporting only; scenarios are not real SE students.",
    )
    write_json(out_dir / "evaluation_plan.json", plan)
    return plan
