"""Build a Colab source ZIP with forward-slash archive paths.

Excludes caches, virtualenvs, secrets, datasets (except fixtures), checkpoints,
and experiment result artifacts. Does not modify existing run outputs.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
    ".venv",
    "venv",
    "env",
    "ENV",
    "node_modules",
    "checkpoints",
    "models",
    ".git",
}

EXCLUDE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".pt",
    ".pth",
    ".ckpt",
    ".onnx",
    ".safetensors",
    ".h5",
    ".pkl",
    ".joblib",
    ".bin",
    ".env",
    ".zip",
}

EXCLUDE_PATH_PARTS = {
    "datasets/raw",
    "datasets/processed",
    "experiments/results",
}


def should_exclude(rel_posix: str, path: Path) -> bool:
    parts = rel_posix.split("/")
    if any(p in EXCLUDE_DIR_NAMES for p in parts):
        return True
    for block in EXCLUDE_PATH_PARTS:
        if rel_posix == block or rel_posix.startswith(block + "/"):
            # Keep directory placeholders and fixtures.
            if rel_posix.endswith("/.gitkeep") or "/fixtures/" in f"/{rel_posix}":
                return False
            if path.name == ".gitkeep":
                return False
            return True
    if path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return True
    if path.name.startswith(".env"):
        return True
    if path.name == "c4-source-colab.zip":
        return True
    return False


def build_zip(c4_root: Path, out_zip: Path) -> list[str]:
    included: list[str] = []
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(c4_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(c4_root).as_posix()
            if should_exclude(rel, path):
                continue
            # Archive as ai-services/c4/... so Colab ZIP extract finds training/
            arcname = f"ai-services/c4/{rel}"
            zf.write(path, arcname)
            included.append(arcname)
    return included


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--c4-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to ai-services/c4",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output zip path (default: <c4-root>/c4-source-colab.zip)",
    )
    args = parser.parse_args()
    c4_root = args.c4_root.resolve()
    out_zip = (args.output or (c4_root / "c4-source-colab.zip")).resolve()
    included = build_zip(c4_root, out_zip)
    print(f"Wrote {out_zip}")
    print(f"Files: {len(included)}")
    # Verify forward slashes in archive names
    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()
    bad = [n for n in names if "\\" in n]
    if bad:
        raise SystemExit(f"Archive contains backslash paths: {bad[:5]}")
    print("Archive path style: forward-slash OK")
    print("Sample:", names[:5])


if __name__ == "__main__":
    main()
