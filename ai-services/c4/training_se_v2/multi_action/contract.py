"""se-path-multi-v1 observation and action contract.

Preserves training_se_v2/observation.py (46-topic latent replacement scaffold).
This module is the multi-action replacement. It does not use prior_strength.

Action index = type_index * N_TOPICS + topic_index
Types: practice, revision, quiz, coding
Coding is in the schema so indices stay stable, but the content registry is empty,
so every coding action is masked. A label is not a launch path.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from catalogues.c1_practice_full_2026_10 import (
    N_TOPICS,
    ORDERED_TOPICS,
    catalogue_hash,
    semester_eligibility_mask,
)

PROTOCOL = "se-path-multi-v1"
REWARD_DEFINITION_VERSION = "se-path-multi-v1-reward-1"
ACTION_TYPES = ("practice", "revision", "quiz", "coding")
N_ACTION_TYPES = len(ACTION_TYPES)
N_ACTIONS = N_ACTION_TYPES * N_TOPICS
MASTERY_THRESHOLD = 0.8
MAX_EPISODE_STEPS = 40
# Extras after mastery || available. No latent prior_strength.
EXTRA_NAMES = (
    "mean_mastery",
    "frac_mastered",
    "elapsed_env_step_frac",
    "recent_accuracy",
    "recent_accuracy_observed",
    "engagement_completion_rate",
    "engagement_observed",
    "exam_urgency",
    "exam_date_known",
)
OBS_DIM = 2 * N_TOPICS + len(EXTRA_NAMES)
CATALOGUE_HASH = catalogue_hash()
# No approved coding exercise ids. Empty means the whole coding block is masked.
CODING_CONTENT_IDS: tuple[str, ...] = ()


def observation_schema() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "dim": OBS_DIM,
        "n_topics": N_TOPICS,
        "n_actions": N_ACTIONS,
        "action_types": list(ACTION_TYPES),
        "action_layout": "type_index * n_topics + topic_index",
        "extras": list(EXTRA_NAMES),
        "catalogue_hash": CATALOGUE_HASH,
        "no_prior_strength": True,
        "coding_content_ids": list(CODING_CONTENT_IDS),
        "cold_start": {
            "recent_accuracy": "0.5 default when recent_accuracy_observed=0",
            "engagement_completion_rate": "0 when engagement_observed=0 (not zero mastery)",
            "exam_urgency": "0 when exam_date_known=0",
        },
    }


def decode_action(index: int) -> tuple[str, int]:
    if index < 0 or index >= N_ACTIONS:
        raise ValueError(f"action {index} outside 0..{N_ACTIONS - 1}")
    type_index, topic_index = divmod(int(index), N_TOPICS)
    return ACTION_TYPES[type_index], topic_index


def encode_action(action_type: str, topic_index: int) -> int:
    if action_type not in ACTION_TYPES:
        raise ValueError(action_type)
    if topic_index < 0 or topic_index >= N_TOPICS:
        raise ValueError(topic_index)
    return ACTION_TYPES.index(action_type) * N_TOPICS + int(topic_index)


def build_observation(
    mastery: np.ndarray,
    available: np.ndarray,
    *,
    elapsed_env_steps: int,
    max_episode_steps: int = MAX_EPISODE_STEPS,
    recent_accuracy: float | None = None,
    engagement_completion_rate: float | None = None,
    exam_urgency: float | None = None,
    mastery_threshold: float = MASTERY_THRESHOLD,
) -> np.ndarray:
    mastery = np.asarray(mastery, dtype=np.float32).reshape(N_TOPICS)
    available = np.asarray(available, dtype=np.float32).reshape(N_TOPICS)
    if not np.isfinite(mastery).all() or not np.isfinite(available).all():
        raise ValueError("non-finite mastery or availability")
    mastery = np.clip(np.where(available > 0.5, mastery, 0.0), 0.0, 1.0).astype(np.float32)
    available = np.clip(available, 0.0, 1.0).astype(np.float32)
    avail_bool = available > 0.5
    if avail_bool.any():
        mean_m = float(mastery[avail_bool].mean())
        frac_m = float((mastery[avail_bool] >= mastery_threshold).mean())
    else:
        mean_m = 0.0
        frac_m = 0.0
    step_frac = float(min(1.0, max(0.0, elapsed_env_steps) / max(1, max_episode_steps)))
    recent_observed = 0.0 if recent_accuracy is None else 1.0
    recent_value = 0.5 if recent_accuracy is None else float(np.clip(recent_accuracy, 0.0, 1.0))
    engagement_observed = 0.0 if engagement_completion_rate is None else 1.0
    engagement_value = (
        0.0
        if engagement_completion_rate is None
        else float(np.clip(engagement_completion_rate, 0.0, 1.0))
    )
    urgency_known = 0.0 if exam_urgency is None else 1.0
    urgency_value = 0.0 if exam_urgency is None else float(np.clip(exam_urgency, 0.0, 1.0))
    extras = np.asarray(
        [
            mean_m,
            frac_m,
            step_frac,
            recent_value,
            recent_observed,
            engagement_value,
            engagement_observed,
            urgency_value,
            urgency_known,
        ],
        dtype=np.float32,
    )
    obs = np.concatenate([mastery, available, extras])
    if obs.shape != (OBS_DIM,) or not np.isfinite(obs).all():
        raise RuntimeError("invalid multi-action observation")
    return obs


def action_mask(
    *,
    semester: str,
    available: np.ndarray,
    mastery: np.ndarray,
    mastery_threshold: float = MASTERY_THRESHOLD,
) -> np.ndarray:
    """Practice/revision/quiz require semester eligibility and availability.

    Coding is masked for every topic while CODING_CONTENT_IDS is empty.
    """
    if semester not in ("Y3S1", "Y3S2"):
        return np.zeros(N_ACTIONS, dtype=bool)
    semester_ok = np.asarray(semester_eligibility_mask(semester), dtype=bool)
    available = np.asarray(available, dtype=np.float32).reshape(N_TOPICS)
    mastery = np.asarray(mastery, dtype=np.float32).reshape(N_TOPICS)
    base = (available > 0.5) & semester_ok
    below = mastery < mastery_threshold
    practice = base & below
    if not practice.any() and base.any():
        practice = base.copy()
    revision = base.copy()
    quiz = base.copy()
    coding = np.zeros(N_TOPICS, dtype=bool)
    for topic_id in CODING_CONTENT_IDS:
        if topic_id in ORDERED_TOPICS:
            coding[ORDERED_TOPICS.index(topic_id)] = True
    coding = coding & base
    return np.concatenate([practice, revision, quiz, coding]).astype(bool)
