"""Inventory authorized SE exports if present; otherwise document synthetic-only path."""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Relative to ai-services/c4 — places where a de-identified SE export might appear.
CANDIDATE_GLOBS = (
    "datasets/raw/**/*se*attempt*",
    "datasets/raw/**/*attempt*export*",
    "datasets/raw/**/*mock*exam*",
    "datasets/raw/**/*se*exam*",
    "datasets/processed/**/*se*attempt*",
    "datasets/authorized_se/**/*",
)


def inventory_local_se_exports(c4_root: Path | str) -> dict[str, Any]:
    root = Path(c4_root).resolve()
    found: list[str] = []
    for pattern in CANDIDATE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file():
                found.append(str(path.relative_to(root).as_posix()))
    return {
        "c4_root": str(root),
        "searched_globs": list(CANDIDATE_GLOBS),
        "found_files": found,
        "real_se_exports_available": bool(found),
        "decision": (
            "Use authorized local exports for supervised fitting."
            if found
            else (
                "No authorized SE attempt/exam exports found under ai-services/c4. "
                "Use explicitly synthetic se-supervised-sim-v0 data. "
                "Do not download unrelated datasets or relabel ASSISTments records."
            )
        ),
    }
