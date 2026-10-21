"""Gymnasium wrapper so MaskablePPO can train with env.action_masks().

Dynamics stay in MultiActionSimEnv. They are synthetic assumptions.
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .contract import N_ACTIONS, OBS_DIM, PROTOCOL
from .environment import MultiActionSimEnv


class MultiActionGymEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, *, semester: str = "Y3S1", seed: int = 0):
        super().__init__()
        if semester not in ("Y3S1", "Y3S2"):
            raise ValueError("semester must be Y3S1 or Y3S2")
        self.semester = semester
        self.core = MultiActionSimEnv(semester=semester, seed=seed)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = spaces.Discrete(N_ACTIONS)
        self.mask_calls = 0
        super().reset(seed=seed)

    def action_masks(self) -> np.ndarray:
        self.mask_calls += 1
        if self.core.state is None:
            return np.zeros(N_ACTIONS, dtype=bool)
        return self.core.mask()

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        opts = options or {}
        semester = str(opts.get("semester", self.semester))
        if semester not in ("Y3S1", "Y3S2"):
            raise ValueError("semester must be Y3S1 or Y3S2")
        self.semester = semester
        self.core.semester = semester
        self.core.rng = np.random.default_rng(int(self.np_random.integers(0, 2**31 - 1)))
        # Assumption: urgency is sometimes unknown. Not a measured latent.
        if "exam_urgency" in opts:
            self.core._next_exam_urgency = opts["exam_urgency"]
        elif float(self.np_random.random()) < 0.25:
            self.core._next_exam_urgency = None
        else:
            self.core._next_exam_urgency = float(self.np_random.random())
        obs = self.core.reset()
        for _ in range(4):
            if self.action_masks().any():
                break
            obs = self.core.reset()
        info = {
            "action_mask": self.action_masks(),
            "mastery": self.core.state.mastery.copy(),
            "recent_by_topic": self.core.recent_by_topic(),
            "synthetic": True,
            "protocol": PROTOCOL,
            "semester": self.semester,
            "exam_urgency_assumption": self.core.exam_urgency,
        }
        return obs, info

    def step(self, action: int):
        obs, reward, done, info = self.core.step(int(action))
        truncated = bool(done)
        terminated = False
        if info.get("invalid") and not self.action_masks().any():
            terminated = True
            truncated = False
        info = dict(info)
        info["action_mask"] = self.action_masks()
        info["mastery"] = self.core.state.mastery.copy()
        info["recent_by_topic"] = self.core.recent_by_topic()
        info["synthetic"] = True
        return obs, float(reward), terminated, truncated, info
