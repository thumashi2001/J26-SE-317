"""Import a C4 research bundle ZIP into runtime-artifacts/ and verify manifest SHA-256.

Does not copy bundle ``source/`` over the live ``training/`` tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def import_bundle(zip_path: Path, dest_root: Path) -> Path:
    zip_path = zip_path.resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(f"Bundle ZIP not found: {zip_path}")

    dest = dest_root / zip_path.stem
    dest_root.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        # Preserve historical runs: keep existing dir; re-extract into a sibling stamp only if needed.
        # Default: verify in place if manifest already present.
        if (dest / "manifest.json").is_file():
            print(f"Bundle already present at {dest}; verifying checksums only.")
            verify_manifest(dest)
            return dest
        raise FileExistsError(
            f"Destination exists without manifest: {dest}. Remove or rename before re-import."
        )

    dest.mkdir(parents=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)

    # Some ZIPs nest an extra top folder; flatten if single child equals stem-ish content.
    children = [p for p in dest.iterdir()]
    if len(children) == 1 and children[0].is_dir() and (children[0] / "manifest.json").is_file():
        nested = children[0]
        for item in nested.iterdir():
            shutil.move(str(item), str(dest / item.name))
        nested.rmdir()

    if not (dest / "manifest.json").is_file():
        raise FileNotFoundError(f"manifest.json missing after extract under {dest}")

    verify_manifest(dest)
    print(f"Imported OK → {dest}")
    print("Note: bundle source/ is reference-only; live training/ code was not overwritten.")
    return dest


def verify_manifest(bundle_dir: Path) -> None:
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    sha = manifest.get("sha256") or {}
    if not sha:
        raise ValueError("manifest.json has empty sha256 map")
    bad: list[str] = []
    for rel, expected in sha.items():
        path = bundle_dir / rel
        if not path.is_file():
            bad.append(f"MISSING {rel}")
            continue
        got = _sha256(path)
        if got != expected:
            bad.append(f"MISMATCH {rel}: got {got}, expected {expected}")
    if bad:
        raise RuntimeError("Checksum verification failed:\n" + "\n".join(bad))
    print(f"Verified {len(sha)} files against manifest sha256.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_path", type=Path, help="Local path to research bundle ZIP")
    parser.add_argument(
        "--dest-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "runtime-artifacts",
        help="Gitignored runtime-artifacts directory",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify an already-extracted bundle (pass directory as zip_path)",
    )
    args = parser.parse_args()
    if args.verify_only:
        verify_manifest(args.zip_path)
    else:
        import_bundle(args.zip_path, args.dest_root)


if __name__ == "__main__":
    main()
