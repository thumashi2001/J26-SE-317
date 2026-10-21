"""se-path-multi-v2 loader.

Refuses se-path-multi-v1 weights, smoke runs, and exports that missed the
validation learning criterion. serves_students stays false: a ready artifact
is a synthetic-validation checkpoint, not a real-student effectiveness claim.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from catalogues.c1_practice_full_2026_10 import ORDERED_TOPICS, catalogue_hash
from training_se_v2.multi_action_v2.contract import (
    N_ACTIONS,
    OBS_DIM,
    PROTOCOL,
    decode_action,
)
from training_se_v2.multi_action_v2.objective import (
    ACCEPTANCE_RULE,
    TRAINING_REVISION,
    coverage_balanced,
)

POLICY_FILE = "maskable_ppo_final.zip"
REQUIRED = (
    "manifest.json",
    POLICY_FILE,
    "observation_schema.json",
    "selection_val.json",
    "final_test.json",
    "train_config.json",
    "dependency_versions.json",
    "checksums.json",
    "semester_coverage.json",
)


class MultiV2NotActive(RuntimeError):
    pass


class MultiValidationError(ValueError):
    pass


def active_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime-artifacts" / "se_path_multi_v2" / "active"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assess_artifact(folder: Path) -> dict[str, Any]:
    folder = Path(folder)
    missing = [name for name in REQUIRED if not (folder / name).is_file()]
    if missing:
        return {"ready": False, "protocol": PROTOCOL, "reason": "incomplete_artifact", "missing": missing}
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    reasons: list[str] = []
    if manifest.get("protocol") != PROTOCOL:
        reasons.append("protocol_mismatch")
    if manifest.get("algorithm") != "maskable_ppo":
        reasons.append("algorithm_is_not_maskable_ppo")
    if manifest.get("training_mode") != "full":
        reasons.append("training_mode_is_not_full")
    if manifest.get("criterion_met") is not True or manifest.get("activation_allowed") is not True:
        reasons.append("validation_criterion_not_met")
    if manifest.get("serves_students") is not False:
        reasons.append("student_serving_must_stay_explicitly_off")
    if manifest.get("masks_in_training") is not True or manifest.get("masks_in_evaluation") is not True:
        reasons.append("masks_not_declared")
    if manifest.get("obs_dim") != OBS_DIM or manifest.get("n_actions") != N_ACTIONS:
        reasons.append("schema_mismatch")
    if manifest.get("catalogue_hash") != catalogue_hash():
        reasons.append("catalogue_mismatch")
    if manifest.get("selection_metric") != "mean_mastery_change":
        reasons.append("selection_metric_is_not_learning_progress")
    if list(manifest.get("seeds") or []) != [0, 1, 2] or manifest.get("test_used_for_selection") is not False:
        reasons.append("provenance_invalid")
    checksums = json.loads((folder / "checksums.json").read_text(encoding="utf-8"))
    for name, expected in checksums.items():
        file_path = folder / name
        if not file_path.is_file() or _sha256(file_path) != expected:
            reasons.append(f"checksum_mismatch:{name}")
            break
    selection = json.loads((folder / "selection_val.json").read_text(encoding="utf-8"))
    if selection.get("criterion_met") is not True or selection.get("test_used_for_selection") is not False:
        reasons.append("selection_record_rejected")
    if selection.get("selected_seed") != manifest.get("selected_seed"):
        reasons.append("selected_seed_mismatch")
    config = json.loads((folder / "train_config.json").read_text(encoding="utf-8"))
    if int(config.get("timesteps") or 0) < 10_000:
        reasons.append("timesteps_below_full_run")
    if manifest.get("training_revision") != TRAINING_REVISION or config.get("training_revision") != TRAINING_REVISION:
        reasons.append("training_revision_mismatch")
    recorded = manifest.get("semester_coverage") or {}
    for seed in ("0", "1", "2"):
        if not coverage_balanced(recorded.get(seed) or {}):
            reasons.append("missing_semester_coverage")
            break
    if reasons:
        return {"ready": False, "protocol": PROTOCOL, "reason": reasons[0], "reasons": reasons}
    return {
        "ready": True,
        "protocol": PROTOCOL,
        "serves_students": False,
        "acceptance_rule": ACCEPTANCE_RULE,
        "selected_seed": manifest.get("selected_seed"),
    }


def readiness() -> dict[str, Any]:
    info = assess_artifact(active_dir())
    # The Colab manifest field stays false. It is export metadata, not a statement
    # that no student plan is allowed to request the checkpoint.
    info["serves_students"] = False
    info["artifact_serves_students"] = False
    info["artifact_serves_students_meaning"] = (
        "Unchanged Colab export field. It does not say whether the student plan requested this checkpoint."
    )
    info["student_plan_integration"] = "requestable" if info.get("ready") else "unavailable"
    if info.get("ready"):
        info["detail"] = (
            "Synthetic validation floor passed. The student plan may request the next eligible "
            "practice, revision, or quiz from this checkpoint. serves_students remains the export "
            "metadata flag and stays false. Calendar packing stays heuristic. "
            "This is not a real-student learning result."
        )
    else:
        info["detail"] = "No verified se-path-multi-v2 checkpoint is active. The student plan uses its explicit fallback."
        info["student_plan_integration"] = "unavailable"
    return info


def _obs(observation: Any) -> np.ndarray:
    obs = np.asarray(observation, dtype=np.float32)
    if obs.shape != (OBS_DIM,) or not np.isfinite(obs).all():
        raise MultiValidationError("malformed observation")
    return obs


def _mask(action_mask: Any) -> np.ndarray:
    mask = np.asarray(action_mask, dtype=bool)
    if mask.shape != (N_ACTIONS,):
        raise MultiValidationError("malformed action mask")
    return mask


def predict_with_model(model: Any, observation: Any, action_mask: Any) -> dict[str, Any]:
    if type(model).__name__ != "MaskablePPO":
        raise MultiV2NotActive("loaded object is not MaskablePPO")
    obs = _obs(observation)
    mask = _mask(action_mask)
    if not mask.any():
        raise MultiValidationError("no eligible actions")
    action, _state = model.predict(obs, action_masks=mask, deterministic=True)
    action_index = int(action)
    if not bool(mask[action_index]):
        raise MultiValidationError("selected masked action")
    kind, topic_index = decode_action(action_index)
    if kind == "coding":
        raise MultiValidationError("coding action is unavailable")
    return {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "action_index": action_index,
        "action_type": kind,
        "topic_id": ORDERED_TOPICS[topic_index],
        "weights_updated": False,
        "serves_students": False,
        "synthetic": True,
    }


_CACHED: dict[str, Any] = {"hash": None, "model": None}


def predict(observation: list[float], action_mask: list[bool], catalogue_hash_client: str | None) -> dict[str, Any]:
    info = readiness()
    if not info["ready"]:
        raise MultiV2NotActive(info.get("reason") or "not_ready")
    if catalogue_hash_client and catalogue_hash_client != catalogue_hash():
        raise MultiValidationError("catalogue_hash mismatch")
    path = active_dir() / POLICY_FILE
    digest = _sha256(path)
    if _CACHED["hash"] != digest:
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(path), device="cpu")
        _CACHED["hash"] = digest
        _CACHED["model"] = model
    manifest = json.loads((active_dir() / "manifest.json").read_text(encoding="utf-8"))
    result = predict_with_model(_CACHED["model"], observation, action_mask)
    result["checkpoint_sha256"] = digest
    result["catalogue_hash"] = catalogue_hash()
    result["training_revision"] = manifest.get("training_revision")
    result["selected_seed"] = manifest.get("selected_seed")
    return result
