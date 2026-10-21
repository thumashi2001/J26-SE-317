"""Re-export frozen S1 catalogue for se-path-sim-v1 (additive; v0 untouched)."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `import catalogues...` when C4 root is on sys.path (Colab / tests).
_C4_ROOT = Path(__file__).resolve().parents[1]
if str(_C4_ROOT) not in sys.path:
    sys.path.insert(0, str(_C4_ROOT))

from catalogues.c1_practice_full_2026_10 import (  # noqa: E402
    CATALOGUE_ID,
    N_TOPICS,
    ORDERED_TOPICS,
    SCOPE_DECISION,
    SOURCE_COMMIT,
    SOURCE_FILE_HASHES,
    TOPIC_LABEL,
    TOPIC_MODULE,
    TOPIC_SEMESTER,
    Y3S1_INDICES,
    Y3S1_TOPICS,
    Y3S2_INDICES,
    Y3S2_TOPICS,
    catalogue_hash,
    catalogue_payload,
    semester_eligibility_mask,
    topic_index,
    validate_catalogue,
)

SOURCE = (
    "Frozen snapshot c1-practice-full-2026.10 from C1 PRACTICE_QUESTIONS / content "
    f"(commit {SOURCE_COMMIT}); S1 semester-mask scope."
)

__all__ = [
    "CATALOGUE_ID",
    "N_TOPICS",
    "ORDERED_TOPICS",
    "SCOPE_DECISION",
    "SOURCE",
    "SOURCE_COMMIT",
    "SOURCE_FILE_HASHES",
    "TOPIC_LABEL",
    "TOPIC_MODULE",
    "TOPIC_SEMESTER",
    "Y3S1_INDICES",
    "Y3S1_TOPICS",
    "Y3S2_INDICES",
    "Y3S2_TOPICS",
    "catalogue_hash",
    "catalogue_payload",
    "semester_eligibility_mask",
    "topic_index",
    "validate_catalogue",
]
