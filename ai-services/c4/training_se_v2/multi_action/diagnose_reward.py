"""Train-scenario reward trace for historical se-path-multi-v1.

Does not load a checkpoint and does not use the held-out test seeds (20_000+).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from catalogues.c1_practice_full_2026_10 import N_TOPICS, ORDERED_TOPICS

from .baselines import recent_performance, weakest_practice
from .contract import encode_action
from .environment import MultiActionSimEnv


def _force(env: MultiActionSimEnv, mastery: float) -> None:
    env.reset()
    assert env.state is not None
    mastered = np.zeros(N_TOPICS, dtype=np.float32)
    available = np.zeros(N_TOPICS, dtype=np.float32)
    mastered[0] = mastery
    available[0] = 1.0
    env.state.mastery = mastered
    env.state.available = available


def clip_cases() -> list[dict]:
    rows = []
    env = MultiActionSimEnv(semester="Y3S1", seed=0)
    for kind in ("practice", "revision", "quiz"):
        _force(env, 1.0)
        before = float(env.state.mastery[0])
        action = encode_action(kind, 0)
        _obs, reward, _done, info = env.step(action)
        after = float(env.state.mastery[0])
        rows.append(
            {
                "case": "mastery_at_ceiling",
                "action_type": kind,
                "topic": ORDERED_TOPICS[0],
                "mastery_before": before,
                "mastery_after": after,
                "actual_mastery_delta": after - before,
                "reward": float(reward),
                "reward_minus_actual_delta": float(reward) - (after - before),
                "invalid": bool(info.get("invalid")),
                "duration_steps": 1,
            }
        )
    return rows


def _quiz_highest(mastery: np.ndarray, mask: np.ndarray) -> int:
    from .contract import decode_action

    best = None
    for action in np.flatnonzero(mask):
        kind, topic = decode_action(int(action))
        if kind != "quiz":
            continue
        key = (-float(mastery[topic]), int(topic), int(action))
        if best is None or key < best[0]:
            best = (key, int(action))
    if best is None:
        raise RuntimeError("no quiz")
    return best[1]


def rollout(method: str, *, semester: str, episodes: int) -> dict:
    from .contract import decode_action

    returns = []
    mastery_changes = []
    actual_deltas = []
    rewards = []
    kinds = {"practice": 0, "revision": 0, "quiz": 0, "coding": 0}
    repeats = 0
    zero_progress = 0
    steps = 0
    trace = []
    for ep in range(episodes):
        # Train-scenario seeds. Not the frozen final-test stream.
        env = MultiActionSimEnv(semester=semester, seed=1_000 + ep)
        env.reset()
        assert env.state is not None
        avail = env.state.available > 0.5
        start = float(env.state.mastery[avail].mean())
        seen: set[tuple[str, int]] = set()
        total = 0.0
        done = False
        guard = 0
        while not done and guard < 40:
            guard += 1
            mask = env.mask()
            mastery = env.state.mastery
            if method == "recent_performance":
                action = recent_performance(env.recent_by_topic(), mask)
            elif method == "weakest_practice":
                action = weakest_practice(mastery, mask)
            else:
                action = _quiz_highest(mastery, mask)
            kind, topic = decode_action(action)
            before = float(env.state.mastery[topic])
            _obs, reward, done, info = env.step(action)
            after = float(env.state.mastery[topic])
            delta = after - before
            key = (kind, topic)
            repeated = key in seen
            seen.add(key)
            if repeated:
                repeats += 1
            if abs(delta) < 1e-8 and not info.get("invalid"):
                zero_progress += 1
            kinds[kind] = kinds.get(kind, 0) + 1
            steps += 1
            total += float(reward)
            actual_deltas.append(delta)
            rewards.append(float(reward))
            if ep == 0 and len(trace) < 6:
                trace.append(
                    {
                        "semester": semester,
                        "method": method,
                        "action_type": kind,
                        "topic": ORDERED_TOPICS[topic],
                        "mastery_before": before,
                        "mastery_after": after,
                        "actual_mastery_delta": delta,
                        "reward": float(reward),
                        "repeated": repeated,
                        "duration_steps": 1,
                        "eligible": True,
                    }
                )
        end = float(env.state.mastery[avail].mean())
        returns.append(total)
        mastery_changes.append(end - start)
    return {
        "method": method,
        "semester": semester,
        "episodes": episodes,
        "mean_return": float(np.mean(returns)),
        "mean_mastery_change": float(np.mean(mastery_changes)),
        "mean_reward_per_step": float(np.mean(rewards)),
        "mean_actual_delta_per_step": float(np.mean(actual_deltas)),
        "action_counts": kinds,
        "repeat_rate": repeats / steps,
        "zero_progress_rate": zero_progress / steps,
        "trace": trace,
        "split": "train_scenario_diagnostic",
        "not_final_test": True,
    }


def main() -> None:
    payload = {
        "protocol": "se-path-multi-v1",
        "note": "Historical reward. Not a new protocol and not the held-out test.",
        "ceiling_steps": clip_cases(),
        "rollouts": [
            rollout(method, semester=semester, episodes=3)
            for semester in ("Y3S1", "Y3S2")
            for method in ("recent_performance", "weakest_practice", "quiz_highest_mastery")
        ],
    }
    out = Path(__file__).resolve().parents[2] / "experiments" / "diagnostics" / "se_path_multi_v1_reward_trace.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"ceiling_steps": payload["ceiling_steps"], "rollouts": [
        {k: v for k, v in row.items() if k != "trace"} for row in payload["rollouts"]
    ]}, indent=2))


if __name__ == "__main__":
    main()
