"""
AdaptiveLearnSE Component 3 — Synthetic dataset release loader (C3-v6).

Reads a release directory produced by datasets/generate_c3_dataset.py:
questions.csv, rubrics.csv, answers.csv and manifest.json. Hashes recorded in the manifest are
verified on load so experiments always run against exactly the released files. Nothing here
fabricates or repairs data: malformed files raise ReleaseError.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_RELEASE_DIR = Path(__file__).resolve().parent / "c3_synthetic_v6"

QUESTION_JSON_COLUMNS = ("expected_concepts", "concept_graph")
ANSWER_JSON_COLUMNS = (
    "criterion_marks",
    "concept_status",
    "incorrect_concepts",
    "evidence_spans",
    "gold_mindmap",
)
SPLITS = ("train", "validation", "test")


class ReleaseError(RuntimeError):
    """Raised when a dataset release is missing, corrupt or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise ReleaseError(f"Missing release file: {path}")
    # keep_default_na=False: an empty answer must stay "" and the literal text "nan" must stay text
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _parse_json_columns(df: pd.DataFrame, columns: tuple[str, ...], where: str) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            raise ReleaseError(f"{where} is missing required column '{column}'")
        try:
            df[column] = df[column].map(json.loads)
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"{where}.{column} contains invalid JSON: {exc}") from exc
    return df


@dataclass(frozen=True)
class Release:
    path: Path
    manifest: dict[str, Any]
    questions: pd.DataFrame
    rubrics: pd.DataFrame
    answers: pd.DataFrame

    @property
    def version(self) -> str:
        return str(self.manifest["dataset_version"])

    def question(self, question_id: str) -> dict[str, Any]:
        rows = self.questions[self.questions["question_id"] == question_id]
        if rows.empty:
            raise KeyError(f"Unknown question_id {question_id}")
        return rows.iloc[0].to_dict()

    def rubric_for(self, question_id: str) -> dict[str, Any]:
        """Rubric in the C3 API schema (app.schemas.marking.Rubric)."""
        rows = self.rubrics[self.rubrics["question_id"] == question_id]
        if rows.empty:
            raise KeyError(f"No rubric rows for question_id {question_id}")
        criteria = []
        for _, row in rows.iterrows():
            criteria.append(
                {
                    "criterion_id": row["criterion_id"],
                    "description": row["description"],
                    "max_marks": float(row["max_marks"]),
                    "scoring_levels": json.loads(row["scoring_levels"]),
                }
            )
        rubric_id = str(rows.iloc[0]["rubric_id"])
        return {"rubric_id": rubric_id, "title": f"Rubric for {question_id}", "criteria": criteria}

    def split_questions(self, split: str) -> pd.DataFrame:
        if split not in SPLITS:
            raise ValueError(f"split must be one of {SPLITS}")
        return self.questions[self.questions["split"] == split].reset_index(drop=True)

    def split_answers(self, split: str, include_needs_review: bool = True) -> pd.DataFrame:
        if split not in SPLITS:
            raise ValueError(f"split must be one of {SPLITS}")
        df = self.answers[self.answers["split"] == split]
        if not include_needs_review:
            df = df[df["needs_review"] != "True"]
        return df.reset_index(drop=True)


def load_release(path: str | Path | None = None, verify_hashes: bool = True) -> Release:
    root = Path(path) if path else DEFAULT_RELEASE_DIR
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise ReleaseError(
            f"No dataset release at {root}. Generate it with: python datasets/generate_c3_dataset.py"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if verify_hashes:
        for name, meta in manifest.get("files", {}).items():
            file_path = root / name
            if not file_path.exists():
                raise ReleaseError(f"Manifest lists {name} but the file is missing")
            if sha256_file(file_path) != meta["sha256"]:
                raise ReleaseError(f"{name} does not match the sha256 recorded in manifest.json")

    questions = _parse_json_columns(_read_csv(root / "questions.csv"), QUESTION_JSON_COLUMNS, "questions.csv")
    rubrics = _read_csv(root / "rubrics.csv")
    answers = _parse_json_columns(_read_csv(root / "answers.csv"), ANSWER_JSON_COLUMNS, "answers.csv")

    for col in ("expected_mark", "max_marks", "normalized_mark", "word_count"):
        answers[col] = pd.to_numeric(answers[col], errors="raise")
    questions["max_marks"] = pd.to_numeric(questions["max_marks"], errors="raise")

    return Release(path=root, manifest=manifest, questions=questions, rubrics=rubrics, answers=answers)
