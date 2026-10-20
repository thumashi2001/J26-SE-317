"""Generate synthetic trajectories via the simulator (never by copying CSV rows)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .baselines import WeakestMasteryBaseline
from .config import EnvConfig
from .environment import make_env
from .paths import ensure_dir
from .provenance import write_json
from .simulator import Simulator


# Train/val/test simulation configs with varied learner conditions.
# Do not tune policies against the test configuration.
SIM_SCENARIOS = {
    "sim_train": {"prior_strength": 0.35, "episodes": 50},
    "sim_val": {"prior_strength": 0.45, "episodes": 20},
    "sim_test": {"prior_strength": 0.55, "episodes": 20},
}


def generate_scenario_trajectories(
    simulator: Simulator,
    env_config: EnvConfig,
    *,
    scenario: str,
    seed: int,
    episodes: int | None = None,
    prior_strength: float | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if scenario not in SIM_SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario}; known={list(SIM_SCENARIOS)}")
    meta = SIM_SCENARIOS[scenario]
    n_ep = episodes if episodes is not None else int(meta["episodes"])
    prior = prior_strength if prior_strength is not None else float(meta["prior_strength"])

    env = make_env(simulator, env_config, scenario=scenario, prior_strength=prior, seed=seed)
    policy = WeakestMasteryBaseline(simulator.n_skills)
    rows: list[dict[str, Any]] = []
    for ep in range(n_ep):
        obs, info = env.reset(seed=seed + ep, options={"prior_strength": prior, "scenario": scenario})
        done = False
        t = 0
        while not done:
            mask = info.get("action_mask")
            action = policy.predict(obs, mask)
            next_obs, reward, terminated, truncated, info = env.step(action)
            rows.append(
                {
                    "data_kind": "synthetic_simulator_trajectories",
                    "scenario": scenario,
                    "episode": ep,
                    "t": t,
                    "action": int(action),
                    "action_label": env.action_labels[int(action)] if 0 <= int(action) < env.n_actions else None,
                    "reward": float(reward),
                    "correct": info.get("correct"),
                    "mastery_gain": info.get("mastery_gain"),
                    "invalid_action": bool(info.get("invalid_action")),
                    "mean_mastery": info.get("mean_mastery"),
                    "seed": seed,
                }
            )
            obs = next_obs
            t += 1
            done = terminated or truncated

    df = pd.DataFrame(rows)
    prov = simulator.provenance(seed=seed, scenario=scenario)
    prov["n_rows"] = int(len(df))
    prov["n_episodes"] = n_ep
    prov["prior_strength"] = prior
    return df, prov


def write_synthetic_splits(
    simulator: Simulator,
    env_config: EnvConfig,
    output_dir: Path | str,
    *,
    seed: int = 42,
) -> dict[str, Path]:
    out = ensure_dir(output_dir)
    paths = {}
    for scenario in ("sim_train", "sim_val", "sim_test"):
        df, prov = generate_scenario_trajectories(simulator, env_config, scenario=scenario, seed=seed)
        csv_path = out / f"{scenario}_trajectories.csv"
        json_path = out / f"{scenario}_provenance.json"
        df.to_csv(csv_path, index=False)
        write_json(json_path, prov)
        paths[scenario] = csv_path
    # Guard: ensure synthetic is not a copy of real interactions schema dump
    write_json(
        out / "SYNTHETIC_README.json",
        {
            "warning": (
                "These files are simulator-generated. They are not ASSISTments rows and "
                "must not be used as evidence of real SE learning gains."
            )
        },
    )
    return paths
