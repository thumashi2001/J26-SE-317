from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .protocol import PROTOCOL_VERSION


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_run_dir(root: Path | str, mode: str) -> Path:
    """Create a unique run folder; never overwrite an existing path."""
    root = ensure_dir(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f")[:-3] + "Z"
    name = f"train_{mode}_{PROTOCOL_VERSION}_{stamp}"
    out = root / name
    if out.exists():
        raise FileExistsError(f"run dir already exists: {out}")
    out.mkdir(parents=True)
    return out


def write_json(path: Path, obj: object) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> object:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
