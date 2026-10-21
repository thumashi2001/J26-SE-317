"""Verify and import one se-path-multi-v2 coverage-r2 Colab backup.

Does not retrain, does not edit activation flags, and does not replace
training source. A checksum or gate mismatch stops before activation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = "se-path-multi-v2-coverage-r2_20261017T040345500695Z"
REVISION = "se-path-multi-v2-coverage-r2"
EXPORT_PREFIX = f"run/{RUN_NAME}/export/"
DEFAULT_ZIP = (
    Path(r"C:\Users\Deshan\Documents\GitHub\Softedge\Suwani_Research\C4_v2_exports")
    / "C4_multi_v2_coverage_r2_complete_20261017T042614Z.zip"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_member(name: str) -> str:
    if not name or name.endswith("/"):
        raise SystemExit(f"unsafe zip member: {name!r}")
    parts = Path(name).parts
    if Path(name).is_absolute() or ".." in parts or "\\" in name:
        raise SystemExit(f"unsafe zip path: {name}")
    return name


def place(dest: Path, data: bytes) -> str:
    digest = sha256_bytes(data)
    if dest.exists():
        current = sha256_bytes(dest.read_bytes())
        if current != digest:
            raise SystemExit(f"refusing to overwrite differing file: {dest}")
        return "unchanged"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return "written"


def verify_zip(zf: zipfile.ZipFile) -> dict:
    names = [safe_member(info.filename) for info in zf.infolist() if not info.is_dir()]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate zip members")
    if "BACKUP_MANIFEST.json" not in names:
        raise SystemExit("BACKUP_MANIFEST.json is missing")
    manifest = json.loads(zf.read("BACKUP_MANIFEST.json"))
    if manifest.get("training_revision") != REVISION:
        raise SystemExit(f"backup revision is {manifest.get('training_revision')}, expected {REVISION}")
    if RUN_NAME not in str(manifest.get("run_dir")):
        raise SystemExit(f"backup run_dir is {manifest.get('run_dir')}")
    listed = manifest.get("files") or []
    listed_paths = {item["path"] for item in listed}
    extra = set(names) - listed_paths - {"BACKUP_MANIFEST.json"}
    missing = listed_paths - set(names)
    if extra or missing:
        raise SystemExit(f"backup membership mismatch extra={sorted(extra)} missing={sorted(missing)}")
    for item in listed:
        path = safe_member(item["path"])
        data = zf.read(path)
        if len(data) != int(item["bytes"]):
            raise SystemExit(f"size mismatch: {path}")
        if sha256_bytes(data) != item["sha256"]:
            raise SystemExit(f"BACKUP_MANIFEST hash mismatch: {path}")
    export_root = EXPORT_PREFIX
    checksums = json.loads(zf.read(export_root + "checksums.json"))
    for name, expected in checksums.items():
        data = zf.read(export_root + name)
        if sha256_bytes(data) != expected:
            raise SystemExit(f"export checksum mismatch: {name}")
    meta = json.loads(zf.read(export_root + "manifest.json"))
    if "manifest.json" not in checksums:
        raise SystemExit("checksums.json does not record manifest.json")
    selection = json.loads(zf.read(export_root + "selection_val.json"))
    config = json.loads(zf.read(export_root + "train_config.json"))
    problems = []
    if meta.get("protocol") != "se-path-multi-v2":
        problems.append("protocol")
    if meta.get("algorithm") != "maskable_ppo" or meta.get("training_mode") != "full":
        problems.append("algorithm")
    if meta.get("selected_seed") != 1 or selection.get("selected_seed") != 1:
        problems.append("selected_seed")
    if meta.get("criterion_met") is not True or selection.get("criterion_met") is not True:
        problems.append("criterion_met")
    if meta.get("activation_allowed") is not True:
        problems.append("activation_allowed")
    if meta.get("serves_students") is not False:
        problems.append("serves_students")
    if meta.get("training_revision") != REVISION or config.get("training_revision") != REVISION:
        problems.append("training_revision")
    if meta.get("test_used_for_selection") is not False or selection.get("test_used_for_selection") is not False:
        problems.append("test_used_for_selection")
    if int(config.get("timesteps") or 0) != 80_000:
        problems.append("timesteps")
    if meta.get("obs_dim") != 101 or meta.get("n_actions") != 184:
        problems.append("schema")
    policy = zf.read(export_root + "maskable_ppo_final.zip")
    seed_policy = zf.read(export_root + "models/seed_1/maskable_ppo_final.zip")
    if sha256_bytes(policy) != sha256_bytes(seed_policy):
        problems.append("selected_checkpoint_is_not_seed_1")
    if sha256_bytes(policy) != checksums["maskable_ppo_final.zip"]:
        problems.append("policy_checksum")
    coverage = meta.get("semester_coverage") or {}
    for seed in ("0", "1", "2"):
        block = coverage.get(seed) or {}
        for semester in ("Y3S1", "Y3S2"):
            steps = int((block.get(semester) or {}).get("steps") or 0)
            episodes = int((block.get(semester) or {}).get("episodes") or 0)
            if steps < 1 or episodes < 1:
                problems.append(f"coverage:{seed}:{semester}")
    chosen = selection["by_seed"]["1"]
    for semester in ("Y3S1", "Y3S2"):
        row = chosen[semester]["maskable_ppo"]
        if float(row["invalid_action_rate"]["mean"]) != 0.0:
            problems.append(f"invalid:{semester}")
    if problems:
        raise SystemExit("export gate mismatch: " + ", ".join(problems))
    return {
        "members": len(names),
        "manifest_files": len(listed),
        "policy_sha256": sha256_bytes(policy),
        "catalogue_hash": meta["catalogue_hash"],
        "y3s1_mastery": chosen["Y3S1"]["maskable_ppo"]["mean_mastery_change"]["mean"],
        "y3s2_mastery": chosen["Y3S2"]["maskable_ppo"]["mean_mastery_change"]["mean"],
        "y3s1_return": chosen["Y3S1"]["maskable_ppo"]["return"]["mean"],
        "y3s2_return": chosen["Y3S2"]["maskable_ppo"]["return"]["mean"],
        "y3s1_no_progress": chosen["Y3S1"]["maskable_ppo"]["no_progress_rate"]["mean"],
        "y3s2_no_progress": chosen["Y3S2"]["maskable_ppo"]["no_progress_rate"]["mean"],
    }


def inference_checks(export_dir: Path, *, active_missing: bool) -> None:
    os.environ.setdefault("PYTHONPATH", str(ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import numpy as np
    from catalogues.c1_practice_full_2026_10 import Y3S1_INDICES, Y3S2_INDICES, catalogue_hash
    from sb3_contrib import MaskablePPO
    from training_se_v2.multi_action_v2.contract import N_ACTIONS, N_TOPICS, OBS_DIM, action_mask
    from training_se_v2.multi_action_v2.serving import (
        MultiV2NotActive,
        MultiValidationError,
        assess_artifact,
        predict,
        predict_with_model,
    )

    info = assess_artifact(export_dir)
    if not info.get("ready"):
        raise SystemExit(f"assess_artifact rejected the export: {info}")
    if catalogue_hash() != json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))["catalogue_hash"]:
        raise SystemExit("live catalogue hash does not match the export")
    model_a = MaskablePPO.load(str(export_dir / "maskable_ppo_final.zip"), device="cpu")
    model_b = MaskablePPO.load(str(export_dir / "maskable_ppo_final.zip"), device="cpu")
    if type(model_a).__name__ != "MaskablePPO":
        raise SystemExit("checkpoint is not MaskablePPO")

    def case(semester: str, foreign: tuple[int, ...]) -> None:
        available = np.zeros(N_TOPICS, dtype=np.float32)
        mastery = np.full(N_TOPICS, 0.4, dtype=np.float32)
        own = Y3S1_INDICES if semester == "Y3S1" else Y3S2_INDICES
        for index in own[:6]:
            available[index] = 1.0
        mask = action_mask(semester=semester, available=available, mastery=mastery)
        if mask[3 * N_TOPICS :].any():
            raise SystemExit("coding actions are unmasked")
        for index in foreign:
            if mask[index] or mask[N_TOPICS + index] or mask[2 * N_TOPICS + index]:
                raise SystemExit(f"{semester} mask includes another semester")
        obs = np.zeros(OBS_DIM, dtype=np.float32)
        obs[:N_TOPICS] = mastery
        obs[N_TOPICS : 2 * N_TOPICS] = available
        left = predict_with_model(model_a, obs, mask)
        right = predict_with_model(model_b, obs, mask)
        if left["action_index"] != right["action_index"]:
            raise SystemExit("reload changed the action")
        if left["action_type"] not in ("practice", "revision", "quiz") or not mask[left["action_index"]]:
            raise SystemExit("prediction left the mask")
        available[own[0]] = 0.0
        blocked = action_mask(semester=semester, available=available, mastery=mastery)
        if blocked[own[0]] or blocked[N_TOPICS + own[0]] or blocked[2 * N_TOPICS + own[0]]:
            raise SystemExit("unavailable topic stayed eligible")

    case("Y3S1", Y3S2_INDICES)
    case("Y3S2", Y3S1_INDICES)
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    mask = np.zeros(N_ACTIONS, dtype=bool)
    try:
        predict_with_model(model_a, obs, mask)
    except MultiValidationError:
        pass
    else:
        raise SystemExit("all-false mask was accepted")
    try:
        predict_with_model(model_a, np.zeros(3, dtype=np.float32), np.ones(N_ACTIONS, dtype=bool))
    except MultiValidationError:
        pass
    else:
        raise SystemExit("malformed observation was accepted")
    try:
        predict_with_model(model_a, obs, np.ones(3, dtype=bool))
    except MultiValidationError:
        pass
    else:
        raise SystemExit("malformed mask was accepted")
    if active_missing:
        try:
            predict(obs.tolist(), np.ones(N_ACTIONS, dtype=bool).tolist(), catalogue_hash())
        except MultiV2NotActive:
            pass
        else:
            raise SystemExit("predict succeeded before the active directory was installed")


def main() -> None:
    zip_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ZIP
    if not zip_path.is_file():
        raise SystemExit(f"backup zip not found: {zip_path}")
    archive_root = ROOT / "local-colab-archive" / "se_path_multi_v2" / RUN_NAME
    runtime_export = ROOT / "runtime-artifacts" / "se_path_multi_v2" / RUN_NAME
    active = ROOT / "runtime-artifacts" / "se_path_multi_v2" / "active"
    evidence = ROOT / "experiments" / "results" / "se_path_multi_v2" / RUN_NAME
    notebook_dest = (
        ROOT
        / "experiments"
        / "notebooks"
        / "v2"
        / "03_se_path_multi_v2_coverage_r2_20261017T040345500695Z.ipynb"
    )
    with zipfile.ZipFile(zip_path) as zf:
        summary = verify_zip(zf)
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = safe_member(info.filename)
            place(archive_root / name, zf.read(name))
            if name.startswith(EXPORT_PREFIX):
                place(runtime_export / name[len(EXPORT_PREFIX) :], zf.read(name))
            if name == "notebooks/03_se_path_multi_v2_executed.ipynb":
                place(notebook_dest, zf.read(name))
        for rel in (
            "manifest.json",
            "train_config.json",
            "semester_coverage.json",
            "checksums.json",
            "dependency_versions.json",
            "selection_val.json",
            "observation_schema.json",
        ):
            place(evidence / rel, zf.read(EXPORT_PREFIX + rel))
    inference_checks(runtime_export, active_missing=not (active / "manifest.json").is_file())
    for path in runtime_export.rglob("*"):
        if path.is_file():
            place(active / path.relative_to(runtime_export), path.read_bytes())
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from catalogues.c1_practice_full_2026_10 import catalogue_hash
    from training_se_v2.multi_action_v2.contract import N_ACTIONS, OBS_DIM
    from training_se_v2.multi_action_v2.serving import predict

    loaded = predict([0.0] * OBS_DIM, [True] + [False] * (N_ACTIONS - 1), catalogue_hash())
    if loaded.get("serves_students") is not False or loaded.get("checkpoint_sha256") != summary["policy_sha256"]:
        raise SystemExit(f"active checkpoint did not match the verified export: {loaded}")
    if loaded.get("action_type") not in ("practice", "revision", "quiz"):
        raise SystemExit("active checkpoint returned an unsupported action")
    report = {
        "zip": str(zip_path),
        "run": RUN_NAME,
        "revision": REVISION,
        "policy_sha256": summary["policy_sha256"],
        "catalogue_hash": summary["catalogue_hash"],
        "selected_seed": 1,
        "validation_mean_mastery_change": {
            "Y3S1": summary["y3s1_mastery"],
            "Y3S2": summary["y3s2_mastery"],
        },
        "validation_return": {"Y3S1": summary["y3s1_return"], "Y3S2": summary["y3s2_return"]},
        "validation_no_progress_rate": {
            "Y3S1": summary["y3s1_no_progress"],
            "Y3S2": summary["y3s2_no_progress"],
        },
        "validation_invalid_action_rate": {"Y3S1": 0.0, "Y3S2": 0.0},
        "synthetic": True,
        "serves_students": False,
        "activated_directory": str(active),
        "final_test_used_for_selection": False,
    }
    place(evidence / "import_report.json", json.dumps(report, indent=2).encode("utf-8"))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
