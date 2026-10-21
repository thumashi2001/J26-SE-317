"""Baselines for se-path-sim-v0.

Naming vs Node ``weakest_stored_mastery_v1``
-------------------------------------------
Node heuristic ranks C1 twin/insights scores (0–100) among practiseable topics
present on the twin. This simulator baseline
``weakest_stored_mastery_v1_sim`` ranks **simulator observation mastery** ([0,1])
among **masked-valid** actions. Same ranking idea; different state source
(synthetic vector, not live C1 insights). Do not claim identical semantics.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

import numpy as np

from .catalogue import N_TOPICS
from .environment import SePathSimEnv
from .observation import mastery_from_obs

DEFAULT_RECENT_WINDOW = 5

COMPARISON_LABELS = {
    "maskable_ppo": (
        "MaskablePPO (sb3-contrib; masks in training and evaluation)"
    ),
    "weakest_stored_mastery_v1_sim": (
        "Weakest mastery among masked-valid topics using simulator obs mastery "
        "(compatible ranking rule with Node weakest_stored_mastery_v1; "
        "state source differs — synthetic obs, not C1 insights)"
    ),
    "random_valid": "Uniform random among masked-valid actions (separate RNG stream)",
    "recent_performance": (
        "Lowest rolling in-episode attempt accuracy; cold-start = lowest-index untried valid"
    ),
}


class WeakestStoredMasteryV1SimBaseline:
    uses_action_mask = True
    comparison_key = "weakest_stored_mastery_v1_sim"

    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int:
        mastery = mastery_from_obs(observation)
        mask = (
            np.asarray(action_mask, dtype=bool)
            if action_mask is not None
            else np.ones(N_TOPICS, dtype=bool)
        )
        avail = mask.copy()
        if not avail.any():
            return 0
        scores = np.where(avail, mastery, np.inf)
        # Tie-break: lowest index (np.argmin)
        return int(np.argmin(scores))

    def reset_episode(self) -> None:
        return None

    def observe_transition(self, info: dict[str, Any]) -> None:
        return None


class RandomValidBaseline:
    uses_action_mask = True
    comparison_key = "random_valid"

    def __init__(self, seed: int):
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)

    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int:
        mask = (
            np.asarray(action_mask, dtype=bool)
            if action_mask is not None
            else np.ones(N_TOPICS, dtype=bool)
        )
        valid = np.flatnonzero(mask)
        if len(valid) == 0:
            return 0
        return int(self.rng.choice(valid))

    def reset_episode(self) -> None:
        return None

    def observe_transition(self, info: dict[str, Any]) -> None:
        return None


class RecentPerformanceBaseline:
    uses_action_mask = True
    comparison_key = "recent_performance"

    def __init__(self, window: int = DEFAULT_RECENT_WINDOW):
        self.window = int(window)
        self._history: dict[int, deque[int]] = defaultdict(
            lambda: deque(maxlen=self.window)
        )

    def reset_episode(self) -> None:
        self._history = defaultdict(lambda: deque(maxlen=self.window))

    def observe_transition(self, info: dict[str, Any]) -> None:
        if info.get("invalid_action"):
            return
        if info.get("correct") is None:
            return
        action = info.get("action")
        if action is None:
            return
        self._history[int(action)].append(int(bool(info["correct"])))

    def _acc(self, i: int) -> float | None:
        h = self._history.get(i)
        if not h:
            return None
        return float(sum(h) / len(h))

    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int:
        mask = (
            np.asarray(action_mask, dtype=bool)
            if action_mask is not None
            else np.ones(N_TOPICS, dtype=bool)
        )
        valid = [i for i in range(N_TOPICS) if mask[i]]
        if not valid:
            return 0
        untried = [i for i in valid if self._acc(i) is None]
        if untried:
            return int(min(untried))
        best = valid[0]
        best_acc = self._acc(best)
        assert best_acc is not None
        for i in valid[1:]:
            acc = self._acc(i)
            assert acc is not None
            if acc < best_acc - 1e-12 or (abs(acc - best_acc) <= 1e-12 and i < best):
                best, best_acc = i, acc
        return int(best)


def rollout_policy(
    env: SePathSimEnv,
    policy: Any,
    *,
    episodes: int,
    seed_fn,
) -> list[dict]:
    results = []
    for ep in range(episodes):
        ep_seed = seed_fn(ep)
        if hasattr(policy, "reset_episode"):
            policy.reset_episode()
        obs, info = env.reset(seed=ep_seed)
        ep_ret = 0.0
        selected_gain = 0.0
        invalid = 0
        valid_n = 0
        term_reason = ""
        while True:
            mask = info.get("action_mask")
            if hasattr(policy, "predict"):
                # MaskablePPO needs action_masks kw
                try:
                    action = policy.predict(obs, action_mask=mask)
                except TypeError:
                    action, _ = policy.predict(obs, action_masks=mask, deterministic=True)
                    action = int(action)
            else:
                action = 0
            if not isinstance(action, (int, np.integer)):
                action = int(action)
            obs, reward, terminated, truncated, info = env.step(int(action))
            if hasattr(policy, "observe_transition"):
                policy.observe_transition(info)
            ep_ret += float(reward)
            if info.get("invalid_action"):
                invalid += 1
            else:
                valid_n += 1
                selected_gain += float(info.get("selected_topic_gain") or 0.0)
            if terminated or truncated:
                term_reason = info.get("termination_reason") or (
                    "truncated" if truncated else "terminated"
                )
                break
        results.append(
            {
                "episode_seed": ep_seed,
                "return": ep_ret,
                "selected_topic_mastery_gain_sum": selected_gain,
                "net_total_mastery_change": float(
                    info.get("total_mastery_delta_final_minus_initial") or 0.0
                ),
                "net_mean_mastery_change": float(
                    info.get("mean_mastery_delta_final_minus_initial") or 0.0
                ),
                "valid_practice_count": valid_n,
                "invalid_action_rate": invalid / max(1, valid_n + invalid),
                "termination_reason": term_reason,
                "domain": "se_simulation",
                "synthetic": True,
            }
        )
    return results
