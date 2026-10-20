"""Train a tiny MaskablePPO, reload it through the production predict path, and reject smoke activation.

Does not copy anything into runtime-artifacts/se_path_multi_v1/active.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from catalogues.c1_practice_full_2026_10 import N_TOPICS, ORDERED_TOPICS, Y3S1_TOPICS, Y3S2_TOPICS

from services.inference.se_path_multi_v1_loader import (
    MultiValidationError,
    action_probabilities,
    assess_artifact,
    predict_with_model,
)
from .contract import N_ACTIONS, action_mask, build_observation, decode_action
from .export_bundle import write_parity_sidecar
from .evaluate import load_model
from .train_rl import PARITY_TIMESTEPS, train_maskable_ppo


def _case(semester: str, topics: list[str], mastery_value: float, *, high: set[str] | None = None) -> tuple[np.ndarray, np.ndarray]:
    mastery = np.full(N_TOPICS, 0.0, dtype=np.float32)
    available = np.zeros(N_TOPICS, dtype=np.float32)
    high = high or set()
    for topic in topics:
        idx = ORDERED_TOPICS.index(topic)
        available[idx] = 1.0
        mastery[idx] = 0.95 if topic in high else mastery_value
    obs = build_observation(
        mastery,
        available,
        elapsed_env_steps=3,
        recent_accuracy=0.4,
        engagement_completion_rate=0.5,
        exam_urgency=0.25 if semester == "Y3S1" else None,
    )
    mask = action_mask(semester=semester, available=available, mastery=mastery)
    return obs, mask


def _probs(model, obs: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return action_probabilities(model, obs, mask)


def main() -> None:
    out = Path(__file__).resolve().parents[2] / "experiments" / "parity_runs" / "se_path_multi_v1"
    if out.exists():
        shutil.rmtree(out)
    trained = train_maskable_ppo(out, timesteps=PARITY_TIMESTEPS, seed=0, semester="Y3S1")
    write_parity_sidecar(out, trained["meta"])
    assert trained["meta"]["masks_in_training"] is True
    assert trained["meta"]["activation_allowed"] is False
    live = trained["model"]
    reloaded = load_model(out / "maskable_ppo_final.zip")

    cases = [
        _case("Y3S1", list(Y3S1_TOPICS[:8]), 0.3),
        _case("Y3S2", list(Y3S2_TOPICS), 0.35),
        _case("Y3S1", list(Y3S1_TOPICS[:6]), 0.2, high=set(Y3S1_TOPICS[:2])),
        _case("Y3S2", list(Y3S2_TOPICS[:5]), 0.15),
    ]
    for obs, mask in cases:
        assert mask.any()
        assert not mask[3 * N_TOPICS :].any()
        a_live = predict_with_model(live, obs, mask)
        a_load = predict_with_model(reloaded, obs, mask)
        if a_live["action_index"] != a_load["action_index"]:
            raise SystemExit(f"action mismatch {a_live['action_index']} vs {a_load['action_index']}")
        kind, _topic = decode_action(a_load["action_index"])
        if kind == "coding" or not mask[a_load["action_index"]]:
            raise SystemExit("selected an invalid or coding action")
        p_live = _probs(live, obs, mask)
        p_load = _probs(reloaded, obs, mask)
        if not np.allclose(p_live, p_load, atol=1e-5):
            raise SystemExit("masked action probabilities diverged after reload")
        if float(p_load[~mask].sum()) > 1e-5:
            raise SystemExit("probability mass on masked actions")
        if int(np.argmax(p_load)) != a_load["action_index"]:
            raise SystemExit("deterministic action is not the masked mode")

    empty_obs = build_observation(
        np.zeros(N_TOPICS, dtype=np.float32),
        np.zeros(N_TOPICS, dtype=np.float32),
        elapsed_env_steps=0,
    )
    empty_mask = np.zeros(N_ACTIONS, dtype=bool)
    try:
        predict_with_model(reloaded, empty_obs, empty_mask)
    except MultiValidationError as exc:
        if "no eligible" not in str(exc):
            raise
    else:
        raise SystemExit("all-invalid mask was not rejected")

    refused = assess_artifact(out)
    if refused["ready"]:
        raise SystemExit("parity artifact must not be ready for activation")

    forged = out / "forged"
    if forged.exists():
        shutil.rmtree(forged)
    shutil.copytree(out, forged)
    manifest = json.loads((forged / "manifest.json").read_text(encoding="utf-8"))
    manifest["activation_allowed"] = True
    manifest["training_mode"] = "full"
    (forged / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    forged_ready = assess_artifact(forged)
    if forged_ready["ready"]:
        raise SystemExit("flipping activation_allowed on a parity run was accepted")

    linear = out / "linear_only"
    linear.mkdir()
    np.savez(linear / "policy.npz", weights=np.zeros((N_ACTIONS, empty_obs.shape[0]), dtype=np.float32))
    if assess_artifact(linear)["ready"]:
        raise SystemExit("linear policy.npz was accepted")

    relabel = out / "relabel_complete"
    if relabel.exists():
        shutil.rmtree(relabel)
    relabel.mkdir()
    shutil.copy(out / "maskable_ppo_final.zip", relabel / "maskable_ppo_final.zip")
    from .contract import observation_schema
    from .export_bundle import sha256_file

    schema = observation_schema()
    (relabel / "observation_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    selection = {
        "test_used_for_selection": False,
        "seeds": [0],
        "selected_seed": 0,
        "split": "validation",
    }
    (relabel / "selection_val.json").write_text(json.dumps(selection), encoding="utf-8")
    (relabel / "final_test.json").write_text(
        json.dumps({"used_for_selection": False, "seed": 0, "split": "final_test"}),
        encoding="utf-8",
    )
    config = {"algorithm": "maskable_ppo", "masks_in_training": True, "timesteps": PARITY_TIMESTEPS}
    (relabel / "train_config.json").write_text(json.dumps(config), encoding="utf-8")
    (relabel / "dependency_versions.json").write_text(json.dumps({"note": "parity"}), encoding="utf-8")
    manifest = {
        "protocol": "se-path-multi-v1",
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "training_mode": "full",
        "activation_allowed": True,
        "masks_in_training": True,
        "masks_in_evaluation": True,
        "obs_dim": int(empty_obs.shape[0]),
        "n_actions": N_ACTIONS,
        "catalogue_hash": json.loads((out / "manifest.json").read_text(encoding="utf-8")).get("catalogue_hash"),
        "policy_file": "maskable_ppo_final.zip",
        "selected_seed": 0,
        "seeds": [0, 1, 2],
        "schema_sha256": "not-the-schema",
        "selection_split": "validation",
        "test_used_for_selection": False,
        "linear_policy_npz": False,
        "file_sha256": {},
    }
    (relabel / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    names = [
        "maskable_ppo_final.zip",
        "observation_schema.json",
        "selection_val.json",
        "final_test.json",
        "train_config.json",
        "dependency_versions.json",
        "manifest.json",
    ]
    checksums = {name: sha256_file(relabel / name) for name in names}
    manifest["file_sha256"] = {name: checksums[name] for name in names if name != "manifest.json"}
    (relabel / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    checksums["manifest.json"] = sha256_file(relabel / "manifest.json")
    (relabel / "checksums.json").write_text(json.dumps(checksums), encoding="utf-8")
    relabel_ready = assess_artifact(relabel)
    if relabel_ready["ready"]:
        raise SystemExit("a checksum-valid smoke relabel was accepted")
    if "timesteps_below_full_run" not in relabel_ready.get("reasons", []):
        raise SystemExit(f"relabel was not rejected for smoke budget: {relabel_ready}")

    print(
        "OK parity",
        "actions",
        len(cases),
        "probs_match",
        "coding_masked",
        "all_invalid_rejected",
        "smoke_activation_rejected",
        "linear_npz_rejected",
    )


if __name__ == "__main__":
    main()
