"""Gymnasium SE practice environment (se-path-sim-v1)."""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .catalogue import N_TOPICS, ORDERED_TOPICS, semester_eligibility_mask
from .config import SeEnvConfig
from .observation import OBS_DIM, build_observation
from .protocol import DEFAULT_TRAIN_SCENARIO, PROTOCOL_VERSION, scenario_params
from .simulator import SeLearnerState, SeSyntheticSimulator


class SePathSimEnvV1(gym.Env):
    """
    Discrete actions = practise one of 46 C1 practice topics.

    Mask = semester_eligible AND available AND (below mastery threshold,
    with reopen-if-all-mastered rule among available). No eligible actions →
    all-False mask; stepping any action yields invalid penalty and no mastery change.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        cfg: SeEnvConfig | None = None,
        *,
        scenario: str = DEFAULT_TRAIN_SCENARIO,
        seed: int | None = None,
    ):
        super().__init__()
        self.cfg = cfg or SeEnvConfig()
        self.cfg.validate()
        self.scenario = scenario
        params = scenario_params(scenario)
        self.semester = str(params["semester"])
        self.prior_strength = float(params["prior_strength"])
        self.availability_rate = float(params["availability_rate"])
        self.simulator = SeSyntheticSimulator(self.cfg)
        self.n_actions = N_TOPICS
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(self.n_actions)
        self._state: SeLearnerState | None = None
        self._initial_mastery: np.ndarray | None = None
        self._episode_return = 0.0
        self._invalid_actions = 0
        self._valid_practice = 0
        self._selected_gain_sum = 0.0
        self._steps = 0
        self._termination_reason = ""
        self.env_protocol_version = PROTOCOL_VERSION
        super().reset(seed=seed)
        self._rng = self.np_random

    def action_masks(self) -> np.ndarray:
        return self.available_action_mask()

    def available_action_mask(self, state: SeLearnerState | None = None) -> np.ndarray:
        st = state if state is not None else self._state
        assert st is not None
        semester_ok = np.asarray(semester_eligibility_mask(st.semester), dtype=bool)
        avail = (st.available > 0.5) & semester_ok
        below = st.mastery < self.cfg.mastery_threshold
        mask = avail & below
        if not mask.any() and avail.any():
            mask = avail.copy()
        # If empty: all False — no eligible actions
        return mask.astype(bool)

    def _obs(self) -> np.ndarray:
        assert self._state is not None
        return build_observation(
            self._state.mastery,
            self._state.available,
            elapsed_env_steps=self._steps,
            max_episode_steps=self.cfg.max_episode_steps,
            prior_strength=self.prior_strength,
            mastery_threshold=self.cfg.mastery_threshold,
        )

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self._rng = self.np_random
        opts = options or {}
        if "scenario" in opts:
            self.scenario = str(opts["scenario"])
            params = scenario_params(self.scenario)
            self.semester = str(params["semester"])
            self.prior_strength = float(params["prior_strength"])
            self.availability_rate = float(params["availability_rate"])
        if "semester" in opts:
            self.semester = str(opts["semester"])
        if "prior_strength" in opts:
            self.prior_strength = float(opts["prior_strength"])
        if "availability_rate" in opts:
            self.availability_rate = float(opts["availability_rate"])

        self._state = self.simulator.initial_state(
            self._rng,
            semester=self.semester,
            prior_strength=self.prior_strength,
            availability_rate=self.availability_rate,
        )
        self._initial_mastery = self._state.mastery.copy()
        self._episode_return = 0.0
        self._invalid_actions = 0
        self._valid_practice = 0
        self._selected_gain_sum = 0.0
        self._steps = 0
        self._termination_reason = ""
        info = {
            "scenario": self.scenario,
            "semester": self.semester,
            "prior_strength": self.prior_strength,
            "availability_rate": self.availability_rate,
            "action_mask": self.available_action_mask(),
            "n_eligible_actions": int(self.available_action_mask().sum()),
            "domain": "se_simulation",
            "synthetic": True,
            "protocol": PROTOCOL_VERSION,
            "topics": list(ORDERED_TOPICS),
            "generation_note": (
                "Synthetic learner state generated under declared assumptions; "
                "not a live AdaptiveLearnSE student."
            ),
        }
        return self._obs(), info

    def step(self, action: int):
        assert self._state is not None and self._initial_mastery is not None
        action = int(action)
        mask = self.available_action_mask()
        terminated = False
        truncated = False
        info: dict[str, Any] = {
            "action": action,
            "domain": "se_simulation",
            "synthetic": True,
            "protocol": PROTOCOL_VERSION,
            "semester": self._state.semester,
        }

        if action < 0 or action >= self.n_actions or not bool(mask[action]):
            reward = float(self.cfg.invalid_action_penalty)
            self._invalid_actions += 1
            info.update(
                {
                    "invalid_action": True,
                    "correct": None,
                    "selected_topic_gain": 0.0,
                    "all_invalid_mask": not bool(mask.any()),
                    "no_eligible_actions": not bool(mask.any()),
                }
            )
            if not mask.any():
                terminated = True
                self._termination_reason = "no_eligible_actions"
        else:
            self._state, step_info = self.simulator.step_attempt(
                self._state, action, self._rng
            )
            gain = float(step_info["selected_topic_gain"])
            correct = bool(step_info["correct"])
            reward = (
                self.cfg.correctness_reward_weight * float(correct)
                + self.cfg.mastery_gain_weight * gain
                - self.cfg.time_cost_weight
            )
            self._valid_practice += 1
            self._selected_gain_sum += gain
            info.update(step_info)
            info["invalid_action"] = False
            info["topic"] = ORDERED_TOPICS[action]

        self._episode_return += reward
        self._steps += 1
        if self._steps >= self.cfg.max_episode_steps:
            truncated = True
            if not self._termination_reason:
                self._termination_reason = "max_episode_steps"

        avail = self._state.available > 0.5
        mean_now = float(self._state.mastery[avail].mean()) if avail.any() else 0.0
        total_now = float(self._state.mastery.sum())
        total_init = float(self._initial_mastery.sum())
        info.update(
            {
                "action_mask": self.available_action_mask(),
                "n_eligible_actions": int(self.available_action_mask().sum()),
                "episode_return": self._episode_return,
                "invalid_action_count": self._invalid_actions,
                "valid_practice_count": self._valid_practice,
                "selected_topic_mastery_gain_sum": self._selected_gain_sum,
                "mean_mastery": mean_now,
                "total_mastery": total_now,
                "mean_mastery_delta_final_minus_initial": mean_now
                - float(self._initial_mastery[avail].mean() if avail.any() else 0.0),
                "total_mastery_delta_final_minus_initial": total_now - total_init,
                "elapsed_env_steps": self._steps,
                "termination_reason": self._termination_reason
                if (terminated or truncated)
                else "",
                "reward": reward,
            }
        )
        return self._obs(), float(reward), terminated, truncated, info


# Alias matching v0 naming inside this package
SePathSimEnv = SePathSimEnvV1


def make_env(
    cfg: SeEnvConfig | None = None,
    *,
    scenario: str = DEFAULT_TRAIN_SCENARIO,
    seed: int | None = None,
) -> SePathSimEnvV1:
    return SePathSimEnvV1(cfg, scenario=scenario, seed=seed)
