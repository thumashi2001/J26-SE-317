"""Reuse the frozen 12-topic C1 practice catalogue from training_se."""

from __future__ import annotations

from training_se.catalogue import (
    N_TOPICS,
    ORDERED_TOPICS,
    SOURCE,
    TOPIC_MODULE,
    catalogue_hash,
    catalogue_payload,
    topic_index,
)

__all__ = [
    "N_TOPICS",
    "ORDERED_TOPICS",
    "SOURCE",
    "TOPIC_MODULE",
    "catalogue_hash",
    "catalogue_payload",
    "topic_index",
]
