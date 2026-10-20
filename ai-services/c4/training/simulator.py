"""Learner-response simulator backed by a fitted model + assumed mastery dynamics.

Synthetic trajectories must be generated here (not by duplicating CSV rows).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import GENERATOR_VERSION
from .config import EnvConfig
from .features import FEATURE_NAMES
from .provenance import make_synthetic_provenance
from .response_model import ResponseModelBundle


@dataclass
class LearnerSimState:
    skill_mastery: np.ndarray  # float in [0, 1], length = n_skills
    skill_attempts: np.ndarray
    skill_correct: np.ndarray
    skill_streak: np.ndarray
    global_attempts: int = 0
    global_correct: int = 0
    step: int = 0

    def copy(self) -> "LearnerSimState":
        return LearnerSimState(
            skill_mastery=self.skill_mastery.copy(),
            skill_attempts=self.skill_attempts.copy(),
            skill_correct=self.skill_correct.copy(),
            skill_streak=self.skill_streak.copy(),
            global_attempts=self.global_attempts,
            global_correct=self.global_correct,
            step=self.step,
        )


@dataclass
class Simulator:
    response_model: ResponseModelBundle
    skill_list: list[str]
    env_config: EnvConfig = field(default_factory=EnvConfig)
    parent_real_checksum: str | None = None

    def __post_init__(self) -> None:
        self.n_skills = len(self.skill_list)
        self.skill_to_idx = {s: i for i, s in enumerate(self.skill_list)}

    def initial_state(self, rng: np.random.Generator, *, prior_strength: float = 0.4) -> LearnerSimState:
        # Varied learner conditions: sample initial mastery around prior_strength.
        mastery = rng.beta(2, 2, size=self.n_skills) * 0.5 + prior_strength * 0.5
        mastery = np.clip(mastery, 0.05, 0.95)
        return LearnerSimState(
            skill_mastery=mastery.astype(np.float32),
            skill_attempts=np.zeros(self.n_skills, dtype=np.float32),
            skill_correct=np.zeros(self.n_skills, dtype=np.float32),
            skill_streak=np.zeros(self.n_skills, dtype=np.float32),
        )

    def historical_features_for_skill(self, state: LearnerSimState, skill_idx: int) -> dict[str, float]:
        sa = float(state.skill_attempts[skill_idx])
        sc = float(state.skill_correct[skill_idx])
        ga = float(state.global_attempts)
        gc = float(state.global_correct)
        return {
            "skill_prior_attempts": sa,
            "skill_prior_correct": sc,
            "skill_prior_accuracy": (sc / sa) if sa > 0 else 0.5,
            "skill_prior_consecutive_correct": float(state.skill_streak[skill_idx]),
            "global_prior_attempts": ga,
            "global_prior_accuracy": (gc / ga) if ga > 0 else 0.5,
            "learner_step": float(state.step),
        }

    def predict_correct_prob(self, state: LearnerSimState, skill_idx: int) -> float:
        feats = self.historical_features_for_skill(state, skill_idx)
        # Blend fitted response model with current simulated mastery (assumed coupling).
        x = self.response_model.scaler.transform_row(feats).reshape(1, -1)
        p_model = float(self.response_model.model.predict_proba(x)[0, 1])
        p_mastery = float(state.skill_mastery[skill_idx])
        # Documented assumption: equal blend.
        return float(np.clip(0.5 * p_model + 0.5 * p_mastery, 0.02, 0.98))

    def step(
        self,
        state: LearnerSimState,
        skill_idx: int,
        rng: np.random.Generator,
    ) -> tuple[LearnerSimState, dict[str, Any]]:
        cfg = self.env_config
        p = self.predict_correct_prob(state, skill_idx)
        correct = int(rng.random() < p)
        new = state.copy()
        mastery_before_all = new.skill_mastery.copy()
        mastery_before = float(new.skill_mastery[skill_idx])
        # Assumed mastery transition (not causal ASSISTments treatment effect).
        gain = cfg.assumed_mastery_gain_correct if correct else cfg.assumed_mastery_gain_incorrect
        new.skill_mastery[skill_idx] = np.clip(mastery_before + gain, 0.0, 1.0)
        # Practice-interference forgetting: applied on *valid practice* steps to other
        # skills only. Not applied on invalid actions / pure elapsed env time.
        # See docs/FORGETTING_AND_LEARNING_ASSUMPTIONS.md (assumption, not fitted).
        if cfg.assumed_forgetting_per_step > 0:
            mask = np.ones(self.n_skills, dtype=bool)
            mask[skill_idx] = False
            new.skill_mastery[mask] = np.clip(
                new.skill_mastery[mask] - cfg.assumed_forgetting_per_step, 0.0, 1.0
            )
        new.skill_attempts[skill_idx] += 1
        new.skill_correct[skill_idx] += correct
        new.skill_streak[skill_idx] = (new.skill_streak[skill_idx] + 1) if correct else 0
        new.global_attempts += 1
        new.global_correct += correct
        new.step += 1
        selected_gain = float(new.skill_mastery[skill_idx] - mastery_before)
        net_total_delta = float(new.skill_mastery.sum() - mastery_before_all.sum())
        info = {
            "correct": correct,
            "p_correct": p,
            "skill_idx": skill_idx,
            "skill": self.skill_list[skill_idx],
            "mastery_before": mastery_before,
            "mastery_after": float(new.skill_mastery[skill_idx]),
            "mastery_gain": selected_gain,
            "selected_skill_mastery_gain": selected_gain,
            "net_total_mastery_delta_step": net_total_delta,
            "forgetting_model": "practice_interference_on_non_selected_skills",
            "predicted_correctness_not_causal_gain": True,
        }
        return new, info

    def assumptions(self) -> dict[str, Any]:
        cfg = self.env_config
        n_other = max(0, self.n_skills - 1)
        return {
            "fitted_from_data": [
                "logistic_regression_response_coefficients",
                "feature_scaler_means_stds",
                "skill_catalogue_from_train_frequency",
            ],
            "assumed_not_fitted": {
                "assumed_mastery_gain_correct": cfg.assumed_mastery_gain_correct,
                "assumed_mastery_gain_incorrect": cfg.assumed_mastery_gain_incorrect,
                "assumed_forgetting_per_step": cfg.assumed_forgetting_per_step,
                "forgetting_interpretation": (
                    "practice_interference: subtract forgetting from every non-selected "
                    "skill on each valid practice step; not calendar-time decay; "
                    "not applied on invalid actions"
                ),
                "expected_net_total_delta_correct_away_from_bounds": (
                    cfg.assumed_mastery_gain_correct
                    - n_other * cfg.assumed_forgetting_per_step
                ),
                "expected_net_total_delta_incorrect_away_from_bounds": (
                    cfg.assumed_mastery_gain_incorrect
                    - n_other * cfg.assumed_forgetting_per_step
                ),
                "blend_response_model_with_mastery": 0.5,
                "initial_mastery_sampling": "beta-based prior around prior_strength",
            },
            "domain": "ASSISTments math skills only unless simulation-only actions enabled",
            "generator_version": GENERATOR_VERSION,
            "feature_names": list(FEATURE_NAMES),
        }

    def provenance(self, *, seed: int, scenario: str) -> dict[str, Any]:
        return make_synthetic_provenance(
            generator_version=GENERATOR_VERSION,
            seed=seed,
            scenario=scenario,
            assumptions=self.assumptions(),
            parent_real_checksum=self.parent_real_checksum,
        )


def choose_top_skills(train_interactions, top_k: int) -> list[str]:
    counts = train_interactions["primary_skill"].astype(str).value_counts()
    skills = [s for s in counts.index.tolist() if s and s != "unknown"]
    return skills[:top_k]
