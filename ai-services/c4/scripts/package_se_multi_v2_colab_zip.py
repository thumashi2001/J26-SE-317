#!/usr/bin/env python3
"""ZIP se-path-multi-v2 Colab source from its import closure. Leaves the v1 ZIP alone."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "colab_zips" / "se_path_multi_v2_colab.zip"
SPEC = importlib.util.spec_from_file_location(
    "package_se_multi_v1_colab_zip",
    Path(__file__).with_name("package_se_multi_v1_colab_zip.py"),
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

ENTRYPOINTS = (
    "training_se_v2.multi_action_v2.smoke_runner",
    "training_se_v2.multi_action_v2.full_run",
)
MUST_INCLUDE = (
    "training_se_v1/__init__.py",
    "training_se_v1/protocol.py",
    "training_se_v1/catalogue.py",
    "training_se_v1/config.py",
    "training_se_v1/simulator.py",
    "training_se_v2/multi_action_v2/objective.py",
    "training_se_v2/multi_action_v2/environment.py",
    "training_se_v2/multi_action_v2/full_run.py",
    "training_se_v2/multi_action_v2/smoke_runner.py",
    "training_se_v2/multi_action_v2/serving.py",
)
EXTRA = (
    "README_SE_MULTI_V2_COLAB.md",
    "experiments/notebooks/v2/03_se_path_multi_v2.ipynb",
)


def main() -> None:
    files = MODULE.source_closure(ENTRYPOINTS, MUST_INCLUDE)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            if "fixtures" in path.parts or "__pycache__" in path.parts:
                continue
            zf.write(path, path.relative_to(ROOT).as_posix())
        for rel in EXTRA:
            zf.write(ROOT / rel, rel)
        zf.writestr(
            "FULL_TRAINING.txt",
            "Protocol se-path-multi-v2.\n"
            "Training revision se-path-multi-v2-coverage-r2.\n"
            "Every seed alternates Y3S1 and Y3S2. Do not assign one semester per seed.\n"
            "Set RUN_FULL_TRAINING=True only for the intentional Colab run.\n"
            "The full run writes a new timestamped directory and does not overwrite older runs.\n"
            "Budget: 80000 timesteps, seeds 0, 1, 2.\n"
            "Select on the shared validation bank mean_mastery_change, not return and not the held-out bank.\n"
            "activation_allowed is true only if the predeclared validation criterion passes.\n"
            "Do not copy the export into the student runtime unless that criterion passed.\n"
            "The live app is not switched by this export.\n",
        )
    print(f"Wrote {OUT}")
    for path in files:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
