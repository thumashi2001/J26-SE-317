"""Synthetic SE learner dynamics (se-path-sim-v0).

Partial observability
---------------------
Affects transitions but **hidden** from the policy observation:
  - underlying Bernoulli draw for correctness (only outcome observed via reward/info)
  - configured p_floor / p_slope / gains (known at train time via config, not in obs)

Observed: mastery and availability vectors, mean/frac, step_frac, prior_strength.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .catalogue import N_TOPICS
from .config import SeEnvConfig


@dataclass
class SeLearnerState:
    mastery: np.ndarray  # float32 [N], meaningful where available
    available: np.ndarray  # float32 [N] in {0,1}
    attempt_count: int = 0


class SeSyntheticSimulator:
    def __init__(self, cfg: SeEnvConfig | None = None):
        self.cfg = cfg or SeEnvConfig()
        self.cfg.validate()

    def initial_state(
        self,
        rng: np.random.Generator,
        *,
        prior_strength: float,
        availability_rate: float,
    ) -> SeLearnerState:
        avail = (rng.random(N_TOPICS) < float(availability_rate)).astype(np.float32)
        if not avail.any():
            avail[int(rng.integers(0, N_TOPICS))] = 1.0
        # Initial mastery around prior_strength with noise, only for available topics
        low, high = self.cfg.initial_mastery_low, self.cfg.initial_mastery_high
        raw = rng.uniform(low, high, size=N_TOPICS).astype(np.float32)
        # Blend toward prior_strength
        mastery = (0.5 * raw + 0.5 * float(prior_strength)).astype(np.float32)
        mastery = np.clip(mastery, 0.0, 1.0)
        mastery = np.where(avail > 0.5, mastery, 0.0).astype(np.float32)
        return SeLearnerState(mastery=mastery, available=avail, attempt_count=0)

    def p_correct(self, mastery: float) -> float:
        c = self.cfg
        return float(np.clip(c.p_floor + c.p_slope * mastery, c.p_floor, c.p_ceil))

    def step_attempt(
        self,
        state: SeLearnerState,
        topic_index: int,
        rng: np.random.Generator,
    ) -> tuple[SeLearnerState, dict]:
        """One practice attempt on topic_index. Requires topic available."""
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
        # Forgetting frozen at 0.0 — no other-topic updates
        if self.cfg.forgetting_per_other_topic != 0.0:
            raise RuntimeError("unexpected forgetting in se-path-sim-v0")

        new_state = SeLearnerState(
            mastery=mastery,
            available=state.available.copy(),
            attempt_count=state.attempt_count + 1,
        )
        selected_gain = float(mastery[i] - m_before)
        info = {
            "correct": correct,
            "p_correct": p,
            "selected_topic_index": i,
            "mastery_before": m_before,
            "mastery_after": float(mastery[i]),
            "selected_topic_gain": selected_gain,
            "step_kind": "synthetic_practice_attempt",
        }
        return new_state, info
