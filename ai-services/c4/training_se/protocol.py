"""Protocol se-path-sim-v0 — versioning and disjoint evaluation seeds."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PROTOCOL_VERSION = "se-path-sim-v0"
GENERATOR_VERSION = "se-sim-0.1.0"
DOMAIN = "se_simulation"

# Scenario names = initial-condition presets only (NOT held-out real SE students).
SCENARIO_PRESETS: dict[str, dict[str, float]] = {
    "sim_train": {"prior_strength": 0.35, "availability_rate": 0.85},
    "sim_val": {"prior_strength": 0.45, "availability_rate": 0.80},
    "sim_test": {"prior_strength": 0.55, "availability_rate": 0.75},
}

VAL_EPISODE_SEED_BASE = 3_000_000
TEST_EPISODE_SEED_BASE = 4_000_000
DIAG_EPISODE_SEED_BASE = 3_500_000
SEED_STRIDE = 10_000
# Separate stream for random_valid baseline RNG (must not share simulator outcome RNG).
BASELINE_RNG_SEED_BASE = 5_000_000


@dataclass(frozen=True)
class HeldOutContract:
    real_se_students: str = (
        "No real SE longitudinal attempt exports are used in se-path-sim-v0. "
        "Synthetic scenarios are NOT held-out real students."
    )
    simulator_scenarios: str = (
        "sim_train/sim_val/sim_test change prior_strength and availability_rate presets only."
    )
    evaluation_seeds: str = (
        "Validation and final-test episode reset seeds use disjoint numeric bands."
    )


def scenario_params(scenario: str) -> dict[str, float]:
    return dict(SCENARIO_PRESETS.get(scenario, SCENARIO_PRESETS["sim_train"]))


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
        "held_out": asdict(HeldOutContract()),
        "scenarios": SCENARIO_PRESETS,
        "seed_bands": {
            "val_base": VAL_EPISODE_SEED_BASE,
            "test_base": TEST_EPISODE_SEED_BASE,
            "diag_base": DIAG_EPISODE_SEED_BASE,
            "baseline_rng_base": BASELINE_RNG_SEED_BASE,
            "stride": SEED_STRIDE,
        },
    }
