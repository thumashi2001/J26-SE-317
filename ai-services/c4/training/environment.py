"""Gymnasium-compatible adaptive practice environment (protocol c4-env-eval-v1.1)."""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .config import EnvConfig, SIMULATION_ONLY_ACTIVITY_TYPES
from .protocol import ENV_PROTOCOL_VERSION, scenario_prior_strength
from .simulator import LearnerSimState, Simulator


class AdaptivePracticeEnv(gym.Env):
    """
    Discrete actions = practice a catalogue skill (and optional simulation-only activities).

    Invalid actions receive an explicit penalty and do NOT remap to another skill.

    Timing (v1.1)
    -------------
    ``_steps`` / observation ``elapsed_env_step_frac`` advance on **every** env step,
    including invalid actions. ``LearnerSimState.step`` counts learner interactions
    only (valid practice transitions) and is exposed separately in ``info``.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        simulator: Simulator,
        env_config: EnvConfig | None = None,
        *,
        scenario: str = "default",
        prior_strength: float | None = None,
        seed: int | None = None,
    ):
        super().__init__()
        self.simulator = simulator
        self.cfg = env_config or simulator.env_config
        self.scenario = scenario
        self.prior_strength = (
            float(prior_strength)
            if prior_strength is not None
            else scenario_prior_strength(scenario, 0.4)
        )
        self._skill_actions = list(simulator.skill_list)
        self._extra_actions: list[str] = []
        if self.cfg.include_simulation_only_actions:
            self._extra_actions = list(SIMULATION_ONLY_ACTIVITY_TYPES)

        self.action_labels = self._skill_actions + self._extra_actions
        self.n_actions = len(self.action_labels)
        # Observation: [mastery_1..K, mean_mastery, frac_mastered, elapsed_env_step_frac, prior_strength]
        # Dimension unchanged from v1.0 for checkpoint load compatibility.
        self.obs_dim = self.simulator.n_skills + 4
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.obs_dim,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(self.n_actions)

        self._state: LearnerSimState | None = None
        self._initial_mastery: np.ndarray | None = None
        self._episode_return = 0.0
        self._invalid_actions = 0
        self._steps = 0  # elapsed environment steps (includes invalid)
        self.env_protocol_version = ENV_PROTOCOL_VERSION
        # Seed via Gymnasium so reset/constructor share np_random.
        super().reset(seed=seed)
        self._rng = self.np_random

    def action_catalogue(self) -> list[dict[str, Any]]:
        cat = []
        for i, label in enumerate(self.action_labels):
            kind = "assistments_skill_practice" if i < len(self._skill_actions) else "simulation_only_assumption"
            cat.append(
                {
                    "action_id": i,
                    "label": label,
                    "kind": kind,
                    "real_assistments_support": kind == "assistments_skill_practice",
                }
            )
        return cat

    def available_action_mask(self, state: LearnerSimState | None = None) -> np.ndarray:
        st = state if state is not None else self._state
        assert st is not None
        mask = np.ones(self.n_actions, dtype=bool)
        for i in range(len(self._skill_actions)):
            if st.skill_mastery[i] >= self.cfg.mastery_threshold:
                mask[i] = False
        if not mask.any():
            mask[: len(self._skill_actions)] = True
        return mask

    def action_masks(self) -> np.ndarray:
        """sb3-contrib MaskablePPO API: True = valid action."""
        return self.available_action_mask()

    def _obs(self, state: LearnerSimState) -> np.ndarray:
        mastery = state.skill_mastery.astype(np.float32)
        mean_m = float(mastery.mean())
        frac_m = float((mastery >= self.cfg.mastery_threshold).mean())
        # v1.1: elapsed *environment* time, consistent on invalid transitions.
        step_frac = float(min(1.0, self._steps / max(1, self.cfg.max_episode_steps)))
        extras = np.asarray(
            [mean_m, frac_m, step_frac, float(self.prior_strength)], dtype=np.float32
        )
        return np.concatenate([mastery, extras], axis=0)

    def _timing_info(self) -> dict[str, Any]:
        assert self._state is not None
        return {
            "elapsed_env_steps": int(self._steps),
            "learner_interaction_count": int(self._state.step),
            "elapsed_env_step_frac": float(
                min(1.0, self._steps / max(1, self.cfg.max_episode_steps))
            ),
            "env_protocol_version": self.env_protocol_version,
        }

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self._rng = self.np_random
        opts = options or {}
        if "scenario" in opts:
            self.scenario = str(opts["scenario"])
        if "prior_strength" in opts:
            self.prior_strength = float(opts["prior_strength"])
        else:
            # Scenario name applies a preset; it is not a held-out learner split.
            self.prior_strength = scenario_prior_strength(self.scenario, self.prior_strength)
        self._state = self.simulator.initial_state(self._rng, prior_strength=self.prior_strength)
        self._initial_mastery = self._state.skill_mastery.copy()
        self._episode_return = 0.0
        self._invalid_actions = 0
        self._steps = 0
        info = {
            "scenario": self.scenario,
            "prior_strength": self.prior_strength,
            "action_mask": self.available_action_mask(self._state),
            "data_kind": "synthetic_simulator_episode",
            "initial_mean_mastery": float(self._initial_mastery.mean()),
            "initial_total_mastery": float(self._initial_mastery.sum()),
            **self._timing_info(),
        }
        return self._obs(self._state), info

    def step(self, action: int):
        assert self._state is not None
        assert self._initial_mastery is not None
        action = int(action)
        mask = self.available_action_mask(self._state)
        terminated = False
        truncated = False

        def _finish(reward: float, info: dict[str, Any]):
            nonlocal terminated, truncated
            self._episode_return += reward
            self._steps += 1
            truncated = self._steps >= self.cfg.max_episode_steps
            mastered = float((self._state.skill_mastery >= self.cfg.mastery_threshold).mean())
            if mastered >= 1.0:
                terminated = True
            mean_now = float(self._state.skill_mastery.mean())
            total_now = float(self._state.skill_mastery.sum())
            info.update(
                {
                    "action_mask": self.available_action_mask(self._state),
                    "episode_return": self._episode_return,
                    "invalid_action_count": self._invalid_actions,
                    "mean_mastery": mean_now,
                    "frac_mastered": mastered,
                    "mean_mastery_delta_final_minus_initial": mean_now
                    - float(self._initial_mastery.mean()),
                    "total_mastery_delta_final_minus_initial": total_now
                    - float(self._initial_mastery.sum()),
                    **self._timing_info(),
                }
            )
            return self._obs(self._state), float(reward), terminated, truncated, info

        if action < 0 or action >= self.n_actions:
            self._invalid_actions += 1
            return _finish(
                self.cfg.invalid_action_penalty,
                {
                    "invalid_action": True,
                    "reason": "out_of_range",
                    "action": action,
                    "action_mask": mask,
                    "selected_skill_mastery_gain": 0.0,
                    "correct": None,
                },
            )

        if not mask[action]:
            self._invalid_actions += 1
            return _finish(
                self.cfg.invalid_action_penalty,
                {
                    "invalid_action": True,
                    "reason": "masked_unavailable",
                    "action": action,
                    "action_label": self.action_labels[action],
                    "action_mask": mask,
                    "selected_skill_mastery_gain": 0.0,
                    "mastery_gain": 0.0,  # legacy key; prefer selected_skill_mastery_gain
                    "correct": None,
                },
            )

        if action >= len(self._skill_actions):
            weakest = int(np.argmin(self._state.skill_mastery))
            before = self._state.skill_mastery.copy()
            self._state.skill_mastery[weakest] = np.clip(
                self._state.skill_mastery[weakest] + 0.5 * self.cfg.assumed_mastery_gain_correct,
                0.0,
                1.0,
            )
            self._state.step += 1  # learner interaction
            selected_gain = float(self._state.skill_mastery[weakest] - before[weakest])
            # Net change across all skills (forgetting not applied on this branch).
            reward = (
                self.cfg.mastery_gain_weight * float(self._state.skill_mastery.sum() - before.sum())
                - self.cfg.time_cost_weight
            )
            info = {
                "invalid_action": False,
                "simulation_only_action": True,
                "action": action,
                "action_label": self.action_labels[action],
                "assumed_effect_on_skill": self._skill_actions[weakest],
                "selected_skill_mastery_gain": selected_gain,
                "mastery_gain": selected_gain,
                "correct": None,
                "not_assistments_evidence": True,
            }
            return _finish(reward, info)

        before_all = self._state.skill_mastery.copy()
        self._state, sim_info = self.simulator.step(self._state, action, self._rng)
        selected_gain = float(sim_info["mastery_gain"])
        reward = (
            self.cfg.correctness_reward_weight * float(sim_info["correct"])
            + self.cfg.mastery_gain_weight * selected_gain
            - self.cfg.time_cost_weight
        )
        info = {
            "invalid_action": False,
            "simulation_only_action": False,
            **sim_info,
            "action": action,
            "action_label": self.action_labels[action],
            "selected_skill_mastery_gain": selected_gain,
            "total_mastery_delta_step": float(self._state.skill_mastery.sum() - before_all.sum()),
        }
        return _finish(reward, info)


def make_env(
    simulator: Simulator,
    env_config: EnvConfig | None = None,
    **kwargs,
) -> AdaptivePracticeEnv:
    return AdaptivePracticeEnv(simulator, env_config=env_config, **kwargs)
