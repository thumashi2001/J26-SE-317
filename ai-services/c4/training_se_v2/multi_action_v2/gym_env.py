"""Gymnasium wrapper for se-path-multi-v2. Masks are read during training."""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .contract import N_ACTIONS, OBS_DIM, PROTOCOL
from .environment import MultiActionSimEnvV2
from .objective import training_episode_rng_seed, training_semester


class MultiActionGymEnvV2(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        semester: str = "Y3S1",
        seed: int = 0,
        schedule_training: bool = False,
        train_seed: int | None = None,
    ):
        super().__init__()
        if semester not in ("Y3S1", "Y3S2"):
            raise ValueError("semester must be Y3S1 or Y3S2")
        self.semester = semester
        self.schedule_training = False
        self.train_seed = int(seed if train_seed is None else train_seed)
        self._episode_index = 0
        self._episode_open = False
        self.coverage = {
            "Y3S1": {"episodes": 0, "steps": 0},
            "Y3S2": {"episodes": 0, "steps": 0},
        }
        self.core = MultiActionSimEnvV2(semester=semester, seed=seed)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = spaces.Discrete(N_ACTIONS)
        self.mask_calls = 0
        super().reset(seed=seed)
        self.schedule_training = bool(schedule_training)
        self._episode_index = 0

    def action_masks(self) -> np.ndarray:
        self.mask_calls += 1
        if self.core.state is None:
            return np.zeros(N_ACTIONS, dtype=bool)
        return self.core.mask()

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        opts = options or {}
        self._episode_open = False
        if self.schedule_training and "semester" not in opts:
            episode_index = self._episode_index
            self._episode_index += 1
            semester = training_semester(episode_index)
            rng_seed = training_episode_rng_seed(self.train_seed, episode_index)
        else:
            semester = str(opts.get("semester", self.semester))
            rng_seed = int(seed if seed is not None else self.train_seed)
        if semester not in ("Y3S1", "Y3S2"):
            raise ValueError("semester must be Y3S1 or Y3S2")
        super().reset(seed=rng_seed)
        self.semester = semester
        self.core.semester = semester
        episode_rng = np.random.default_rng(rng_seed)
        if "exam_urgency" in opts:
            self.core._next_exam_urgency = opts["exam_urgency"]
        elif float(episode_rng.random()) < 0.25:
            self.core._next_exam_urgency = None
        else:
            self.core._next_exam_urgency = float(episode_rng.random())
        self.core.rng = episode_rng
        obs = self.core.reset()
        for _ in range(4):
            if self.action_masks().any():
                break
            obs = self.core.reset()
        return obs, self._info()

    def _info(self) -> dict:
        assert self.core.state is not None
        return {
            "action_mask": self.action_masks(),
            "mastery": self.core.state.mastery.copy(),
            "recent_by_topic": self.core.recent_by_topic(),
            "available": self.core.state.available.copy(),
            "synthetic": True,
            "protocol": PROTOCOL,
            "semester": self.semester,
        }

    def step(self, action: int):
        if self.schedule_training:
            if not self._episode_open:
                self.coverage[self.semester]["episodes"] += 1
                self._episode_open = True
            self.coverage[self.semester]["steps"] += 1
        obs, reward, done, info = self.core.step(int(action))
        truncated = bool(done)
        terminated = False
        if info.get("invalid") and not self.action_masks().any():
            terminated = True
            truncated = False
        info = dict(info)
        info.update(self._info())
        return obs, float(reward), terminated, truncated, info
