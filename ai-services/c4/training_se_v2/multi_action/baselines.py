"""Rule baselines for se-path-multi-v1. Same mask as the learned policy."""

from __future__ import annotations

import numpy as np

from catalogues.c1_practice_full_2026_10 import N_TOPICS

from .contract import decode_action, encode_action


def _masked(mask: np.ndarray) -> np.ndarray:
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        raise RuntimeError("no eligible actions")
    return idx


def random_valid(mask: np.ndarray, rng: np.random.Generator) -> int:
    return int(rng.choice(_masked(mask)))


def weakest_practice(mastery: np.ndarray, mask: np.ndarray) -> int:
    """Lowest mastery among masked practice actions; topic-index tie-break."""
    candidates = []
    for action in _masked(mask):
        kind, topic = decode_action(int(action))
        if kind != "practice":
            continue
        candidates.append((float(mastery[topic]), topic, int(action)))
    if not candidates:
        return int(_masked(mask)[0])
    candidates.sort()
    return candidates[0][2]


def recent_performance(recent_by_topic: np.ndarray, mask: np.ndarray) -> int:
    """Lowest recent accuracy among masked practice actions."""
    candidates = []
    for action in _masked(mask):
        kind, topic = decode_action(int(action))
        if kind != "practice":
            continue
        candidates.append((float(recent_by_topic[topic]), topic, int(action)))
    if not candidates:
        return int(_masked(mask)[0])
    candidates.sort()
    return candidates[0][2]


def practice_action(topic_index: int) -> int:
    return encode_action("practice", topic_index)
