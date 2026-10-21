"""Validation comparison and final-test evaluation (se-path-sim-v1).

Reports Y3S1 and Y3S2 semester scenarios separately. Selection uses the mean
of per-semester validation returns (not final test).
"""

from __future__ import annotations

import csv
import json
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
    TEST_SCENARIOS,
    VAL_SCENARIOS,
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


def evaluate_method(
    method: str,
    *,
    train_seed: int,
    n_episodes: int,
    split: str,
    cfg: SeEnvConfig,
    model_path: Path | None = None,
    scenario: str,
) -> dict[str, Any]:
    if split == "validation":
        seed_fn: Callable[[int], int] = lambda e: val_episode_seed(train_seed, e)
    elif split == "final_test":
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
    by_semester: dict[str, Any] = {}
    combined_means: dict[str, list[float]] = {m: [] for m in methods}

    for scenario in VAL_SCENARIOS:
        semester = "Y3S1" if scenario.startswith("y3s1") else "Y3S2"
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
                    scenario=scenario,
                )
                per_seed[str(s)][m] = {
                    "summary": result["summary"],
                    "scenario": scenario,
                }
                mean_by_method[m].append(
                    float(statistics.mean(e["return"] for e in result["episodes"]))
                )
                write_json(
                    run_dir / "val_detail" / f"{scenario}_seed_{s}_{m}.json",
                    result,
                )

        def across_seeds(vals: list[float]) -> dict[str, float]:
            if len(vals) == 1:
                return {"mean": vals[0], "sample_sd": 0.0}
            return {
                "mean": float(statistics.mean(vals)),
                "sample_sd": float(statistics.stdev(vals)),
            }

        mean_val_return = {m: across_seeds(v) for m, v in mean_by_method.items()}
        by_semester[semester] = {
            "scenario": scenario,
            "mean_val_return_by_algorithm": mean_val_return,
            "seeds": per_seed,
        }
        for m in methods:
            combined_means[m].append(mean_val_return[m]["mean"])

    combined = {
        m: {"mean": float(statistics.mean(vs)), "per_semester_means": vs}
        for m, vs in combined_means.items()
    }
    best_mean = max(combined[m]["mean"] for m in methods)
    candidates = [m for m in methods if abs(combined[m]["mean"] - best_mean) < 1e-12]
    selected = candidates[0]

    payload = synthetic_banner(
        comparison_labels=COMPARISON_LABELS,
        env_protocol_version=PROTOCOL_VERSION,
        note=(
            "Selection uses mean of Y3S1+Y3S2 validation returns only; "
            "do not tune on final test. Semesters reported separately under by_semester."
        ),
        by_semester=by_semester,
        mean_val_return_combined=combined,
        selected=selected,
        train_seeds=train_seeds,
        n_episodes=n_episodes,
        val_scenarios=list(VAL_SCENARIOS),
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
    for scenario in TEST_SCENARIOS:
        semester = "Y3S1" if scenario.startswith("y3s1") else "Y3S2"
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
                    scenario=scenario,
                )
                write_json(
                    run_dir / "final_simulator_test" / f"{scenario}_seed_{s}_{m}.json",
                    result,
                )
                rows.append(
                    {
                        "semester": semester,
                        "scenario": scenario,
                        "seed": s,
                        "method": m,
                        "return": result["summary"]["return"]["mean"],
                        "selected_topic_gain": result["summary"][
                            "selected_topic_mastery_gain_sum"
                        ]["mean"],
                        "net_total_mastery_change": result["summary"][
                            "net_total_mastery_change"
                        ]["mean"],
                        "invalid_action_rate": result["summary"]["invalid_action_rate"][
                            "mean"
                        ],
                    }
                )

    out_dir = run_dir / "final_simulator_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "test_per_seed.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary_rows = []
    for semester in ("Y3S1", "Y3S2"):
        for m in methods:
            subset = [r for r in rows if r["method"] == m and r["semester"] == semester]
            rets = [r["return"] for r in subset]

            def ms(vals: list[float]) -> tuple[float, float]:
                if len(vals) == 1:
                    return vals[0], 0.0
                return float(statistics.mean(vals)), float(statistics.stdev(vals))

            rm, rs = ms(rets)
            summary_rows.append(
                {
                    "semester": semester,
                    "method": m,
                    "return_mean": rm,
                    "return_sample_sd": rs,
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
        test_scenarios=list(TEST_SCENARIOS),
        note="Final simulator test reporting only; not real SE students.",
    )
    write_json(out_dir / "evaluation_plan.json", plan)
    return plan
