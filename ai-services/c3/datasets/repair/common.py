"""Shared constants and IO helpers for the C3 dataset repair (deterministic, byte-stable output)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

DATASETS_DIR = Path(__file__).resolve().parents[1]
C3_ROOT = DATASETS_DIR.parent
ARCHIVE_DIR = DATASETS_DIR / "archive" / "C3-Phase3-v5-FINAL_original"
DEFAULT_OUT_DIR = DATASETS_DIR / "c3_phase3_v5_repaired"
TIER_SPEC_PATH = Path(__file__).resolve().parent / "validation_spec.json"

SOURCE_VERSION = "C3-Phase3-v5-FINAL"
REPAIRED_VERSION = "C3-Phase3-v5-REPAIRED-r2"
REPAIR_TOOL_VERSION = "1.0.0"

LABELS = ("FULL", "MOSTLY_CORRECT", "PARTIAL", "MISSING_CONCEPT", "MISCONCEPTION", "IRRELEVANT")
SPLITS = ("train", "validation", "test")

# Tokens that mean "missing value" when they are a whole cell or a whole list element.
NULL_TOKENS = frozenset({"nan", "none", "null", ""})
# Literal "nan" used as a word inside text (the lost-concept-name defect of the replacement block).
NAN_WORD = re.compile(r"(?<![A-Za-z0-9_])nan(?![A-Za-z0-9_])", re.IGNORECASE)

ORIGINAL_FILES = {
    "question_bank": "01_FINAL_question_bank.csv",
    "answers": "02_FINAL_controlled_answers.csv",
    "rubric": "03_FINAL_rubric_criteria.csv",
    "audit": "04_ORIGINAL_63_REPLACEMENT_AUDIT.csv",
}


class OriginalIntegrityError(RuntimeError):
    """The archived original does not match its SHA256SUMS.txt."""


class OutputExistsError(RuntimeError):
    """The default output directory already contains files."""


def sha256_bytes(data: bytes) -> str:
    """SHA-256 of bytes as hex."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """SHA-256 of a file's contents."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_original(archive_dir: Path = ARCHIVE_DIR) -> dict[str, str]:
    """Check every file listed in SHA256SUMS.txt; raise OriginalIntegrityError on any mismatch."""
    sums = Path(archive_dir) / "SHA256SUMS.txt"
    if not sums.exists():
        raise OriginalIntegrityError(f"Missing {sums}")
    verified: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition(" *")
        name = name.strip()
        target = Path(archive_dir) / name
        if not target.exists():
            raise OriginalIntegrityError(f"{name} listed in SHA256SUMS.txt is missing")
        actual = sha256_file(target)
        if actual != digest.strip():
            raise OriginalIntegrityError(f"{name}: sha256 mismatch (expected {digest.strip()}, got {actual})")
        verified[name] = actual
    if not verified:
        raise OriginalIntegrityError("SHA256SUMS.txt lists no files")
    return verified


def read_csv(path: Path) -> pd.DataFrame:
    """Read as text only; keep literal 'nan' and empty strings distinct from missing."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a table as UTF-8 CSV with Unix line endings."""
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def write_json(obj: Any, path: Path) -> None:
    """Write sorted, indented JSON with Unix line endings."""
    with Path(path).open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def fmt_float(value: float) -> str:
    """Float as text, the same way every time."""
    return f"{float(value)}"


def truncate_value(value: str, limit: int = 300) -> str:
    """Full value if short, else the first 300 chars plus the sha256 of the whole value."""
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...[sha256:{sha256_bytes(value.encode('utf-8'))}]"


def parse_json_list(value: str) -> list[Any] | None:
    """Return the parsed JSON list, or None when the cell is not a JSON list."""
    text = value.strip()
    if not text.startswith("["):
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


def dump_json_list(items: list[Any]) -> str:
    """A list as JSON text for a CSV cell."""
    return json.dumps(items, ensure_ascii=False)


def drop_null_elements(value: str) -> tuple[str, int]:
    """Remove empty/'nan'/'None'/'null' elements from a JSON-list cell; return (new_value, removed_count)."""
    parsed = parse_json_list(value)
    if parsed is None:
        return value, 0
    kept = [e for e in parsed if str(e).strip().lower() not in NULL_TOKENS]
    removed = len(parsed) - len(kept)
    return (dump_json_list(kept), removed) if removed else (value, 0)


def normalise_text(text: str) -> str:
    """Collapse whitespace and ignore case, for comparing texts."""
    return " ".join(text.split()).casefold()


def load_original(archive_dir: Path = ARCHIVE_DIR) -> dict[str, pd.DataFrame]:
    """Load the untouched original release files from the archive."""
    return {key: read_csv(Path(archive_dir) / name) for key, name in ORIGINAL_FILES.items()}


def ratio_concentration(ratios: list[float], top_n: int = 7) -> float:
    """Share of answers on the top_n most frequent ratios (3 d.p.), excluding the anchors 0 and 1.

    Copied unchanged from the removed datasets/generator/checks.py (same definition, same 0.45 threshold)."""
    from collections import Counter

    inner = [round(r, 3) for r in ratios if 0.0 < r < 1.0]
    if not inner:
        return 0.0
    return sum(c for _, c in Counter(inner).most_common(top_n)) / len(inner)
