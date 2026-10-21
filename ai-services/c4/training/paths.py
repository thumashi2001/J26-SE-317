"""Path helpers for local and Colab runs."""

from __future__ import annotations

import os
from pathlib import Path


def c4_root() -> Path:
    """Return ai-services/c4 root (parent of training/)."""
    return Path(__file__).resolve().parents[1]


def training_dir() -> Path:
    return Path(__file__).resolve().parent


def experiments_dir() -> Path:
    return c4_root() / "experiments"


def results_dir() -> Path:
    return experiments_dir() / "results"


def datasets_dir() -> Path:
    return c4_root() / "datasets"


def raw_dir() -> Path:
    return datasets_dir() / "raw"


def processed_dir() -> Path:
    return datasets_dir() / "processed"


def fixtures_dir() -> Path:
    return datasets_dir() / "fixtures"


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def resolve_output_root(drive_subdir: str | None = None, prefer_drive: bool = True) -> Path:
    """
    Choose an output root.

    Colab + Drive: /content/drive/MyDrive/<drive_subdir>
    Otherwise: ai-services/c4/experiments/results
    Fast working copies may still live under /content/c4_work when present.
    """
    if prefer_drive and drive_subdir:
        drive_root = Path("/content/drive/MyDrive") / drive_subdir
        if Path("/content/drive/MyDrive").exists():
            return ensure_dir(drive_root)
    content_work = Path("/content/c4_work")
    if content_work.parent.exists() and str(content_work).startswith("/content"):
        # Only use /content when actually on Colab-like layout.
        if Path("/content").exists():
            return ensure_dir(content_work)
    return ensure_dir(results_dir())


def stage_dirs(output_root: Path | str) -> dict[str, Path]:
    root = ensure_dir(output_root)
    dirs = {
        "root": root,
        "artifacts": ensure_dir(root / "artifacts"),
        "checkpoints": ensure_dir(root / "checkpoints"),
        "metrics": ensure_dir(root / "metrics"),
        "exports": ensure_dir(root / "exports"),
        "reports": ensure_dir(root / "reports"),
        "synthetic": ensure_dir(root / "synthetic"),
        "logs": ensure_dir(root / "logs"),
    }
    return dirs


def require_path(path: Path | str, hint: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Required path missing: {p}\n"
            f"Action: {hint}"
        )
    return p


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
