"""Export a native MaskablePPO zip for se-path-multi-v2.

activation_allowed follows the predeclared validation criterion. Completing
training does not set it. This package does not switch the live student plan.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from catalogues.c1_practice_full_2026_10 import catalogue_hash

from .contract import N_ACTIONS, OBS_DIM, observation_schema
from .objective import (
    ACCEPTANCE_RULE,
    FULL_SEEDS,
    PROTOCOL,
    SELECTION_RULE,
    TRAINING_REVISION,
    TRAINING_SCHEDULE,
    coverage_balanced,
)
from .train_rl import dependency_versions

POLICY_FILE = "maskable_ppo_final.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_training_coverage(folder: Path) -> dict[str, Any]:
    path = folder / "training_coverage.json"
    if not path.is_file():
        raise RuntimeError(f"missing semester coverage record: {folder}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("training_revision") != TRAINING_REVISION:
        raise RuntimeError("training coverage is not the dual-semester revision")
    semesters = data.get("semesters") or {}
    if not coverage_balanced(semesters):
        raise RuntimeError(f"missing or unbalanced semester coverage: {semesters}")
    return data


def write_full_export(
    out_dir: Path,
    *,
    seed_dirs: dict[int, Path],
    selection: dict[str, Any],
    final_test: dict[str, Any],
    timesteps: int,
) -> dict[str, Any]:
    if tuple(int(seed) for seed in selection.get("seeds") or ()) != tuple(FULL_SEEDS):
        raise RuntimeError("full export requires seeds 0, 1 and 2")
    if selection.get("test_used_for_selection") is not False or final_test.get("used_for_selection") is not False:
        raise RuntimeError("held-out evaluation was used for selection")
    selected = int(selection["selected_seed"])
    allowed = bool(selection.get("criterion_met"))
    coverages = {int(seed): load_training_coverage(folder) for seed, folder in seed_dirs.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / POLICY_FILE).write_bytes((seed_dirs[selected] / POLICY_FILE).read_bytes())
    for seed, folder in seed_dirs.items():
        dest = out_dir / "models" / f"seed_{seed}"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / POLICY_FILE).write_bytes((folder / POLICY_FILE).read_bytes())
        (dest / "training_coverage.json").write_text(
            (folder / "training_coverage.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    schema = observation_schema()
    _write(out_dir / "observation_schema.json", schema)
    _write(out_dir / "selection_val.json", selection)
    _write(out_dir / "final_test.json", final_test)
    config = {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "seeds": list(FULL_SEEDS),
        "timesteps": int(timesteps),
        "masks_in_training": True,
        "masks_in_evaluation": True,
        "selection_rule": SELECTION_RULE,
        "acceptance_rule": ACCEPTANCE_RULE,
        "catalogue_hash": catalogue_hash(),
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "synthetic": True,
        "serves_students": False,
        "training_revision": TRAINING_REVISION,
        "training_schedule": TRAINING_SCHEDULE,
    }
    semester_coverage = {
        str(seed): coverages[int(seed)]["semesters"] for seed in FULL_SEEDS
    }
    _write(out_dir / "semester_coverage.json", semester_coverage)
    versions = dependency_versions()
    _write(out_dir / "train_config.json", config)
    _write(out_dir / "dependency_versions.json", versions)
    manifest = {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "training_mode": "full",
        "activation_allowed": allowed,
        "criterion_met": allowed,
        "serves_students": False,
        "masks_in_training": True,
        "masks_in_evaluation": True,
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "catalogue_hash": catalogue_hash(),
        "policy_file": POLICY_FILE,
        "selected_seed": selected,
        "seeds": list(FULL_SEEDS),
        "schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
        "selection_split": "validation",
        "selection_metric": "mean_mastery_change",
        "test_used_for_selection": False,
        "linear_policy_npz": False,
        "acceptance_rule": ACCEPTANCE_RULE,
        "training_revision": TRAINING_REVISION,
        "semester_coverage": semester_coverage,
        "versions": versions,
    }
    manifest["file_sha256"] = {
        name: sha256_file(out_dir / name)
        for name in (
            POLICY_FILE,
            "observation_schema.json",
            "selection_val.json",
            "final_test.json",
            "train_config.json",
            "dependency_versions.json",
            "semester_coverage.json",
        )
    }
    _write(out_dir / "manifest.json", manifest)
    checksums = dict(manifest["file_sha256"])
    checksums["manifest.json"] = sha256_file(out_dir / "manifest.json")
    _write(out_dir / "checksums.json", checksums)
    return manifest
