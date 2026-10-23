"""Small shared helpers for the gold-evaluation tooling: canonical JSON bytes, hashes, and the provenance vocabulary."""

import hashlib
import json
from pathlib import Path

# Where a sheet or a set of returns comes from. 'toy_fixture' is simulated test material and is never real marking.
ORIGINS = ("toy_fixture", "pilot", "gold")
SIMULATED_NOTICE = "SIMULATED TOY FIXTURE - NOT HUMAN MARKS"


class GoldToolError(ValueError):
    """A request the tooling refuses (never repaired silently)."""


def canonical_bytes(obj: object) -> bytes:
    """Stable bytes for hashing and writing: sorted keys, 2-space indent, one trailing newline."""
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_hex(Path(path).read_bytes())
