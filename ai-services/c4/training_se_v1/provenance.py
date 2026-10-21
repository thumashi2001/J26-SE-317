from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path | str, payload: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def synthetic_banner(**extra: Any) -> dict[str, Any]:
    from .protocol import DOMAIN, GENERATOR_VERSION, PROTOCOL_VERSION

    out = {
        "domain": DOMAIN,
        "synthetic": True,
        "protocol": PROTOCOL_VERSION,
        "generator": GENERATOR_VERSION,
        "not_real_se_students": True,
        "not_assistments": True,
    }
    out.update(extra)
    return out
