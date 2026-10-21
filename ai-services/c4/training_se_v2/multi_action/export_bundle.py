"""Export a native MaskablePPO zip. Never relabels a smoke run as full."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from catalogues.c1_practice_full_2026_10 import catalogue_hash

from .contract import N_ACTIONS, OBS_DIM, PROTOCOL, observation_schema
from .train_rl import FULL_SEEDS, dependency_versions

POLICY_FILE = "maskable_ppo_final.zip"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_parity_sidecar(out_dir: Path, meta: dict[str, Any]) -> None:
    """Sidecar for a tiny local MaskablePPO. activation_allowed stays false."""
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = observation_schema()
    _write(out_dir / "observation_schema.json", schema)
    manifest = {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "training_mode": "parity_smoke",
        "activation_allowed": False,
        "masks_in_training": True,
        "masks_in_evaluation": True,
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "catalogue_hash": catalogue_hash(),
        "policy_file": POLICY_FILE,
        "schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
        "seed": meta.get("seed"),
        "requested_timesteps": meta.get("requested_timesteps"),
        "versions": meta.get("versions") or dependency_versions(),
        "note": "Parity checkpoint only. Do not copy to runtime-artifacts and do not set activation_allowed.",
    }
    _write(out_dir / "manifest.json", manifest)


def write_full_export(
    out_dir: Path,
    *,
    seed_dirs: dict[int, Path],
    selection: dict[str, Any],
    final_test: dict[str, Any],
    timesteps: int,
) -> dict[str, Any]:
    seeds = tuple(int(s) for s in selection.get("seeds") or ())
    if seeds != tuple(FULL_SEEDS):
        raise RuntimeError("full export requires seeds 0, 1 and 2")
    if selection.get("test_used_for_selection") is not False:
        raise RuntimeError("selection must not use the held-out test")
    if final_test.get("used_for_selection") is not False:
        raise RuntimeError("final test must be frozen")
    selected = int(selection["selected_seed"])
    if selected not in FULL_SEEDS:
        raise RuntimeError("selected seed is outside the trained set")
    src = seed_dirs[selected] / POLICY_FILE
    if not src.is_file():
        raise FileNotFoundError(src)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / POLICY_FILE
    target.write_bytes(src.read_bytes())
    for seed, folder in seed_dirs.items():
        dest = out_dir / "models" / f"seed_{seed}"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / POLICY_FILE).write_bytes((folder / POLICY_FILE).read_bytes())
    schema = observation_schema()
    schema_bytes = json.dumps(schema, sort_keys=True).encode()
    _write(out_dir / "observation_schema.json", schema)
    _write(out_dir / "selection_val.json", selection)
    _write(out_dir / "final_test.json", final_test)
    config = {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "policy": "MlpPolicy",
        "seeds": list(FULL_SEEDS),
        "timesteps": int(timesteps),
        "masks_in_training": True,
        "masks_in_evaluation": True,
        "learning_rate": 3e-4,
        "n_epochs": 5,
        "gamma": 0.99,
        "catalogue_hash": catalogue_hash(),
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "synthetic": True,
        "reward_note": "Simulator return is not accuracy.",
    }
    versions = dependency_versions()
    _write(out_dir / "train_config.json", config)
    _write(out_dir / "dependency_versions.json", versions)
    manifest = {
        "protocol": PROTOCOL,
        "algorithm": "maskable_ppo",
        "library": "sb3_contrib.MaskablePPO",
        "training_mode": "full",
        "activation_allowed": True,
        "masks_in_training": True,
        "masks_in_evaluation": True,
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "catalogue_hash": catalogue_hash(),
        "policy_file": POLICY_FILE,
        "selected_seed": selected,
        "seeds": list(FULL_SEEDS),
        "schema_sha256": hashlib.sha256(schema_bytes).hexdigest(),
        "selection_split": "validation",
        "test_used_for_selection": False,
        "versions": versions,
        "linear_policy_npz": False,
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
        )
    }
    _write(out_dir / "manifest.json", manifest)
    checksums = dict(manifest["file_sha256"])
    checksums["manifest.json"] = sha256_file(out_dir / "manifest.json")
    _write(out_dir / "checksums.json", checksums)
    return manifest
