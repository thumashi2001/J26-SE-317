"""Environment / evaluation protocol versioning and seed contracts.

Historical runs under older protocols remain on disk unchanged. New comparison
runs must record ``ENV_PROTOCOL_VERSION`` and use the seed helpers below.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Observation layout is unchanged in length (n_skills + 4) so old SB3 zips still load.
# Semantics of index [-3] (step_frac) changed in v1.1: elapsed *environment* steps,
# including invalid-action transitions — not learner interaction count.
ENV_PROTOCOL_VERSION = "c4-env-eval-v1.1"
GENERATOR_COMPAT = "c4-sim-0.1.0"

# Scenario names label initial-condition presets only. They are NOT held-out
# real-learner partitions. True held-out structure for the response model is the
# ASSISTments learner split (train/validation/test) from notebook 01.
SCENARIO_PRESETS: dict[str, dict[str, float]] = {
    "default": {"prior_strength": 0.40},
    "train": {"prior_strength": 0.40},
    "sim_train": {"prior_strength": 0.35},
    "sim_val": {"prior_strength": 0.45},
    "sim_test": {"prior_strength": 0.55},
}

# Disjoint episode-seed bands (per training seed S, episode e):
#   train stream uses S during SB3.learn (internal)
#   validation episodes: VAL_BASE + S * STRIDE + e
#   diagnostics (val-only): DIAG_BASE + S * STRIDE + e
#   final test episodes: TEST_BASE + S * STRIDE + e
VAL_EPISODE_SEED_BASE = 1_000_000
DIAG_EPISODE_SEED_BASE = 1_500_000
TEST_EPISODE_SEED_BASE = 2_000_000
SEED_STRIDE = 10_000


@dataclass(frozen=True)
class HeldOutContract:
    """What is actually held out vs what is only a scenario label."""

    real_data_held_out: str = (
        "ASSISTments learners partitioned into train/validation/test "
        "(notebook 01). Response-model fit uses train only."
    )
    simulator_scenarios: str = (
        "sim_train/sim_val/sim_test only change initial prior_strength presets. "
        "They are not disjoint real students and are not a substitute for the "
        "learner split."
    )
    evaluation_seeds: str = (
        "Validation and test episode reset seeds use disjoint numeric bands "
        "so they do not collide with each other."
    )


def scenario_prior_strength(scenario: str, default: float = 0.4) -> float:
    preset = SCENARIO_PRESETS.get(scenario)
    if not preset:
        return default
    return float(preset["prior_strength"])


def val_episode_seed(train_seed: int, episode: int) -> int:
    return VAL_EPISODE_SEED_BASE + int(train_seed) * SEED_STRIDE + int(episode)


def diag_episode_seed(train_seed: int, episode: int) -> int:
    return DIAG_EPISODE_SEED_BASE + int(train_seed) * SEED_STRIDE + int(episode)


def final_test_episode_seed(train_seed: int, episode: int) -> int:
    """Episode reset seed for final-test evaluation (disjoint from validation/diagnostics)."""
    return TEST_EPISODE_SEED_BASE + int(train_seed) * SEED_STRIDE + int(episode)


def assert_eval_seeds_disjoint(train_seeds: tuple[int, ...] | list[int], n_episodes: int) -> None:
    val_set: set[int] = set()
    test_set: set[int] = set()
    diag_set: set[int] = set()
    for s in train_seeds:
        for e in range(n_episodes):
            val_set.add(val_episode_seed(s, e))
            test_set.add(final_test_episode_seed(s, e))
            diag_set.add(diag_episode_seed(s, e))
    if val_set & test_set:
        raise AssertionError("Validation and test episode seeds overlap")
    if val_set & diag_set or test_set & diag_set:
        raise AssertionError("Diagnostic seeds overlap validation/test bands")


def protocol_manifest() -> dict[str, Any]:
    return {
        "env_protocol_version": ENV_PROTOCOL_VERSION,
        "generator_compat": GENERATOR_COMPAT,
        "observation": {
            "vector": "[mastery_1..K, mean_mastery, frac_mastered, elapsed_env_step_frac, prior_strength]",
            "dim": "n_skills + 4",
            "step_frac_semantics_v1_1": (
                "elapsed environment steps including invalid-action transitions, "
                "divided by max_episode_steps. Learner interaction count is separate "
                "(info['learner_interaction_count'] / LearnerSimState.step)."
            ),
            "checkpoint_load_note": (
                "Observation dimension unchanged; old SB3 zips load. Feature semantics "
                "for step_frac differ from pre-v1.1 — re-evaluate under this protocol."
            ),
        },
        "held_out": asdict(HeldOutContract()),
        "seed_bands": {
            "val_base": VAL_EPISODE_SEED_BASE,
            "diag_base": DIAG_EPISODE_SEED_BASE,
            "test_base": TEST_EPISODE_SEED_BASE,
            "stride": SEED_STRIDE,
        },
        "partial_observability": {
            "policy_observation_includes": [
                "current mastery per skill",
                "mean mastery",
                "fraction mastered",
                "elapsed env step fraction",
                "prior_strength scalar",
            ],
            "hidden_from_policy_used_by_simulator": [
                "skill_attempts / skill_correct / skill_streak counts",
                "global_attempts / global_correct",
                "logistic response-model features and coefficients",
                "blend weight between p_model and mastery",
                "assumed mastery gain / forgetting parameters",
            ],
            "implication": (
                "The decision process is partially observable relative to the "
                "response simulator's internal history. Policies see mastery and "
                "time, not the full count/streak features that drive p_correct."
            ),
        },
    }
