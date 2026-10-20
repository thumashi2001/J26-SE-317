"""Load and normalise ASSISTments 2009–2010 corrected Skill Builder CSV."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from .config import (
    ASSISTMENTS_CORRECTED_DRIVE_FILE_ID,
    ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL,
    ASSISTMENTS_EXPECTED_FILENAME,
    ASSISTMENTS_OFFICIAL_PAGE,
)
from .paths import ensure_dir, raw_dir
from .provenance import make_real_data_provenance, write_json

# Columns commonly present in the corrected Skill Builder export.
# Actual columns are inspected at load time; this list guides normalisation.
CANONICAL_COLUMNS = (
    "order_id",
    "assignment_id",
    "user_id",
    "assistment_id",
    "problem_id",
    "original",
    "correct",
    "attempt_count",
    "ms_first_response",
    "tutor_mode",
    "answer_type",
    "sequence_id",
    "student_class_id",
    "position",
    "type",
    "base_sequence_id",
    "skill_id",
    "skill_name",
    "teacher_id",
    "school_id",
    "hint_count",
    "hint_total",
    "overlap_time",
    "template_id",
    "answer_id",
    "answer_text",
    "first_action",
    "bottom_hint",
    "opportunity",
    "opportunity_original",
)


def try_download_corrected_csv(dest_dir: Path | str | None = None) -> Path:
    """
    Attempt optional download via gdown using the Drive file id published on the
    official ASSISTments page. On failure, raise with manual-upload instructions.
    Never substitutes synthetic data.
    """
    try:
        import gdown  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Optional automatic download requires the 'gdown' package.\n"
            f"Manual path: open {ASSISTMENTS_OFFICIAL_PAGE}\n"
            f"Download the corrected file: {ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL}\n"
            f"Place it as: {(Path(dest_dir) if dest_dir else raw_dir()) / ASSISTMENTS_EXPECTED_FILENAME}"
        ) from exc

    out_dir = ensure_dir(dest_dir or raw_dir())
    out_path = out_dir / ASSISTMENTS_EXPECTED_FILENAME
    url = f"https://drive.google.com/uc?id={ASSISTMENTS_CORRECTED_DRIVE_FILE_ID}"
    try:
        gdown.download(url, str(out_path), quiet=False)
    except Exception as exc:  # noqa: BLE001 - surface actionable guidance
        raise RuntimeError(
            "Automatic download of the corrected ASSISTments CSV failed.\n"
            "This pipeline will NOT fall back to synthetic data.\n"
            f"1) Open {ASSISTMENTS_OFFICIAL_PAGE}\n"
            f"2) Download the corrected file from {ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL}\n"
            f"3) Upload/copy it to {out_path}\n"
            f"Underlying error: {exc}"
        ) from exc

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(
            "Download reported completion but the CSV is missing or empty.\n"
            f"Manually download from {ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL} and place at {out_path}."
        )
    return out_path


def resolve_csv_path(
    csv_path: str | Path | None = None,
    *,
    allow_download: bool = False,
    search_dirs: list[Path] | None = None,
) -> Path:
    if csv_path is not None:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(
                f"ASSISTments CSV not found at {path}.\n"
                f"Download the corrected file from {ASSISTMENTS_OFFICIAL_PAGE} "
                f"({ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL}) and pass its path."
            )
        return path

    candidates: list[Path] = []
    for d in search_dirs or [raw_dir(), Path("/content"), Path.cwd()]:
        candidates.extend(
            [
                d / ASSISTMENTS_EXPECTED_FILENAME,
                d / "skill_builder_data_corrected_collapsed.csv",
                d / "ASSISTments2009-2010.csv",
            ]
        )
        candidates.extend(d.glob("*skill*builder*corrected*.csv"))

    for c in candidates:
        if c.exists() and c.stat().st_size > 0:
            return c

    if allow_download:
        return try_download_corrected_csv(raw_dir())

    raise FileNotFoundError(
        "No ASSISTments corrected CSV found.\n"
        f"Official page: {ASSISTMENTS_OFFICIAL_PAGE}\n"
        f"Corrected Drive link: {ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL}\n"
        f"Place the file at {raw_dir() / ASSISTMENTS_EXPECTED_FILENAME} or pass csv_path=...\n"
        "Synthetic fixtures must be loaded explicitly via load_fixture_csv() for software tests only."
    )


def load_assistments_csv(csv_path: str | Path, *, encoding: str = "ISO-8859-1") -> pd.DataFrame:
    path = Path(csv_path)
    # Prefer latin-1 / ISO-8859-1; fall back to utf-8.
    try:
        df = pd.read_csv(path, encoding=encoding, low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    if df.empty:
        raise ValueError(f"CSV is empty: {path}")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def parse_skill_tokens(skill_id: Any) -> list[str]:
    """
    Preserve multi-skill tags.

    Corrected ASSISTments often collapses multi-skill problems as skill1_skill2 in one row.
    We split on '_' when tokens look like numeric ids; otherwise keep the whole string.
    """
    if skill_id is None or (isinstance(skill_id, float) and pd.isna(skill_id)):
        return []
    text = str(skill_id).strip()
    if not text or text.lower() == "nan":
        return []
    # Numeric multi-skill collapse: 1_27_33
    if re.fullmatch(r"\d+(?:_\d+)+", text):
        return text.split("_")
    # Single numeric id
    if re.fullmatch(r"\d+", text):
        return [text]
    # Non-numeric skill labels: keep intact (do not split names on underscores blindly)
    return [text]


def normalise_interactions(df: pd.DataFrame) -> pd.DataFrame:
    """Produce a tidy interaction table without dropping multi-skill information."""
    required = {"user_id", "correct"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns {sorted(missing)}. Found: {list(df.columns)}")

    out = df.copy()
    if "order_id" not in out.columns:
        out["order_id"] = range(len(out))
    if "skill_id" not in out.columns:
        out["skill_id"] = out["skill_name"] if "skill_name" in out.columns else "unknown"

    out["user_id"] = out["user_id"].astype(str)
    # correct may be 0/1 or float; coerce carefully
    out["correct"] = pd.to_numeric(out["correct"], errors="coerce")
    out = out.dropna(subset=["correct"]).copy()
    out["correct"] = (out["correct"] > 0).astype(int)

    out["skill_id_raw"] = out["skill_id"].astype(str)
    out["skill_tokens"] = out["skill_id_raw"].map(parse_skill_tokens)
    out["n_skills"] = out["skill_tokens"].map(len)
    out["is_multi_skill"] = out["n_skills"] > 1
    # Primary skill for discrete action catalogue: first token; full set preserved in skill_tokens.
    out["primary_skill"] = out["skill_tokens"].map(lambda xs: xs[0] if xs else "unknown")

    # Chronology: ASSISTments docs note order_id is not a true timestamp.
    # Within-learner sort by order_id is the community convention; documented as a limitation.
    out["order_id"] = pd.to_numeric(out["order_id"], errors="coerce")
    out = out.dropna(subset=["order_id"]).copy()
    out["order_id"] = out["order_id"].astype("int64")
    out = out.sort_values(["user_id", "order_id"], kind="mergesort").reset_index(drop=True)
    out["learner_step"] = out.groupby("user_id").cumcount()

    for col in ("hint_count", "ms_first_response", "attempt_count", "opportunity"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out["data_kind"] = "real_assistments_observations"
    return out


def expand_multi_skill_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optional long-form expansion: one row per (interaction, skill token).

    Does not invent new outcomes; duplicates the same correctness label across tagged skills.
    Use for skill-level statistics; keep the collapsed table for interaction-level modelling.
    """
    rows = []
    for _, r in df.iterrows():
        tokens = r["skill_tokens"] or ["unknown"]
        for tok in tokens:
            rows.append(
                {
                    "user_id": r["user_id"],
                    "order_id": r["order_id"],
                    "learner_step": r["learner_step"],
                    "correct": r["correct"],
                    "skill": tok,
                    "skill_id_raw": r["skill_id_raw"],
                    "is_multi_skill": r["is_multi_skill"],
                    "data_kind": r["data_kind"],
                }
            )
    return pd.DataFrame(rows)


def save_provenance_for_csv(csv_path: Path | str, out_json: Path | str) -> dict[str, Any]:
    payload = make_real_data_provenance(
        source_path=csv_path,
        official_page=ASSISTMENTS_OFFICIAL_PAGE,
        drive_view_url=ASSISTMENTS_CORRECTED_DRIVE_VIEW_URL,
        notes=(
            "Corrected Skill Builder 2009-2010. Multi-skill tags may appear collapsed as "
            "skill1_skill2 in a single student-problem row. Mathematics tutoring domain only; "
            "not SLIIT SE observations."
        ),
    )
    write_json(out_json, payload)
    return payload
