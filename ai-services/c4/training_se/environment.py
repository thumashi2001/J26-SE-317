"""Gymnasium SE practice environment (se-path-sim-v0)."""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .catalogue import N_TOPICS, ORDERED_TOPICS
from .config import SeEnvConfig
from .observation import OBS_DIM, build_observation
from .protocol import PROTOCOL_VERSION, scenario_params
from .simulator import SeLearnerState, SeSyntheticSimulator


class SePathSimEnv(gym.Env):
    """
    Discrete actions = practise one of 12 C1-supported SE topics (one attempt).

    Invalid actions (masked-off) receive ``invalid_action_penalty`` and do not
    change mastery. Elapsed env steps advance on every step including invalid.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        cfg: SeEnvConfig | None = None,
        *,
        scenario: str = "sim_train",
        seed: int | None = None,
    ):
        super().__init__()
        self.cfg = cfg or SeEnvConfig()
        self.cfg.validate()
        self.scenario = scenario
        params = scenario_params(scenario)
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
        avail = st.available > 0.5
        below = st.mastery < self.cfg.mastery_threshold
        mask = avail & below
        if not mask.any() and avail.any():
            # Re-open available topics that are already "mastered" so episodes can continue.
            mask = avail.copy()
        # If still empty (no available topics): all-invalid — caller/env handles penalties.
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
            self.prior_strength = float(params["prior_strength"])
            self.availability_rate = float(params["availability_rate"])
        if "prior_strength" in opts:
            self.prior_strength = float(opts["prior_strength"])
        if "availability_rate" in opts:
            self.availability_rate = float(opts["availability_rate"])

        self._state = self.simulator.initial_state(
            self._rng,
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
            "prior_strength": self.prior_strength,
            "availability_rate": self.availability_rate,
            "action_mask": self.available_action_mask(),
            "domain": "se_simulation",
            "synthetic": True,
            "protocol": PROTOCOL_VERSION,
            "topics": list(ORDERED_TOPICS),
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
                }
            )
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
        truncated = self._steps >= self.cfg.max_episode_steps
        if truncated:
            self._termination_reason = "max_episode_steps"
        # Terminate early if every available topic is mastered and mask collapsed
        # (reopen rule still allows practice; optional natural end when all available mastered
        # and we choose not to reopen — we reopen, so primarily truncate on horizon.)
        avail = self._state.available > 0.5
        if avail.any() and bool((self._state.mastery[avail] >= self.cfg.mastery_threshold).all()):
            # Still reopen in mask; do not force terminate — horizon is primary.
            pass
        if not avail.any():
            terminated = True
            self._termination_reason = "no_available_topics"

        mean_now = float(self._state.mastery[avail].mean()) if avail.any() else 0.0
        total_now = float(self._state.mastery.sum())
        total_init = float(self._initial_mastery.sum())
        mean_init = float(self._initial_mastery[self._initial_mastery > -1].mean())  # all slots
        # mean over initially available pattern stored in mastery where >0 or use avail
        init_avail = self._initial_mastery  # unavailable were 0; mean over all catalogue
        info.update(
            {
                "action_mask": self.available_action_mask(),
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
        # silence unused
        _ = (mean_init, init_avail)
        return self._obs(), float(reward), terminated, truncated, info


def make_env(
    cfg: SeEnvConfig | None = None,
    *,
    scenario: str = "sim_train",
    seed: int | None = None,
) -> SePathSimEnv:
    return SePathSimEnv(cfg, scenario=scenario, seed=seed)
