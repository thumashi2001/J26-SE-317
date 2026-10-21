"""Safely import a C4 SE supervised simulation bundle ZIP.

Verifies all SHA-256 entries in export_bundle/manifest.json (expected 61).
Never overwrites ASSISTments or SE MaskablePPO runtime directories.
Does not overwrite live application source from export_bundle/source/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

BUNDLE_STEM = "c4_se_supervised_bundle_20261012T131046728530Z"
EXPECTED_MANIFEST_COUNT = 61
REQUIRED_MODELS = (
    "export_bundle/models/response_selected.joblib",
    "export_bundle/models/exam_score_selected.joblib",
    "export_bundle/models/pass_selected.joblib",
)
# Protected sibling trees — never extract into these paths.
PROTECTED_DIRNAMES = (
    "c4_maskable_ppo_research_bundle_20261012T062204868154Z",
    "se_path_sim_v0",
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
        dest_s = str(dest)
        target_s = str(target)
        if not (target_s == dest_s or target_s.startswith(dest_s + "\\") or target_s.startswith(dest_s + "/")):
            raise ValueError(f"ZIP slip rejected: {info.filename!r} -> {target}")
        if info.is_dir() or name.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, target.open("wb") as out:
            out.write(src.read())


def _manifest_map(export: Path) -> dict[str, str]:
    manifest_path = export / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise RuntimeError("manifest.json must be an object of path -> sha256")
    # Support either flat map or {"sha256": {...}}
    if "sha256" in manifest and isinstance(manifest["sha256"], dict):
        return {str(k): str(v) for k, v in manifest["sha256"].items()}
    return {str(k): str(v) for k, v in manifest.items() if k != "sha256"}


def verify_export_manifest(bundle_dir: Path) -> None:
    export = bundle_dir / "export_bundle"
    sha = _manifest_map(export)
    if len(sha) != EXPECTED_MANIFEST_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_MANIFEST_COUNT} export checksums, got {len(sha)}"
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


def verify_models(bundle_dir: Path) -> None:
    missing = [p for p in REQUIRED_MODELS if not (bundle_dir / p).is_file()]
    if missing:
        raise FileNotFoundError("Missing selected models:\n" + "\n".join(missing))
    print("Verified 3 selected supervised models present.")


def import_bundle(zip_path: Path, dest_root: Path) -> Path:
    zip_path = zip_path.resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(f"Bundle ZIP not found: {zip_path}")

    dest = dest_root / "se_supervised_sim_v0" / zip_path.stem
    for name in PROTECTED_DIRNAMES:
        protected = (dest_root / name).resolve()
        if dest.resolve() == protected or str(dest.resolve()).startswith(str(protected) + "\\") or str(
            dest.resolve()
        ).startswith(str(protected) + "/"):
            raise RuntimeError(f"Refusing to extract into protected path {protected}")

    if dest.exists() and (dest / "export_bundle" / "manifest.json").is_file():
        print(f"Bundle already present at {dest}; verifying checksums only.")
        verify_export_manifest(dest)
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
    verify_models(dest)
    print(f"Imported OK -> {dest}")
    print(
        "Note: export_bundle/source/ is for joblib class resolution reference only; "
        "live ai-services/c4 source was not overwritten."
    )
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
        bundle = (
            args.zip_path
            if args.zip_path.is_dir()
            else args.dest_root / "se_supervised_sim_v0" / BUNDLE_STEM
        )
        verify_export_manifest(bundle)
        verify_models(bundle)
    else:
        import_bundle(args.zip_path, args.dest_root)


if __name__ == "__main__":
    main()
