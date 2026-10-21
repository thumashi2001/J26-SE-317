"""Checksums and provenance records for real vs synthetic data."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path | str, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path | str, payload: dict[str, Any]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=str)
    return p


def read_json(path: Path | str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_real_data_provenance(
    *,
    source_path: Path | str,
    official_page: str,
    drive_view_url: str,
    notes: str,
) -> dict[str, Any]:
    path = Path(source_path)
    return {
        "data_kind": "real_assistments_observations",
        "not_synthetic": True,
        "domain": "K-12 mathematics tutoring (ASSISTments Skill Builder 2009-2010)",
        "not_sliit_se_observations": True,
        "official_page": official_page,
        "corrected_drive_view_url": drive_view_url,
        "local_path": str(path.resolve()),
        "filename": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "captured_at_utc": utc_now(),
        "notes": notes,
    }


def make_synthetic_provenance(
    *,
    generator_version: str,
    seed: int,
    scenario: str,
    assumptions: dict[str, Any],
    parent_real_checksum: str | None,
) -> dict[str, Any]:
    return {
        "data_kind": "synthetic_simulator_trajectories",
        "not_real_observations": True,
        "not_evidence_of_sliit_se_learning_gains": True,
        "generator_version": generator_version,
        "seed": seed,
        "scenario": scenario,
        "assumptions": assumptions,
        "parent_real_dataset_sha256": parent_real_checksum,
        "created_at_utc": utc_now(),
    }
