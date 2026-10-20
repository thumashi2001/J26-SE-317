"""Source loading, deterministic pre-screening and structure/OCR helpers (no LLM calls here)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import C3_ROOT

SOURCE_CSV = C3_ROOT / "datasets" / "source" / "questions_source.csv"
SOURCE_COLUMNS = ["question_id", "module_code", "source_type", "legacy_replaced_question_id", "question_text", "marks"]

_BAD_CHARS = set("\ufffd\u00ac\u00a6\u00a7\u00a4\u00b6\u00bf\u00a1\u25a0\u25a1\u25aa")
_PUNCT_ONLY = re.compile(r"[()\[\]{}.,;:\-]+")
_MULTIPART_RE = re.compile(r"(?:^|\s)\(\s*(?:[a-e]|i{1,3}|iv|v)\s*\)(?=\s)|(?:^|[\s.;:])(?:[a-e]|i{1,3}|iv)\)(?=\s)")
_CODE_HINT_RE = re.compile(
    r"\b(write|implement|develop|code)\b[^.?]{0,60}\b(code|program|function|class|query|sql|script|algorithm in)\b"
    r"|\bpseudo-?code\b|\bcode\s*:",
    re.IGNORECASE,
)
_DIAGRAM_HINT_RE = re.compile(
    r"\b(draw|sketch|diagram|figure|fig\.|shown below|given below|see the (?:figure|diagram)|uml|erd|dfd)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SourceQuestion:
    question_id: str
    module_code: str
    source_type: str
    legacy_replaced_question_id: str
    question_text: str
    marks: float


def normalize_ws(text: str) -> str:
    return " ".join(text.split())


def load_source(path: Path | None = None, limit: int | None = None) -> list[SourceQuestion]:
    frame = pd.read_csv(path or SOURCE_CSV, dtype=str, keep_default_na=False)
    missing = [c for c in SOURCE_COLUMNS if c not in frame.columns]
    if missing:
        raise ValueError(f"source file lacks columns: {missing}")
    rows = [
        SourceQuestion(
            question_id=r.question_id.strip(),
            module_code=r.module_code.strip(),
            source_type=r.source_type.strip(),
            legacy_replaced_question_id=r.legacy_replaced_question_id.strip(),
            question_text=r.question_text,
            marks=float(r.marks),
        )
        for r in frame.itertuples(index=False)
    ]
    if len({q.question_id for q in rows}) != len(rows):
        raise ValueError("duplicate question_id in source")
    for q in rows:
        if not q.question_text.strip() or q.marks <= 0:
            raise ValueError(f"source question {q.question_id} has empty text or non-positive marks")
    return rows[:limit] if limit else rows


def ocr_noise_ratio(text: str) -> float:
    """Share of whitespace tokens that look like OCR debris (replacement chars, symbol-only fragments)."""
    tokens = text.split()
    if not tokens:
        return 0.0
    bad = 0
    for tok in tokens:
        if any(ch in _BAD_CHARS for ch in tok):
            bad += 1
        elif (
            len(tok) >= 2
            and not any(ch.isalnum() for ch in tok)
            and len(set(tok)) >= 2
            and not _PUNCT_ONLY.fullmatch(tok)
        ):
            bad += 1
        elif re.search(r"[A-Za-z][^\w\s]{2,}[A-Za-z]", tok):
            bad += 1
    return round(bad / len(tokens), 4)


def multipart_markers(text: str) -> int:
    return len(_MULTIPART_RE.findall(text))


def code_or_diagram_hint(text: str) -> bool:
    return bool(_CODE_HINT_RE.search(text) or _DIAGRAM_HINT_RE.search(text))


def mark_scale_bucket(marks: float) -> str:
    if marks <= 10:
        return "small"
    if marks <= 25:
        return "medium"
    return "large"


def is_verbatim(fragment: str, source_text: str) -> bool:
    """True if fragment (whitespace-normalised) occurs verbatim in the whitespace-normalised source."""
    frag = normalize_ws(fragment)
    return bool(frag) and frag in normalize_ws(source_text)


def hyphen_ws_equivalent(raw: str, cleaned: str) -> bool:
    """clean_text may only change whitespace and hyphenation: compare after dropping both."""
    strip = lambda s: re.sub(r"[\s\-\u00ad\u2010\u2011]", "", s)  # noqa: E731
    return strip(raw) == strip(cleaned)


def dry_run_stats(questions: list[SourceQuestion], ocr_threshold: float) -> dict:
    scales: dict[str, int] = {}
    for q in questions:
        key = f"{q.marks:g}"
        scales[key] = scales.get(key, 0) + 1
    return {
        "questions": len(questions),
        "modules": sorted({q.module_code for q in questions}),
        "total_marks": sum(q.marks for q in questions),
        "mark_scales": dict(sorted(scales.items(), key=lambda kv: float(kv[0]))),
        "ocr_flagged": [q.question_id for q in questions if ocr_noise_ratio(q.question_text) > ocr_threshold],
        "multipart_marker_candidates": [q.question_id for q in questions if multipart_markers(q.question_text) >= 2],
        "code_or_diagram_hints": [q.question_id for q in questions if code_or_diagram_hint(q.question_text)],
    }
