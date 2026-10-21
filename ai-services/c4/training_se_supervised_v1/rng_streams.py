"""Separate deterministic RNG streams for learner / practice / exam / split."""

from __future__ import annotations

import numpy as np

from .contract import (
    STREAM_EXAM,
    STREAM_LEARNER,
    STREAM_PRACTICE,
    STREAM_QUESTIONS,
    STREAM_SPLIT,
)


def make_rng(master_seed: int, stream_offset: int) -> np.random.Generator:
    # Mix master seed with stream offset into a single uint64 seed space.
    seed = (int(master_seed) + int(stream_offset)) % (2**32 - 1)
    if seed == 0:
        seed = 1
    return np.random.default_rng(seed)


def learner_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_LEARNER)


def questions_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_QUESTIONS)


def practice_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_PRACTICE)


def exam_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_EXAM)


def split_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_SPLIT)
