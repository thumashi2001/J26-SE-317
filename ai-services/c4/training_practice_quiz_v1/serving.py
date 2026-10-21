"""Inactive export and readiness check for c4-practice-quiz-pass-v1.

Smoke reports are not student-serving artifacts. A bundle is requestable only
when activation_allowed, serves_students, and reviewed_full_export are all true
and the report checksum matches. This package never sets those flags.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from training_practice_quiz_v1.protocol import (
    BLUEPRINT_STRATEGY,
    FEATURE_CUTOFF,
    FEATURE_NAMES,
    PRODUCT_SCORE_TARGET,
    PROTOCOL,
)


def export_inactive_bundle(report: dict[str, Any], dest: Path) -> dict[str, Any]:
    payload = {
        "protocol": PROTOCOL,
        "blueprint_strategy": BLUEPRINT_STRATEGY,
        "feature_cutoff": FEATURE_CUTOFF,
        "feature_names": list(FEATURE_NAMES),
        "product_score_target": PRODUCT_SCORE_TARGET,
        "product_score_target_note": "Product rule, not an institutional pass mark.",
        "activation_allowed": False,
        "serves_students": False,
        "reviewed_full_export": False,
        "report": report,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "bundle.json").write_bytes(raw)
    (dest / "checksums.json").write_text(
        json.dumps({"bundle.json": digest}, indent=2),
        encoding="utf-8",
    )
    return {"directory": str(dest), "sha256": digest, "activation_allowed": False}


def assess_bundle(directory: Path) -> dict[str, Any]:
    bundle_path = directory / "bundle.json"
    checksum_path = directory / "checksums.json"
    if not bundle_path.is_file() or not checksum_path.is_file():
        return {"ready": False, "usable": False, "code": "missing_bundle"}
    raw = bundle_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    recorded = json.loads(checksum_path.read_text(encoding="utf-8")).get("bundle.json")
    if recorded != digest:
        return {"ready": False, "usable": False, "code": "checksum_mismatch"}
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("protocol") != PROTOCOL or list(payload.get("feature_names") or []) != list(FEATURE_NAMES):
        return {"ready": False, "usable": False, "code": "schema_mismatch"}
    if not (
        payload.get("activation_allowed") is True
        and payload.get("serves_students") is True
        and payload.get("reviewed_full_export") is True
    ):
        return {
            "ready": False,
            "usable": False,
            "code": "not_activated",
            "reason": "Insufficient evidence for this-quiz pass probability. The heuristic remains in use.",
        }
    return {"ready": True, "usable": True, "code": "reviewed_full_export"}
