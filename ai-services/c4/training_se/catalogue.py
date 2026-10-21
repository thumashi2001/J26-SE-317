"""Ordered SE practice topic catalogue for se-path-sim-v0.

Source of truth for IDs: ``backend/src/modules/c1/data/practiceQuestions.js``
keys of ``PRACTICE_QUESTIONS`` (insertion order). Copied here so Colab/training
does not import the Node tree. Do not rename to ASSISTments skill IDs.

This is an **initial practice-only** catalogue (12 topics), not complete lecture
coverage. Module codes are recorded for content matching across academic years
(semester ZIP labels may move; match by module code + content).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# (topic_id, module_code) — module codes from C1 practiceQuestions comments / seed_c1.py
ORDERED_TOPICS: tuple[str, ...] = (
    "usability_heuristics",
    "user_research_methods",
    "prototyping",
    "normalization",
    "indexing",
    "query_optimization",
    "case_analysis_techniques",
    "industry_case_studies",
    "lessons_learned",
    "risk_management",
    "estimation",
    "agile_planning",
)

TOPIC_MODULE: dict[str, str] = {
    "usability_heuristics": "SE3050",
    "user_research_methods": "SE3050",
    "prototyping": "SE3050",
    "normalization": "SE3060",
    "indexing": "SE3060",
    "query_optimization": "SE3060",
    "case_analysis_techniques": "SE3070",
    "industry_case_studies": "SE3070",
    "lessons_learned": "SE3070",
    "risk_management": "SE3080",
    "estimation": "SE3080",
    "agile_planning": "SE3080",
}

SOURCE = (
    "backend/src/modules/c1/data/practiceQuestions.js :: PRACTICE_QUESTIONS keys "
    "(frozen copy for se-path-sim-v0)"
)

N_TOPICS = len(ORDERED_TOPICS)
assert N_TOPICS == 12
assert len(TOPIC_MODULE) == N_TOPICS
assert tuple(TOPIC_MODULE) == ORDERED_TOPICS


def catalogue_payload() -> dict[str, Any]:
    return {
        "protocol": "se-path-sim-v0",
        "domain": "se_simulation",
        "catalogue_kind": "c1_practice_only_initial",
        "source": SOURCE,
        "n_topics": N_TOPICS,
        "topics": list(ORDERED_TOPICS),
        "topic_modules": dict(TOPIC_MODULE),
        "note": (
            "Semester ZIP folder labels may differ by academic year; "
            "match lecture materials by module_code and content, not semester alone."
        ),
    }


def catalogue_hash() -> str:
    canonical = json.dumps(
        {"topics": list(ORDERED_TOPICS), "topic_modules": TOPIC_MODULE},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def topic_index(topic: str) -> int:
    return ORDERED_TOPICS.index(topic)
