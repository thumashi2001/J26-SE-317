"""se-path-multi-v1 loader.

Serves a native sb3_contrib.MaskablePPO zip. A linear policy.npz is not a policy.
activation_allowed=true is required and is not sufficient.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from catalogues.c1_practice_full_2026_10 import ORDERED_TOPICS, catalogue_hash
from training_se_v2.multi_action.contract import (
    N_ACTIONS,
    OBS_DIM,
    PROTOCOL,
    decode_action,
)

POLICY_FILE = "maskable_ppo_final.zip"
REQUIRED_FILES = (
    "manifest.json",
    POLICY_FILE,
    "observation_schema.json",
    "selection_val.json",
    "final_test.json",
    "train_config.json",
    "dependency_versions.json",
    "checksums.json",
)


class MultiNotActive(RuntimeError):
    pass


class MultiValidationError(ValueError):
    pass


def active_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime-artifacts" / "se_path_multi_v1" / "active"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assess_artifact(folder: Path) -> dict[str, Any]:
    folder = Path(folder)
    if (folder / "policy.npz").is_file() and not (folder / POLICY_FILE).is_file():
        return {
            "ready": False,
            "protocol": PROTOCOL,
            "reason": "linear_policy_npz_is_not_maskable_ppo",
        }
    missing = [name for name in REQUIRED_FILES if not (folder / name).is_file()]
    if missing:
        return {
            "ready": False,
            "protocol": PROTOCOL,
            "reason": "incomplete_artifact",
            "missing": missing,
        }
    manifest = _load_json(folder / "manifest.json")
    reasons: list[str] = []
    if manifest.get("protocol") != PROTOCOL:
        reasons.append("protocol_mismatch")
    if manifest.get("algorithm") != "maskable_ppo" or manifest.get("library") != "sb3_contrib.MaskablePPO":
        reasons.append("algorithm_is_not_maskable_ppo")
    if manifest.get("training_mode") != "full":
        reasons.append("training_mode_is_not_full")
    if manifest.get("activation_allowed") is not True:
        reasons.append("activation_flag_false")
    if manifest.get("masks_in_training") is not True or manifest.get("masks_in_evaluation") is not True:
        reasons.append("masks_not_declared")
    if manifest.get("obs_dim") != OBS_DIM or manifest.get("n_actions") != N_ACTIONS:
        reasons.append("schema_mismatch")
    if manifest.get("catalogue_hash") != catalogue_hash():
        reasons.append("catalogue_mismatch")
    if manifest.get("policy_file") != POLICY_FILE or manifest.get("linear_policy_npz") is not False:
        reasons.append("policy_file_is_not_native_zip")
    if list(manifest.get("seeds") or []) != [0, 1, 2]:
        reasons.append("seeds_are_not_0_1_2")
    if manifest.get("test_used_for_selection") is not False or manifest.get("selection_split") != "validation":
        reasons.append("selection_provenance_invalid")
    selected = manifest.get("selected_seed")
    if selected not in (0, 1, 2):
        reasons.append("selected_seed_invalid")

    checksums = _load_json(folder / "checksums.json")
    for name, expected in checksums.items():
        file_path = folder / name
        if not file_path.is_file() or _sha256(file_path) != expected:
            reasons.append(f"checksum_mismatch:{name}")
            break
    file_sha = manifest.get("file_sha256") or {}
    if file_sha.get(POLICY_FILE) != checksums.get(POLICY_FILE):
        reasons.append("manifest_policy_hash_mismatch")

    selection = _load_json(folder / "selection_val.json")
    final_test = _load_json(folder / "final_test.json")
    config = _load_json(folder / "train_config.json")
    schema = _load_json(folder / "observation_schema.json")
    if selection.get("test_used_for_selection") is not False:
        reasons.append("selection_used_test")
    if selection.get("selected_seed") != selected or list(selection.get("seeds") or []) != [0, 1, 2]:
        reasons.append("selection_seed_mismatch")
    if final_test.get("used_for_selection") is not False or final_test.get("seed") != selected:
        reasons.append("final_test_was_not_frozen")
    if config.get("algorithm") != "maskable_ppo" or config.get("masks_in_training") is not True:
        reasons.append("train_config_mismatch")
    if int(config.get("timesteps") or 0) < 10_000:
        reasons.append("timesteps_below_full_run")
    if schema.get("protocol") != PROTOCOL or int(schema.get("dim") or -1) != OBS_DIM:
        reasons.append("observation_schema_mismatch")
    if int(schema.get("n_actions") or -1) != N_ACTIONS:
        reasons.append("action_schema_mismatch")
    schema_hash = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
    if manifest.get("schema_sha256") != schema_hash:
        reasons.append("schema_hash_mismatch")

    if reasons:
        return {"ready": False, "protocol": PROTOCOL, "reason": reasons[0], "reasons": reasons}
    return {
        "ready": True,
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "selected_seed": selected,
        "policy_file": POLICY_FILE,
        "catalogue_hash": catalogue_hash(),
    }


def readiness() -> dict[str, Any]:
    info = assess_artifact(active_dir())
    if not info["ready"] and info.get("reason") == "incomplete_artifact":
        info["detail"] = "Full MaskablePPO export is not imported. Do not copy a parity or linear smoke run here."
    return info


def _as_obs(observation: Any) -> np.ndarray:
    obs = np.asarray(observation, dtype=np.float32)
    if obs.shape != (OBS_DIM,) or not np.isfinite(obs).all():
        raise MultiValidationError("malformed observation")
    return obs


def _as_mask(action_mask: Any) -> np.ndarray:
    mask = np.asarray(action_mask, dtype=bool)
    if mask.shape != (N_ACTIONS,):
        raise MultiValidationError("malformed action mask")
    return mask


def action_probabilities(model: Any, observation: np.ndarray, action_mask: np.ndarray) -> np.ndarray:
    import torch

    obs = _as_obs(observation)
    mask = _as_mask(action_mask)
    if not mask.any():
        raise MultiValidationError("no eligible actions")
    obs_t = torch.as_tensor(obs).float().unsqueeze(0)
    with torch.no_grad():
        dist = model.policy.get_distribution(obs_t, action_masks=mask)
        probs = dist.distribution.probs.squeeze(0).detach().cpu().numpy()
    if not np.isfinite(probs).all() or abs(float(probs.sum()) - 1.0) > 1e-4:
        raise MultiValidationError("masked action distribution is not a probability vector")
    return np.asarray(probs, dtype=np.float64)


def predict_with_model(model: Any, observation: Any, action_mask: Any) -> dict[str, Any]:
    if type(model).__name__ != "MaskablePPO":
        raise MultiNotActive("loaded object is not MaskablePPO")
    obs = _as_obs(observation)
    mask = _as_mask(action_mask)
    if not mask.any():
        raise MultiValidationError("no eligible actions")
    action, _state = model.predict(obs, action_masks=mask, deterministic=True)
    action_index = int(action)
    if action_index < 0 or action_index >= N_ACTIONS or not bool(mask[action_index]):
        raise MultiValidationError("selected masked action")
    kind, topic_index = decode_action(action_index)
    if kind == "coding":
        raise MultiValidationError("coding action is unavailable")
    probs = action_probabilities(model, obs, mask)
    return {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "action_index": action_index,
        "action_type": kind,
        "topic_id": ORDERED_TOPICS[topic_index],
        "uncalibrated_action_probability": float(probs[action_index]),
        "experimental": True,
        "simulation_trained": True,
        "weights_updated": False,
        "probability_note": "Masked policy probability. Not a calibrated confidence and not accuracy.",
    }


_CACHED: dict[str, Any] = {"hash": None, "model": None}


def _model():
    info = readiness()
    if not info["ready"]:
        raise MultiNotActive(info.get("reason") or "not_ready")
    path = active_dir() / POLICY_FILE
    digest = _sha256(path)
    if _CACHED["hash"] != digest:
        from sb3_contrib import MaskablePPO

        model = MaskablePPO.load(str(path), device="cpu")
        obs_space = getattr(model, "observation_space", None)
        act_space = getattr(model, "action_space", None)
        if obs_space is None or tuple(getattr(obs_space, "shape", ())) != (OBS_DIM,):
            raise MultiNotActive("checkpoint observation space does not match schema")
        if act_space is None or int(getattr(act_space, "n", -1)) != N_ACTIONS:
            raise MultiNotActive("checkpoint action space does not match schema")
        _CACHED["hash"] = digest
        _CACHED["model"] = model
    return _CACHED["model"]


def predict(observation: list[float], action_mask: list[bool], catalogue_hash_client: str | None) -> dict[str, Any]:
    if catalogue_hash_client and catalogue_hash_client != catalogue_hash():
        raise MultiValidationError("catalogue_hash mismatch")
    return predict_with_model(_model(), observation, action_mask)
