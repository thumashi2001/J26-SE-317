"""Reproducible LLM-driven synthetic dataset generator for Component 3 (C3-v6)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
C3_ROOT = PACKAGE_DIR.parents[1]
DATASET_VERSION = "C3-v6.0.0"
TIER_SPEC_PATH = PACKAGE_DIR / "tier_spec.json"
DEFAULT_SEED = 20261021

if str(C3_ROOT) not in sys.path:  # make `app` / `services` importable when run as a script
    sys.path.insert(0, str(C3_ROOT))


def load_tier_spec(path: Path | None = None) -> dict:
    with (path or TIER_SPEC_PATH).open(encoding="utf-8") as fh:
        return json.load(fh)


def tier_spec_sha256(path: Path | None = None) -> str:
    return hashlib.sha256((path or TIER_SPEC_PATH).read_bytes()).hexdigest()
