"""Rule baselines. Practice-only rules are kept. weakest_multi can use all three types."""

from __future__ import annotations

import numpy as np

from training_se_v2.multi_action.baselines import recent_performance, weakest_practice
from training_se_v2.multi_action.contract import decode_action, encode_action

__all__ = ["WeakestMulti", "recent_performance", "weakest_practice"]


class WeakestMulti:
    """On the current weakest eligible topic, cycle practice, revision, then quiz.

    Uses the same mask and mastery vector as the other rules, plus this rule's
    own action counts. It does not see a hidden learner latent.
    """

    def __init__(self) -> None:
        self.used: dict[int, set[str]] = {}

    def reset_episode(self) -> None:
        self.used = {}

    def action(self, mastery: np.ndarray, mask: np.ndarray) -> int:
        options: dict[int, set[str]] = {}
        for raw in np.flatnonzero(mask):
            kind, topic = decode_action(int(raw))
            if kind == "coding":
                continue
            options.setdefault(int(topic), set()).add(kind)
        if not options:
            raise RuntimeError("no eligible actions")
        topic = sorted(options, key=lambda item: (float(mastery[item]), item))[0]
        used = self.used.setdefault(topic, set())
        for kind in ("practice", "revision", "quiz"):
            if kind in options[topic] and kind not in used:
                used.add(kind)
                return encode_action(kind, topic)
        for kind in ("practice", "revision", "quiz"):
            if kind in options[topic]:
                return encode_action(kind, topic)
        return int(np.flatnonzero(mask)[0])
