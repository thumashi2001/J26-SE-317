"""Safely import a C4 SE simulation bundle ZIP into a dedicated runtime directory.

Verifies export_bundle/manifest.json (26 files) and run_metadata/checksums.json (4 files).
Never overwrites the ASSISTments research bundle directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

BUNDLE_STEM = "c4_se_simulation_bundle_20261012T084659312700Z"
EXPECTED_EXPORT_COUNT = 26
EXPECTED_META_COUNT = 4
REQUIRED_MODELS = (
    "export_bundle/models/seed_0/maskable_ppo_final.zip",
    "export_bundle/models/seed_1/maskable_ppo_final.zip",
    "export_bundle/models/seed_2/maskable_ppo_final.zip",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    dest = dest.resolve()
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or name.startswith("../") or "/../" in f"/{name}/":
            raise ValueError(f"Unsafe ZIP path rejected: {info.filename!r}")
        target = (dest / name).resolve()
        if not str(target).startswith(str(dest) + "\\") and not str(target).startswith(
            str(dest) + "/"
        ):
            if target != dest:
                raise ValueError(f"ZIP slip rejected: {info.filename!r} -> {target}")
        if info.is_dir() or name.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, target.open("wb") as out:
            out.write(src.read())


def verify_export_manifest(bundle_dir: Path) -> None:
    export = bundle_dir / "export_bundle"
    manifest_path = export / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sha = manifest.get("sha256") or {}
    if len(sha) != EXPECTED_EXPORT_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_EXPORT_COUNT} export checksums, got {len(sha)}"
        )
    bad: list[str] = []
    for rel, expected in sha.items():
        path = export / rel
        if not path.is_file():
            bad.append(f"MISSING {rel}")
            continue
        got = _sha256(path)
        if got != expected:
            bad.append(f"MISMATCH {rel}: got {got}, expected {expected}")
    if bad:
        raise RuntimeError("export_bundle checksum failure:\n" + "\n".join(bad))
    print(f"Verified {len(sha)} export_bundle checksums.")


def verify_run_metadata(bundle_dir: Path) -> None:
    meta = bundle_dir / "run_metadata"
    checksums_path = meta / "checksums.json"
    if not checksums_path.is_file():
        raise FileNotFoundError(f"Missing {checksums_path}")
    checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
    if len(checksums) != EXPECTED_META_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_META_COUNT} metadata checksums, got {len(checksums)}"
        )
    bad: list[str] = []
    for rel, expected in checksums.items():
        path = meta / rel
        if not path.is_file():
            bad.append(f"MISSING {rel}")
            continue
        got = _sha256(path)
        if got != expected:
            bad.append(f"MISMATCH {rel}: got {got}, expected {expected}")
    if bad:
        raise RuntimeError("run_metadata checksum failure:\n" + "\n".join(bad))
    print(f"Verified {len(checksums)} run_metadata checksums.")


def verify_models(bundle_dir: Path) -> None:
    missing = [p for p in REQUIRED_MODELS if not (bundle_dir / p).is_file()]
    if missing:
        raise FileNotFoundError("Missing model checkpoints:\n" + "\n".join(missing))
    print("Verified 3 MaskablePPO checkpoints present.")


def import_bundle(zip_path: Path, dest_root: Path) -> Path:
    zip_path = zip_path.resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(f"Bundle ZIP not found: {zip_path}")

    # Dedicated SE tree — never the ASSISTments research dirname
    dest = dest_root / "se_path_sim_v0" / zip_path.stem
    assistments = dest_root / "c4_maskable_ppo_research_bundle_20261012T062204868154Z"
    if dest.resolve() == assistments.resolve():
        raise RuntimeError("Refusing to extract into ASSISTments bundle directory")

    if dest.exists() and (dest / "export_bundle" / "manifest.json").is_file():
        print(f"Bundle already present at {dest}; verifying checksums only.")
        verify_export_manifest(dest)
        verify_run_metadata(dest)
        verify_models(dest)
        return dest

    if dest.exists():
        raise FileExistsError(
            f"Destination exists without a complete export_bundle: {dest}. "
            "Remove or rename before re-import."
        )

    dest.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        _safe_extract(zf, dest)

    verify_export_manifest(dest)
    verify_run_metadata(dest)
    verify_models(dest)
    print(f"Imported OK -> {dest}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "zip_path",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1]
        / "runtime-artifacts"
        / f"{BUNDLE_STEM}.zip",
    )
    parser.add_argument(
        "--dest-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "runtime-artifacts",
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        bundle = args.zip_path if args.zip_path.is_dir() else args.dest_root / "se_path_sim_v0" / BUNDLE_STEM
        verify_export_manifest(bundle)
        verify_run_metadata(bundle)
        verify_models(bundle)
    else:
        import_bundle(args.zip_path, args.dest_root)


if __name__ == "__main__":
    main()
