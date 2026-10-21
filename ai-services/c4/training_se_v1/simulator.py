"""Synthetic SE learner dynamics for se-path-sim-v1 (semester-aware availability)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .catalogue import N_TOPICS, semester_eligibility_mask
from .config import SeEnvConfig


@dataclass
class SeLearnerState:
    mastery: np.ndarray
    available: np.ndarray
    semester: str
    attempt_count: int = 0


class SeSyntheticSimulator:
    def __init__(self, cfg: SeEnvConfig | None = None):
        self.cfg = cfg or SeEnvConfig()
        self.cfg.validate()

    def initial_state(
        self,
        rng: np.random.Generator,
        *,
        semester: str,
        prior_strength: float,
        availability_rate: float,
    ) -> SeLearnerState:
        """Generate an explicit synthetic learner state (not a live user)."""
        eligible = np.asarray(semester_eligibility_mask(semester), dtype=np.float32)
        # Within-semester topic availability sample
        within = (rng.random(N_TOPICS) < float(availability_rate)).astype(np.float32)
        avail = (eligible * within).astype(np.float32)
        if not avail.any():
            # Safe fallback: enable one random semester-eligible topic
            idxs = np.flatnonzero(eligible > 0.5)
            avail[int(rng.choice(idxs))] = 1.0
        low, high = self.cfg.initial_mastery_low, self.cfg.initial_mastery_high
        raw = rng.uniform(low, high, size=N_TOPICS).astype(np.float32)
        mastery = (0.5 * raw + 0.5 * float(prior_strength)).astype(np.float32)
        mastery = np.clip(mastery, 0.0, 1.0)
        mastery = np.where(avail > 0.5, mastery, 0.0).astype(np.float32)
        return SeLearnerState(
            mastery=mastery, available=avail, semester=semester, attempt_count=0
        )

    def p_correct(self, mastery: float) -> float:
        c = self.cfg
        return float(np.clip(c.p_floor + c.p_slope * mastery, c.p_floor, c.p_ceil))

    def step_attempt(
        self,
        state: SeLearnerState,
        topic_index: int,
        rng: np.random.Generator,
    ) -> tuple[SeLearnerState, dict]:
        i = int(topic_index)
        if i < 0 or i >= N_TOPICS:
            raise IndexError(i)
        if state.available[i] < 0.5:
            raise ValueError("attempt on unavailable topic")
        m_before = float(state.mastery[i])
        p = self.p_correct(m_before)
        correct = bool(rng.random() < p)
        gain = (
            self.cfg.mastery_gain_correct if correct else self.cfg.mastery_gain_incorrect
        )
        mastery = state.mastery.copy()
        mastery[i] = float(np.clip(m_before + gain, 0.0, 1.0))
        if self.cfg.forgetting_per_other_topic != 0.0:
            raise RuntimeError("unexpected forgetting in se-path-sim-v1")
        new_state = SeLearnerState(
            mastery=mastery,
            available=state.available.copy(),
            semester=state.semester,
            attempt_count=state.attempt_count + 1,
        )
        return new_state, {
            "correct": correct,
            "p_correct": p,
            "selected_topic_index": i,
            "mastery_before": m_before,
            "mastery_after": float(mastery[i]),
            "selected_topic_gain": float(mastery[i] - m_before),
            "step_kind": "synthetic_practice_attempt",
            "semester": state.semester,
        }
