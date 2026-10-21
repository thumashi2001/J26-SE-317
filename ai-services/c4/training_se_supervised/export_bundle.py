"""Export selected models, schemas, checksums, and evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .catalogue import catalogue_hash, catalogue_payload
from .paths import ensure_dir, sha256_file, write_json
from .protocol import DOMAIN_MARKERS, PROTOCOL_VERSION


def build_manifest(export_dir: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(export_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "manifest.json":
            continue
        rel = path.relative_to(export_dir).as_posix()
        manifest[rel] = sha256_file(path)
    write_json(export_dir / "manifest.json", manifest)
    return manifest


def export_run_bundle(run_dir: Path) -> Path:
    """Copy evidence + models into export_bundle/ and write SHA-256 manifest."""
    run_dir = Path(run_dir)
    export_dir = ensure_dir(run_dir / "export_bundle")

    # Fresh export directory contents (safe: only under this run)
    for child in list(export_dir.iterdir()):
        if child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)

    copy_names = [
        "frozen_contract.json",
        "generation_index.json",
        "split_ids.json",
        "leakage_checks.json",
        "selection_val.json",
        "comparison_val_response.json",
        "comparison_val_exam_score.json",
        "comparison_val_pass.json",
        "scenario_sensitivity.json",
        "runtime_versions.json",
        "pass_enablement.json",
        "SELECTION_FROZEN.json",
        "feature_schema_response.json",
        "feature_schema_exam.json",
        "target_definitions.json",
    ]
    for name in copy_names:
        src = run_dir / name
        if src.is_file():
            shutil.copy2(src, export_dir / name)

    models_src = run_dir / "models"
    if models_src.is_dir():
        shutil.copytree(models_src, export_dir / "models")

    cards_src = run_dir / "model_cards"
    if cards_src.is_dir():
        shutil.copytree(cards_src, export_dir / "model_cards")

    final_src = run_dir / "final_test"
    if final_src.is_dir():
        shutil.copytree(final_src, export_dir / "final_test")

    write_json(
        export_dir / "topic_catalogue.json",
        {**catalogue_payload(), "sha256": catalogue_hash()},
    )
    write_json(
        export_dir / "synthetic_provenance.json",
        {
            **DOMAIN_MARKERS,
            "protocol": PROTOCOL_VERSION,
            "note": (
                "All data and labels are synthetic. "
                "real_exam_validation=false. Not validated on real SE students."
            ),
        },
    )

    # Mark file
    write_json(
        export_dir / "DOMAIN_MARKERS.json",
        DOMAIN_MARKERS,
    )

    build_manifest(export_dir)
    return export_dir


def verify_manifest(export_dir: Path) -> dict[str, Any]:
    export_dir = Path(export_dir)
    manifest = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))
    mismatches = []
    for rel, expected in manifest.items():
        path = export_dir / rel
        if not path.is_file():
            mismatches.append({"path": rel, "error": "missing"})
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": actual})
    return {"ok": len(mismatches) == 0, "n": len(manifest), "mismatches": mismatches}
