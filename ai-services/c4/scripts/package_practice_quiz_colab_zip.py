#!/usr/bin/env python3
"""Build a self-contained ZIP for the inactive this-quiz pass pipeline."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "colab_zips" / "practice_quiz_pass_v1_colab.zip"
FILES = (
    "training_practice_quiz_v1/__init__.py",
    "training_practice_quiz_v1/protocol.py",
    "training_practice_quiz_v1/blueprint.py",
    "training_practice_quiz_v1/generate.py",
    "training_practice_quiz_v1/train.py",
    "training_practice_quiz_v1/smoke_runner.py",
    "training_practice_quiz_v1/serving.py",
    "README_PRACTICE_QUIZ_COLAB.md",
    "experiments/notebooks/practice_quiz/01_practice_quiz_pass_v1.ipynb",
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in FILES:
            path = ROOT / rel
            if not path.is_file():
                raise SystemExit(f"missing {rel}")
            archive.write(path, rel)
    with zipfile.ZipFile(OUT) as archive:
        names = set(archive.namelist())
    missing = [rel for rel in FILES if rel not in names]
    if missing:
        raise SystemExit(f"zip missing {missing}")
    print(f"OK {OUT} members={len(names)}")


if __name__ == "__main__":
    main()
