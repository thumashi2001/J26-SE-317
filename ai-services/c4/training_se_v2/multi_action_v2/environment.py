"""se-path-multi-v2 simulator wrapper.

Mastery transitions are the existing synthetic assumptions. The reward is the
clipped mastery change, not a correctness bonus and not an intended gain.
"""

from __future__ import annotations

import numpy as np

from training_se_v1.config import SeEnvConfig
from training_se_v1.simulator import SeLearnerState, SeSyntheticSimulator
from training_se_v2.multi_action.contract import N_TOPICS

from .contract import (
    N_ACTIONS,
    REWARD_DEFINITION_VERSION,
    action_mask,
    build_observation,
    decode_action,
)


class MultiActionSimEnvV2:
    """One step = one action. No separate action duration."""

    def __init__(self, *, semester: str = "Y3S1", seed: int = 0):
        self.semester = semester
        self.cfg = SeEnvConfig()
        self.simulator = SeSyntheticSimulator(self.cfg)
        self.rng = np.random.default_rng(seed)
        self.state: SeLearnerState | None = None
        self.steps = 0
        self.invalid = 0
        self._graded_n = 0
        self._graded_correct = 0.0
        self.topic_attempts = np.zeros(N_TOPICS, dtype=np.float32)
        self.topic_correct = np.zeros(N_TOPICS, dtype=np.float32)
        self.selection_counts: dict[tuple[str, int], int] = {}
        self._next_exam_urgency: float | None = 0.5
        self.exam_urgency: float | None = 0.5
        self.initial_mastery: np.ndarray | None = None

    def reset(self) -> np.ndarray:
        self.state = self.simulator.initial_state(
            self.rng,
            semester=self.semester,
            prior_strength=0.4,
            availability_rate=0.85,
        )
        self.initial_mastery = self.state.mastery.copy()
        self.steps = 0
        self.invalid = 0
        self._graded_n = 0
        self._graded_correct = 0.0
        self.topic_attempts = np.zeros(N_TOPICS, dtype=np.float32)
        self.topic_correct = np.zeros(N_TOPICS, dtype=np.float32)
        self.selection_counts = {}
        self.exam_urgency = self._next_exam_urgency
        return self.observation()

    def _record_grade(self, topic_index: int, correct: bool) -> None:
        self.topic_attempts[topic_index] += 1.0
        self.topic_correct[topic_index] += 1.0 if correct else 0.0
        self._graded_n += 1
        self._graded_correct += 1.0 if correct else 0.0

    def recent_by_topic(self) -> np.ndarray:
        out = np.full(N_TOPICS, 0.5, dtype=np.float32)
        seen = self.topic_attempts > 0
        out[seen] = self.topic_correct[seen] / self.topic_attempts[seen]
        return out

    def observation(self) -> np.ndarray:
        assert self.state is not None
        recent = None if self._graded_n == 0 else float(self._graded_correct / self._graded_n)
        engagement = None if self.steps == 0 else 1.0 - (self.invalid / self.steps)
        return build_observation(
            self.state.mastery,
            self.state.available,
            elapsed_env_steps=self.steps,
            recent_accuracy=recent,
            engagement_completion_rate=engagement,
            exam_urgency=self.exam_urgency,
        )

    def mask(self) -> np.ndarray:
        assert self.state is not None
        return action_mask(
            semester=self.state.semester,
            available=self.state.available,
            mastery=self.state.mastery,
        )

    def _learning_step(self, kind: str, topic_index: int) -> tuple[float, bool | None]:
        assert self.state is not None
        before = float(self.state.mastery[topic_index])
        if kind == "revision":
            # Same assumed update as v1. The reward uses the value after clipping.
            intended = 0.5 * self.cfg.mastery_gain_correct
            mastery = self.state.mastery.copy()
            mastery[topic_index] = float(np.clip(before + intended, 0.0, 1.0))
            self.state = SeLearnerState(
                mastery=mastery,
                available=self.state.available.copy(),
                semester=self.state.semester,
            )
            return float(mastery[topic_index] - before), None
        self.state, info = self.simulator.step_attempt(self.state, topic_index, self.rng)
        self._record_grade(topic_index, bool(info.get("correct")))
        return float(self.state.mastery[topic_index] - before), bool(info.get("correct"))

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict]:
        assert self.state is not None
        mask = self.mask()
        if action < 0 or action >= N_ACTIONS or not bool(mask[action]):
            self.invalid += 1
            self.steps += 1
            done = self.steps >= self.cfg.max_episode_steps
            return self.observation(), -0.2, done, {
                "invalid": True,
                "components": {
                    "learning_delta": 0.0,
                    "invalid_penalty": -0.2,
                    "correctness_bonus": 0.0,
                },
                "reward_definition_version": REWARD_DEFINITION_VERSION,
                "synthetic": True,
            }
        kind, topic_index = decode_action(int(action))
        if kind == "coding":
            self.invalid += 1
            self.steps += 1
            return self.observation(), -0.2, self.steps >= self.cfg.max_episode_steps, {
                "invalid": True,
                "components": {
                    "learning_delta": 0.0,
                    "invalid_penalty": -0.2,
                    "correctness_bonus": 0.0,
                },
                "synthetic": True,
            }
        before = float(self.state.mastery[topic_index])
        delta, correct = self._learning_step(kind, topic_index)
        key = (kind, topic_index)
        self.selection_counts[key] = self.selection_counts.get(key, 0) + 1
        self.steps += 1
        done = self.steps >= self.cfg.max_episode_steps
        return self.observation(), float(delta), done, {
            "invalid": False,
            "kind": kind,
            "topic_index": topic_index,
            "mastery_before": before,
            "mastery_after": before + float(delta),
            "actual_mastery_delta": float(delta),
            "correct": correct,
            "repeated": self.selection_counts[key] > 1,
            "selection_count": self.selection_counts[key],
            "duration_steps": 1,
            "components": {
                "learning_delta": float(delta),
                "invalid_penalty": 0.0,
                "correctness_bonus": 0.0,
            },
            "reward_definition_version": REWARD_DEFINITION_VERSION,
            "synthetic": True,
        }
