"""se-path-multi-v2 feature contract.

The observation and mask match se-path-multi-v1. The reward does not.
Old v1 weights must not be loaded under this protocol.
"""

from __future__ import annotations

from typing import Any

from training_se_v2.multi_action.contract import (
    ACTION_TYPES,
    CATALOGUE_HASH,
    EXTRA_NAMES,
    N_ACTIONS,
    N_TOPICS,
    OBS_DIM,
    action_mask,
    build_observation,
    decode_action,
    encode_action,
)

from .objective import PROTOCOL, REWARD_DEFINITION_VERSION

__all__ = [
    "ACTION_TYPES",
    "CATALOGUE_HASH",
    "EXTRA_NAMES",
    "N_ACTIONS",
    "N_TOPICS",
    "OBS_DIM",
    "PROTOCOL",
    "REWARD_DEFINITION_VERSION",
    "action_mask",
    "build_observation",
    "decode_action",
    "encode_action",
    "observation_schema",
]


def observation_schema() -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "reward_definition_version": REWARD_DEFINITION_VERSION,
        "dim": OBS_DIM,
        "n_topics": N_TOPICS,
        "n_actions": N_ACTIONS,
        "action_types": list(ACTION_TYPES),
        "action_layout": "type_index * n_topics + topic_index",
        "extras": list(EXTRA_NAMES),
        "catalogue_hash": CATALOGUE_HASH,
        "same_features_as": "se-path-multi-v1",
        "reward_is_not": "se-path-multi-v1-reward-1",
        "no_prior_strength": True,
        "coding_content_ids": [],
    }
