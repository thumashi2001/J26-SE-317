"""Comparison baselines sharing the same action space and invalid-action rules.

Mask usage
----------
Heuristic / random / recent-performance controls **read** ``action_mask`` and only
select valid actions. Vanilla SB3 DQN/PPO do **not** receive that mask at
predict-time; they learn availability through invalid-action penalties.

A separately named ``maskable_ppo`` experiment (sb3-contrib MaskablePPO) trains
and evaluates with masks; it is not the same as inference-only remapping.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Protocol

import numpy as np

from .environment import AdaptivePracticeEnv

COMPARISON_ALGORITHMS = (
    "dqn",
    "ppo",
    "weakest_mastery",
    "random_valid",
    "recent_performance",
)

COMPARISON_LABELS = {
    "dqn": "DQN (SB3; availability via invalid-action penalties, no action mask)",
    "ppo": "PPO (SB3; availability via invalid-action penalties, no action mask)",
    "weakest_mastery": (
        "Weakest-mastery heuristic (lowest current mastery among masked-valid skills)"
    ),
    "random_valid": (
        "Random-valid control (uniform among masked-valid actions; explicitly seeded)"
    ),
    "recent_performance": (
        "Recent-performance baseline (lowest rolling accuracy over prior observed "
        "responses in-episode; masked-valid only)"
    ),
    "maskable_ppo": (
        "MaskablePPO (sb3-contrib; masks used in training and evaluation — separate experiment)"
    ),
}

COMPARISON_NOTES = {
    "mask_vs_penalty": (
        "weakest_mastery, random_valid, and recent_performance use valid-action masks. "
        "Vanilla DQN/PPO learn unavailable actions only through penalties; "
        "invalid actions are not silently remapped."
    ),
    "recent_performance_defined": (
        "recent_performance uses a rolling window of previously observed correct/incorrect "
        "responses per skill within the episode only. Cold-start prefers untried valid "
        "skills (lowest action index). Ties break by lowest action index. "
        "This is distinct from weakest_mastery (current mastery) and random_valid."
    ),
    "maskable_ppo_separate": (
        "maskable_ppo is opt-in and uses sb3_contrib.MaskablePPO with action_masks() "
        "during learn and predict. Do not describe inference-only remapping as masked training."
    ),
    "legacy_alias": (
        "Older smoke runs labelled rule_based and lowest_first used the same "
        "weakest-mastery heuristic (alias). New runs report weakest_mastery once."
    ),
    "mastery_metrics": (
        "selected_skill_mastery_gain_sum accumulates per-step gains on the chosen skill only. "
        "mean_mastery_delta_final_minus_initial and total_mastery_delta_final_minus_initial "
        "compare end vs start mastery across all skills (includes forgetting)."
    ),
}

DEFAULT_RECENT_WINDOW = 5


class Policy(Protocol):
    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int: ...


class WeakestMasteryBaseline:
    """Practice the skill with the lowest current mastery among available actions."""

    uses_action_mask = True
    comparison_key = "weakest_mastery"

    def __init__(self, n_skills: int):
        self.n_skills = n_skills

    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int:
        mastery = observation[: self.n_skills]
        mask = action_mask if action_mask is not None else np.ones(self.n_skills, dtype=bool)
        avail = np.asarray(mask[: self.n_skills], dtype=bool).copy()
        if not avail.any():
            return 0
        scores = np.where(avail, mastery, np.inf)
        return int(np.argmin(scores))

    def reset_episode(self) -> None:
        return None

    def observe_transition(self, info: dict[str, Any]) -> None:
        return None


RuleBasedBaseline = WeakestMasteryBaseline


class LowestPerformanceFirstBaseline(WeakestMasteryBaseline):
    """Deprecated alias of WeakestMasteryBaseline — not an independent method."""

    comparison_key = "weakest_mastery"


class RandomValidBaseline:
    """Uniform random policy over currently valid (masked) actions."""

    uses_action_mask = True
    comparison_key = "random_valid"

    def __init__(self, seed: int = 0):
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)

    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int:
        mask = action_mask if action_mask is not None else np.ones(1, dtype=bool)
        valid = np.flatnonzero(np.asarray(mask, dtype=bool))
        if len(valid) == 0:
            return 0
        return int(self.rng.choice(valid))

    def reset_episode(self) -> None:
        return None

    def observe_transition(self, info: dict[str, Any]) -> None:
        return None


class RecentPerformanceBaseline:
    """Lowest rolling accuracy over previously observed in-episode responses.

    Cold-start: among masked-valid skills with **no** prior observed responses this
    episode, prefer those (untried). Tie-break: lowest action index.

    When all valid skills have history, choose the lowest rolling mean accuracy
    over the last ``window`` observed responses for that skill; ties → lowest index.

    Distinct from ``weakest_mastery`` (uses current mastery vector) and
    ``random_valid`` (uniform among valid).
    """

    uses_action_mask = True
    comparison_key = "recent_performance"

    def __init__(self, n_skills: int, window: int = DEFAULT_RECENT_WINDOW):
        self.n_skills = int(n_skills)
        self.window = int(window)
        self._history: dict[int, deque[int]] = defaultdict(lambda: deque(maxlen=self.window))

    def reset_episode(self) -> None:
        self._history = defaultdict(lambda: deque(maxlen=self.window))

    def observe_transition(self, info: dict[str, Any]) -> None:
        if info.get("invalid_action"):
            return
        if info.get("correct") is None:
            return
        action = info.get("action")
        if action is None or int(action) >= self.n_skills:
            return
        self._history[int(action)].append(int(info["correct"]))

    def _rolling_accuracy(self, skill: int) -> float | None:
        hist = self._history.get(skill)
        if not hist:
            return None
        return float(sum(hist) / len(hist))

    def predict(self, observation: np.ndarray, action_mask: np.ndarray | None = None) -> int:
        mask = action_mask if action_mask is not None else np.ones(self.n_skills, dtype=bool)
        valid = [i for i in range(self.n_skills) if bool(mask[i])]
        if not valid:
            return 0
        untried = [i for i in valid if self._rolling_accuracy(i) is None]
        if untried:
            return int(min(untried))  # cold-start: lowest-index untried valid skill
        # All have history: lowest rolling accuracy; tie -> lowest index
        best = valid[0]
        best_acc = self._rolling_accuracy(best)
        assert best_acc is not None
        for i in valid[1:]:
            acc = self._rolling_accuracy(i)
            assert acc is not None
            if acc < best_acc - 1e-12 or (abs(acc - best_acc) <= 1e-12 and i < best):
                best, best_acc = i, acc
        return int(best)


def rollout_policy(
    env: AdaptivePracticeEnv,
    policy: Any,
    *,
    episodes: int,
    seed: int,
    seed_fn=None,
) -> list[dict]:
    """Roll out a policy; ``seed_fn(episode)`` overrides per-episode reset seeds when set."""
    results = []
    for ep in range(episodes):
        ep_seed = seed_fn(ep) if seed_fn is not None else seed + ep
        if hasattr(policy, "reset_episode"):
            policy.reset_episode()
        obs, info = env.reset(seed=ep_seed)
        done = False
        total_r = 0.0
        selected_skill_gain_sum = 0.0
        invalid = 0
        valid_practice = 0
        steps = 0
        corrects = 0
        answers = 0
        start_mean = float(info.get("initial_mean_mastery", obs[: env.simulator.n_skills].mean()))
        start_total = float(info.get("initial_total_mastery", obs[: env.simulator.n_skills].sum()))
        while not done:
            mask = info.get("action_mask")
            action = policy.predict(obs, mask)
            obs, reward, terminated, truncated, info = env.step(action)
            if hasattr(policy, "observe_transition"):
                policy.observe_transition(info)
            total_r += reward
            steps += 1
            if info.get("invalid_action"):
                invalid += 1
            else:
                valid_practice += 1
                selected_skill_gain_sum += float(
                    info.get("selected_skill_mastery_gain") or info.get("mastery_gain") or 0.0
                )
                if info.get("correct") is not None:
                    answers += 1
                    corrects += int(info["correct"])
            done = terminated or truncated
        end_mean = float(obs[: env.simulator.n_skills].mean())
        end_total = float(obs[: env.simulator.n_skills].sum())
        results.append(
            {
                "episode": ep,
                "episode_seed": ep_seed,
                "return": total_r,
                "steps": steps,
                "valid_practice_count": valid_practice,
                # Accurate label: cumulative gain on the *selected* skill only.
                "selected_skill_mastery_gain_sum": selected_skill_gain_sum,
                "mastery_gain_sum": selected_skill_gain_sum,  # legacy alias
                "mean_mastery_delta_final_minus_initial": end_mean - start_mean,
                "total_mastery_delta_final_minus_initial": end_total - start_total,
                "mean_mastery_delta": end_mean - start_mean,  # legacy alias
                "invalid_action_rate": invalid / max(1, steps),
                "path_efficiency": selected_skill_gain_sum / max(1, steps),
                "time_cost_proxy_steps": steps,
                "correct_rate": (corrects / answers) if answers else None,
                "env_protocol_version": info.get("env_protocol_version"),
            }
        )
    return results
