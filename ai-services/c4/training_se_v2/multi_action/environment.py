"""Synthetic multi-action environment. Dynamics are labelled assumptions, not real students."""

from __future__ import annotations

import numpy as np

from training_se_v1.catalogue import N_TOPICS, semester_eligibility_mask
from training_se_v1.config import SeEnvConfig
from training_se_v1.simulator import SeLearnerState, SeSyntheticSimulator

from .contract import (
    N_ACTIONS,
    OBS_DIM,
    REWARD_DEFINITION_VERSION,
    action_mask,
    build_observation,
    decode_action,
)


class MultiActionSimEnv:
    """One step = one eligible activity. Coding stays masked."""

    def __init__(self, *, semester: str = "Y3S1", seed: int = 0):
        self.semester = semester
        self.cfg = SeEnvConfig()
        self.simulator = SeSyntheticSimulator(self.cfg)
        self.rng = np.random.default_rng(seed)
        self.state: SeLearnerState | None = None
        self.steps = 0
        self.invalid = 0
        self.completed = 0
        self._initial_mean = 0.0
        self._graded_n = 0
        self._graded_correct = 0.0
        self.topic_attempts = np.zeros(N_TOPICS, dtype=np.float32)
        self.topic_correct = np.zeros(N_TOPICS, dtype=np.float32)
        # Assumption, not a measured student value. Gym training overwrites this per episode.
        self._next_exam_urgency: float | None = 0.5
        self.exam_urgency: float | None = 0.5

    def reset(self) -> np.ndarray:
        self.state = self.simulator.initial_state(
            self.rng,
            semester=self.semester,
            prior_strength=0.4,
            availability_rate=0.85,
        )
        # prior_strength here only initialises the SYNTHETIC learner. It is not an observation slot.
        avail = self.state.available > 0.5
        self._initial_mean = float(self.state.mastery[avail].mean()) if avail.any() else 0.0
        self.steps = 0
        self.invalid = 0
        self.completed = 0
        self._graded_n = 0
        self._graded_correct = 0.0
        self.topic_attempts = np.zeros(N_TOPICS, dtype=np.float32)
        self.topic_correct = np.zeros(N_TOPICS, dtype=np.float32)
        self.exam_urgency = self._next_exam_urgency
        return self.observation()

    def _record_grade(self, topic_index: int, correct: bool) -> None:
        self.topic_attempts[topic_index] += 1.0
        self.topic_correct[topic_index] += 1.0 if correct else 0.0
        self._graded_n += 1
        self._graded_correct += 1.0 if correct else 0.0

    def recent_by_topic(self) -> np.ndarray:
        """Per-topic accuracy. 0.5 until that topic has a graded practice or quiz attempt."""
        out = np.full(N_TOPICS, 0.5, dtype=np.float32)
        seen = self.topic_attempts > 0
        out[seen] = self.topic_correct[seen] / self.topic_attempts[seen]
        return out

    def observation(self) -> np.ndarray:
        assert self.state is not None
        recent = None if self._graded_n == 0 else float(self._graded_correct / self._graded_n)
        engagement = (self.completed / self.steps) if self.steps else None
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

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict]:
        assert self.state is not None
        mask = self.mask()
        if action < 0 or action >= N_ACTIONS or not mask[action]:
            self.invalid += 1
            self.steps += 1
            done = self.steps >= self.cfg.max_episode_steps
            return self.observation(), -0.2, done, {
                "invalid": True,
                "reward_definition_version": REWARD_DEFINITION_VERSION,
            }
        kind, topic_index = decode_action(int(action))
        if kind == "coding":
            self.invalid += 1
            self.steps += 1
            return self.observation(), -0.2, self.steps >= self.cfg.max_episode_steps, {"invalid": True}
        before = float(self.state.mastery[topic_index])
        if kind == "practice":
            self.state, step_info = self.simulator.step_attempt(self.state, topic_index, self.rng)
            self._record_grade(topic_index, bool(step_info.get("correct")))
            gain = float(self.state.mastery[topic_index]) - before
            reward = gain
        elif kind == "revision":
            # Assumption: revision yields half the correct-attempt mastery gain, no correctness draw.
            gain = 0.5 * self.cfg.mastery_gain_correct
            mastery = self.state.mastery.copy()
            mastery[topic_index] = float(np.clip(before + gain, 0.0, 1.0))
            self.state = SeLearnerState(
                mastery=mastery,
                available=self.state.available.copy(),
                semester=self.state.semester,
            )
            reward = gain
        else:
            self.state, step_info = self.simulator.step_attempt(self.state, topic_index, self.rng)
            self._record_grade(topic_index, bool(step_info.get("correct")))
            reward = (1.0 if step_info.get("correct") else 0.0) - 0.5
        self.completed += 1
        self.steps += 1
        done = self.steps >= self.cfg.max_episode_steps
        avail = self.state.available > 0.5
        mean_now = float(self.state.mastery[avail].mean()) if avail.any() else 0.0
        return self.observation(), float(reward), done, {
            "invalid": False,
            "kind": kind,
            "topic_index": topic_index,
            "mastery_delta_mean": mean_now - self._initial_mean,
            "reward_definition_version": REWARD_DEFINITION_VERSION,
            "synthetic": True,
        }


def semester_topic_count(semester: str) -> int:
    return int(np.asarray(semester_eligibility_mask(semester), dtype=bool).sum())
