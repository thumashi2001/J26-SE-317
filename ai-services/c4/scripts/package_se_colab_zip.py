"""Build c4-se-source-colab.zip for the SE path simulation Colab notebook.

Includes training_se/, SE docs, SE notebook helpers, requirements-training.txt,
and packaging metadata. Excludes credentials, venvs, caches, raw datasets,
ASSISTments runtime-artifacts / model binaries, and large result folders.
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
    "runtime-artifacts",
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

# Paths relative to c4 root to include preferentially (plus shared small deps).
INCLUDE_PREFIXES = (
    "training_se/",
    "experiments/05_se_path_simulation.ipynb",
    "experiments/_generate_se_notebook.py",
    "docs/SE_",
    "docs/SE_PATH_SIM",
    "requirements-training.txt",
    "requirements.txt",
    "requirements-dev.txt",
    "scripts/package_se_colab_zip.py",
)


def _wanted(rel: str) -> bool:
    if rel.startswith("training_se/"):
        return True
    if rel == "experiments/05_se_path_simulation.ipynb":
        return True
    if rel == "experiments/_generate_se_notebook.py":
        return True
    if rel.startswith("docs/") and (
        "SE_" in rel or "SE_PATH" in rel or rel.endswith("SE_MODEL_TRAINING_SPEC.md")
    ):
        return True
    if rel in {
        "requirements-training.txt",
        "requirements.txt",
        "requirements-dev.txt",
        "scripts/package_se_colab_zip.py",
        "README_SE_COLAB.md",
    }:
        return True
    return False


def should_exclude(rel_posix: str, path: Path) -> bool:
    parts = rel_posix.split("/")
    if any(p in EXCLUDE_DIR_NAMES for p in parts):
        return True
    if path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return True
    if path.name.startswith(".env"):
        return True
    if not _wanted(rel_posix):
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
            arcname = f"ai-services/c4/{rel}"
            zf.write(path, arcname)
            included.append(arcname)
    return included


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c4-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    c4_root = args.c4_root.resolve()
    out_zip = (args.output or (c4_root / "c4-se-source-colab.zip")).resolve()
    included = build_zip(c4_root, out_zip)
    print(f"Wrote {out_zip}")
    print(f"Files: {len(included)}")
    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()
    if not any(n.endswith("training_se/protocol.py") for n in names):
        raise SystemExit("ZIP missing training_se/protocol.py")
    print("Sample:", names[:8])


if __name__ == "__main__":
    main()
