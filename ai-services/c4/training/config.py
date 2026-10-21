"""Shared configuration for the C4 training pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Official ASSISTments documentation page (cite this URL in publications).
ASSISTMENTS_OFFICIAL_PAGE = (
    "https://sites.google.com/site/assistmentsdata/home/"
    "2009-2010-assistment-data/skill-builder-data-2009-2010"
)

# Corrected Skill Builder file linked from the official page (Google Drive view URL).
# Manual download from that page is the authoritative acquisition path.
ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL = (
    "https://drive.google.com/file/d/1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE/view?usp=sharing"
)
ASSISTMENTS_CORRECTED_DRIVE_FILE_ID = "1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE"
ASSISTMENTS_EXPECTED_FILENAME = "skill_builder_data_corrected.csv"

DEFAULT_SEED = 42
DEFAULT_TRAIN_FRAC = 0.70
DEFAULT_VAL_FRAC = 0.15
DEFAULT_TEST_FRAC = 0.15

# Top-K skills kept as RL actions (practice those skills). Chosen after train-only frequency.
DEFAULT_TOP_K_SKILLS = 20
DEFAULT_MAX_EPISODE_STEPS = 50
DEFAULT_MASTERY_THRESHOLD = 0.80
DEFAULT_INVALID_ACTION_PENALTY = -1.0

# Explicitly labelled simulation-only activity types (NOT observed in ASSISTments).
# Included only for optional sensitivity experiments; never presented as real SE evidence.
SIMULATION_ONLY_ACTIVITY_TYPES = (
    "se_coding_exercise",
    "lecture_revision",
    "mock_exam",
)

SMOKE_TIMESTEPS = 2_000
FULL_TIMESTEPS = 100_000
FULL_SEEDS = (0, 1, 2)

# Comparison methods for new runs (protocol c4-env-eval-v1.1).
# Vanilla dqn/ppo remain unmasked penalty comparators.
# maskable_ppo is opt-in (sb3-contrib), not in the default tuple.
DEFAULT_COMPARISON_ALGORITHMS = (
    "dqn",
    "ppo",
    "weakest_mastery",
    "random_valid",
    "recent_performance",
)


@dataclass
class SplitConfig:
    seed: int = DEFAULT_SEED
    train_frac: float = DEFAULT_TRAIN_FRAC
    val_frac: float = DEFAULT_VAL_FRAC
    test_frac: float = DEFAULT_TEST_FRAC

    def validate(self) -> None:
        total = self.train_frac + self.val_frac + self.test_frac
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Split fractions must sum to 1.0, got {total}")


@dataclass
class EnvConfig:
    top_k_skills: int = DEFAULT_TOP_K_SKILLS
    max_episode_steps: int = DEFAULT_MAX_EPISODE_STEPS
    mastery_threshold: float = DEFAULT_MASTERY_THRESHOLD
    invalid_action_penalty: float = DEFAULT_INVALID_ACTION_PENALTY
    include_simulation_only_actions: bool = False
    time_cost_weight: float = 0.05
    mastery_gain_weight: float = 1.0
    correctness_reward_weight: float = 0.5
    # Assumed learning-gain parameters (NOT fitted from causal ASSISTments treatment effects).
    assumed_mastery_gain_correct: float = 0.08
    assumed_mastery_gain_incorrect: float = 0.02
    assumed_forgetting_per_step: float = 0.005


@dataclass
class TrainConfig:
    mode: str = "smoke"  # "smoke" | "full"
    seeds: tuple[int, ...] = field(default_factory=lambda: (DEFAULT_SEED,))
    timesteps: int = SMOKE_TIMESTEPS
    device: str = "auto"  # auto | cpu | cuda
    checkpoint_freq: int = 1_000
    eval_episodes: int = 20
    algorithms: tuple[str, ...] = DEFAULT_COMPARISON_ALGORITHMS

    def resolved(self) -> "TrainConfig":
        algorithms = tuple(normalize_algorithm_key(a) for a in self.algorithms)
        # Drop duplicate aliases (e.g. legacy rule_based + lowest_first both -> weakest_mastery).
        seen: list[str] = []
        for a in algorithms:
            if a not in seen:
                seen.append(a)
        algorithms = tuple(seen)
        if self.mode == "smoke":
            return TrainConfig(
                mode="smoke",
                seeds=(DEFAULT_SEED,),
                timesteps=SMOKE_TIMESTEPS,
                device=self.device if self.device != "auto" else "cpu",
                checkpoint_freq=min(self.checkpoint_freq, 500),
                eval_episodes=min(self.eval_episodes, 5),
                algorithms=algorithms,
            )
        if self.mode == "full":
            return TrainConfig(
                mode="full",
                seeds=FULL_SEEDS if self.seeds == (DEFAULT_SEED,) else self.seeds,
                timesteps=FULL_TIMESTEPS if self.timesteps == SMOKE_TIMESTEPS else self.timesteps,
                device=self.device,
                checkpoint_freq=self.checkpoint_freq,
                eval_episodes=self.eval_episodes,
                algorithms=algorithms,
            )
        raise ValueError(f"Unknown mode={self.mode!r}; use 'smoke' or 'full'")


def normalize_algorithm_key(name: str) -> str:
    """Map legacy comparison keys onto current labels without inventing new methods."""
    key = str(name).strip().lower()
    if key in {"rule_based", "lowest_first", "lowest_performance_first"}:
        return "weakest_mastery"
    if key in {"recent_perf", "recent_performance_baseline"}:
        return "recent_performance"
    return key


def config_to_dict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    raise TypeError(type(obj))
