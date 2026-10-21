"""Protocol se-path-sim-v1 — S1 catalogue with semester scenarios."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROTOCOL_VERSION = "se-path-sim-v1"
GENERATOR_VERSION = "se-sim-1.0.0"
DOMAIN = "se_simulation"

# Semester scenarios reported separately. Train/val/test still differ by
# prior_strength / topic-availability_rate within each semester.
SCENARIO_PRESETS: dict[str, dict[str, float | str]] = {
    "y3s1_sim_train": {"semester": "Y3S1", "prior_strength": 0.35, "availability_rate": 0.85},
    "y3s1_sim_val": {"semester": "Y3S1", "prior_strength": 0.45, "availability_rate": 0.80},
    "y3s1_sim_test": {"semester": "Y3S1", "prior_strength": 0.55, "availability_rate": 0.75},
    "y3s2_sim_train": {"semester": "Y3S2", "prior_strength": 0.35, "availability_rate": 0.85},
    "y3s2_sim_val": {"semester": "Y3S2", "prior_strength": 0.45, "availability_rate": 0.80},
    "y3s2_sim_test": {"semester": "Y3S2", "prior_strength": 0.55, "availability_rate": 0.75},
}

DEFAULT_TRAIN_SCENARIO = "y3s1_sim_train"
VAL_SCENARIOS = ("y3s1_sim_val", "y3s2_sim_val")
TEST_SCENARIOS = ("y3s1_sim_test", "y3s2_sim_test")

VAL_EPISODE_SEED_BASE = 6_000_000
TEST_EPISODE_SEED_BASE = 7_000_000
DIAG_EPISODE_SEED_BASE = 6_500_000
SEED_STRIDE = 10_000
BASELINE_RNG_SEED_BASE = 8_000_000


@dataclass(frozen=True)
class HeldOutContract:
    real_se_students: str = (
        "No real SE longitudinal attempt exports are used in se-path-sim-v1. "
        "Synthetic semester scenarios are NOT held-out real students."
    )
    simulator_scenarios: str = (
        "y3s1_* / y3s2_* change semester eligibility, prior_strength, and "
        "within-semester topic availability_rate only."
    )
    evaluation_seeds: str = (
        "Validation and final-test episode reset seeds use disjoint numeric bands "
        "(separate from se-path-sim-v0 bands)."
    )


def scenario_params(scenario: str) -> dict[str, float | str]:
    if scenario not in SCENARIO_PRESETS:
        raise KeyError(f"unknown scenario {scenario}; known={sorted(SCENARIO_PRESETS)}")
    return dict(SCENARIO_PRESETS[scenario])


def val_episode_seed(train_seed: int, episode: int) -> int:
    return VAL_EPISODE_SEED_BASE + int(train_seed) * SEED_STRIDE + int(episode)


def final_test_episode_seed(train_seed: int, episode: int) -> int:
    return TEST_EPISODE_SEED_BASE + int(train_seed) * SEED_STRIDE + int(episode)


def diag_episode_seed(train_seed: int, episode: int) -> int:
    return DIAG_EPISODE_SEED_BASE + int(train_seed) * SEED_STRIDE + int(episode)


def baseline_rng_seed(train_seed: int) -> int:
    return BASELINE_RNG_SEED_BASE + int(train_seed)


def assert_eval_seeds_disjoint(train_seeds: tuple[int, ...] | list[int], n_episodes: int) -> None:
    val_set: set[int] = set()
    test_set: set[int] = set()
    for s in train_seeds:
        for e in range(n_episodes):
            val_set.add(val_episode_seed(s, e))
            test_set.add(final_test_episode_seed(s, e))
    overlap = val_set & test_set
    if overlap:
        raise AssertionError(f"val/test episode seed overlap: {sorted(overlap)[:5]}")


def protocol_manifest() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL_VERSION,
        "generator": GENERATOR_VERSION,
        "domain": DOMAIN,
        "synthetic": True,
        "scope_decision": "S1",
        "held_out": asdict(HeldOutContract()),
        "scenarios": SCENARIO_PRESETS,
        "val_scenarios": list(VAL_SCENARIOS),
        "test_scenarios": list(TEST_SCENARIOS),
        "seed_bands": {
            "val_base": VAL_EPISODE_SEED_BASE,
            "test_base": TEST_EPISODE_SEED_BASE,
            "diag_base": DIAG_EPISODE_SEED_BASE,
            "baseline_rng_base": BASELINE_RNG_SEED_BASE,
            "stride": SEED_STRIDE,
        },
        "not_v0": "Additive package training_se_v1; does not modify se-path-sim-v0.",
    }
