from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_run_dir(root: Path | str, mode: str) -> Path:
    """Create a unique run folder; never overwrite an existing path."""
    root = ensure_dir(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f")[:-3] + "Z"
    name = f"train_{mode}_se-path-sim-v1_{stamp}"
    out = root / name
    if out.exists():
        raise FileExistsError(f"run dir already exists: {out}")
    out.mkdir(parents=True)
    return out
