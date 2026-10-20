"""Freeze integrity for S1 46-topic catalogue."""

from __future__ import annotations

import sys
from pathlib import Path

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from catalogues.c1_practice_full_2026_10 import (
    N_TOPICS,
    ORDERED_TOPICS,
    TOPIC_MODULE,
    TOPIC_SEMESTER,
    Y3S1_TOPICS,
    Y3S2_TOPICS,
    catalogue_hash,
    semester_eligibility_mask,
    validate_catalogue,
)
from training_se import PROTOCOL_VERSION as V0_PROTOCOL
from training_se.catalogue import N_TOPICS as V0_N, ORDERED_TOPICS as V0_TOPICS


def test_catalogue_count_unique_semesters():
    summary = validate_catalogue()
    assert summary["ok"] is True
    assert N_TOPICS == 46
    assert len(set(ORDERED_TOPICS)) == 46
    assert len(Y3S1_TOPICS) == 28
    assert len(Y3S2_TOPICS) == 18
    assert set(TOPIC_SEMESTER[t] for t in ORDERED_TOPICS) == {"Y3S1", "Y3S2"}
    assert all(TOPIC_MODULE[t] for t in ORDERED_TOPICS)


def test_catalogue_hash_stable():
    h1 = catalogue_hash()
    h2 = catalogue_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_semester_masks_partition():
    m1 = semester_eligibility_mask("Y3S1")
    m2 = semester_eligibility_mask("Y3S2")
    assert sum(m1) == 28
    assert sum(m2) == 18
    assert all(a ^ b for a, b in zip(m1, m2))


def test_no_v0_id_overlap():
    assert V0_N == 12
    assert set(V0_TOPICS).isdisjoint(set(ORDERED_TOPICS))
    assert V0_PROTOCOL == "se-path-sim-v0"


def test_v1_protocol_isolated():
    from training_se_v1 import PROTOCOL_VERSION as V1

    assert V1 == "se-path-sim-v1"
    assert V1 != V0_PROTOCOL
