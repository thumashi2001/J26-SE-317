"""Build c4-se-v1-source-colab.zip for se-path-sim-v1 Colab notebook.

Includes training_se_v1/, catalogues/, SE v1 docs/notebook, requirements.
Excludes credentials, venvs, caches, v0 packages, result binaries.
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
    "results",
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


def _wanted(rel: str) -> bool:
    if rel.startswith("training_se_v1/"):
        return True
    if rel.startswith("catalogues/"):
        return True
    if rel == "experiments/07_se_path_simulation_v1.ipynb":
        return True
    if rel == "experiments/_generate_se_path_v1_notebook.py":
        return True
    if rel.startswith("docs/") and (
        "SE_PATH_SIM_V1" in rel
        or "SE_MODEL_TRAINING_SPEC" in rel
        or rel.endswith("SE_PATH_SIM_V1.md")
    ):
        return True
    if rel in {
        "requirements-training.txt",
        "requirements.txt",
        "requirements-dev.txt",
        "scripts/package_se_v1_colab_zip.py",
        "README_SE_V1_COLAB.md",
    }:
        return True
    return False


def should_exclude(rel_posix: str, path: Path) -> bool:
    parts = rel_posix.split("/")
    if any(p in EXCLUDE_DIR_NAMES for p in parts):
        return True
    if path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return True
    if path.name.startswith(".env") or path.name.startswith("_tmp_"):
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
    out_zip = (args.output or (c4_root / "c4-se-v1-source-colab.zip")).resolve()
    included = build_zip(c4_root, out_zip)
    print(f"Wrote {out_zip}")
    print(f"Files: {len(included)}")
    with zipfile.ZipFile(out_zip, "r") as zf:
        names = zf.namelist()
    if not any(n.endswith("training_se_v1/protocol.py") for n in names):
        raise SystemExit("ZIP missing training_se_v1/protocol.py")
    if not any(n.endswith("catalogues/c1_practice_full_2026_10.py") for n in names):
        raise SystemExit("ZIP missing catalogues/c1_practice_full_2026_10.py")
    print("Sample:", names[:8])


if __name__ == "__main__":
    main()
