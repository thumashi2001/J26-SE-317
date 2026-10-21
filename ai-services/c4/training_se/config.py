"""Frozen dynamics / reward configuration for se-path-sim-v0.

All transition parameters here are **synthetic assumptions**, not fitted SE
student behaviour. Freeze before training; do not retune to beat baselines.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .catalogue import N_TOPICS
from .protocol import GENERATOR_VERSION, PROTOCOL_VERSION


@dataclass
class SeEnvConfig:
    n_topics: int = N_TOPICS
    max_episode_steps: int = 30
    mastery_threshold: float = 0.80  # on [0,1] scale (= 80/100 in C1)
    invalid_action_penalty: float = -1.0
    # Synthetic response: P(correct) = clip(p_floor + p_slope * mastery, p_floor, p_ceil)
    p_floor: float = 0.15
    p_slope: float = 0.70
    p_ceil: float = 0.95
    # Mastery gains on [0,1] after one practice *attempt* (not a full C1 session)
    mastery_gain_correct: float = 0.08
    mastery_gain_incorrect: float = 0.02
    # Explicitly NO cross-topic forgetting in v0 (hypothetical short-horizon default)
    forgetting_per_other_topic: float = 0.0
    time_cost_weight: float = 0.05
    mastery_gain_weight: float = 1.0
    correctness_reward_weight: float = 0.5
    initial_mastery_low: float = 0.10
    initial_mastery_high: float = 0.55

    def validate(self) -> None:
        if self.n_topics != N_TOPICS:
            raise ValueError(f"n_topics must be {N_TOPICS}")
        if self.forgetting_per_other_topic != 0.0:
            raise ValueError(
                "se-path-sim-v0 freezes forgetting_per_other_topic=0.0; "
                "bump protocol version to change dynamics."
            )


SMOKE_TIMESTEPS = 2_000
SMOKE_SEEDS = (0,)
FULL_TIMESTEPS = 50_000
FULL_SEEDS = (0, 1, 2)

ASSUMPTIONS = {
    "response_model": (
        "Synthetic linear probability of a correct practice *attempt*: "
        "P(correct)=clip(p_floor + p_slope*mastery, p_floor, p_ceil). "
        "Not fitted on fixtures or real SE logs."
    ),
    "step_definition": (
        "One environment step = one synthetic practice attempt on the selected topic "
        "(analogous to a single C1 practice answer), NOT an entire practice session."
    ),
    "forgetting": (
        "No forgetting (forgetting_per_other_topic=0). Hypothetical short-horizon "
        "simplification so net mastery is not forced negative by interference. "
        "Not an empirically fitted SE learning model; distinct from ASSISTments "
        "practice-interference defaults and from C1 calendar decay."
    ),
    "mastery_scale": "Internal [0,1] corresponds to C1 0–100 via /100.",
    "availability": (
        "Topics may be unavailable at episode start (scenario availability_rate). "
        "Unavailable ≠ zero mastery: availability indicators make this distinguishable."
    ),
    "no_prerequisites": "No fabricated prerequisite graph.",
    "not_assistments": "Does not reuse ASSISTments weights, coefficients, or skill IDs.",
}


def reward_equation_latexish() -> str:
    return (
        "r = correctness_reward_weight * 1[correct] "
        "+ mastery_gain_weight * selected_topic_gain "
        "- time_cost_weight "
        "  (invalid: r = invalid_action_penalty; no mastery change)"
    )


def frozen_config_dict(cfg: SeEnvConfig | None = None) -> dict[str, Any]:
    c = cfg or SeEnvConfig()
    c.validate()
    return {
        "protocol": PROTOCOL_VERSION,
        "generator": GENERATOR_VERSION,
        "domain": "se_simulation",
        "synthetic": True,
        "env": asdict(c),
        "reward_equation": reward_equation_latexish(),
        "assumptions": ASSUMPTIONS,
        "smoke_timesteps": SMOKE_TIMESTEPS,
        "full_timesteps_default": FULL_TIMESTEPS,
        "full_seeds_default": list(FULL_SEEDS),
    }
