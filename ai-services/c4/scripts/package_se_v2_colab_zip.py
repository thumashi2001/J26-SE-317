#!/usr/bin/env python3
"""Build a clean Colab ZIP for se-path-sim-v2 (no credentials / student IDs)."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "experiments" / "colab_zips"
OUT_ZIP = OUT_DIR / "se_path_sim_v2_colab.zip"

INCLUDE = [
    "training_se_v2",
    "training_se_v1/catalogue.py",
    "training_se_v1/config.py",
    "training_se_v1/__init__.py",
    "catalogues",
]


def _add_path(zf: zipfile.ZipFile, path: Path, arc_prefix: str = "") -> None:
    if path.is_file():
        arc = f"{arc_prefix}{path.name}" if not arc_prefix else f"{arc_prefix}{path.relative_to(ROOT).as_posix()}"
        # Prefer relative to ROOT for nested paths
        try:
            arc = path.relative_to(ROOT).as_posix()
        except ValueError:
            arc = path.name
        zf.write(path, arcname=arc)
        return
    for p in path.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc"):
            zf.write(p, arcname=p.relative_to(ROOT).as_posix())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE:
            path = ROOT / rel
            if not path.exists():
                raise SystemExit(f"missing: {path}")
            _add_path(zf, path)
        # Minimal notebook pointer
        nb = ROOT / "experiments" / "notebooks" / "v2" / "01_se_path_simulation_v2.ipynb"
        if nb.exists():
            zf.write(nb, arcname=nb.relative_to(ROOT).as_posix())
        readme = (
            "SE_PATH_SIM_V2_COLAB.txt",
            "1. Unzip in Colab runtime or mount Drive.\n"
            "2. Open experiments/notebooks/v2/01_se_path_simulation_v2.ipynb\n"
            "3. Run cells top-to-bottom; keep RUN_FULL_TRAINING=False for smoke.\n"
            "4. Export under MyDrive/AdaptiveLearnSE/c4_runs/se_path_sim_v2/\n"
            "5. Do not overwrite se_path_sim_v1 artifacts.\n",
        )
        zf.writestr(readme[0], readme[1])
    print(f"Wrote {OUT_ZIP}")


if __name__ == "__main__":
    main()
