"""
AdaptiveLearnSE Component 3 - Training-only retrieval corpus for Vector RAG.

The corpus is built from the TRAIN split of a repaired dataset directory only: question reference answers and
question-level expected concepts of eligible train questions. Validation/test questions, student answers and marks are never read, so retrieval
cannot leak held-out information. Every document carries provenance (question id, module, source file hash).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_training_corpus(dataset_dir: str | Path, split: str = "train") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (documents, provenance). Only questions whose own split is `split` (default train) are used."""
    d = Path(dataset_dir)
    qfile = d / "01_question_bank.csv"
    questions = _read(qfile)
    questions = questions[questions["split"] == split]
    if "eligibility_status" in questions.columns:  # eligible only: ineligible/quarantined questions are never indexed
        questions = questions[questions["eligibility_status"] == "eligible"]
    module_of = dict(zip(questions["question_id"], questions["module_code"], strict=False))

    docs: list[dict[str, Any]] = []
    seen: set[str] = set()
    dropped = 0

    def add(doc_id: str, title: str, content: str, source_type: str, question_id: str) -> None:
        nonlocal dropped
        content = " ".join(content.split())
        key = hashlib.sha256(content.lower().encode()).hexdigest()
        if not content:
            return
        if key in seen:  # exact duplicate content
            dropped += 1
            return
        seen.add(key)
        docs.append({"doc_id": doc_id, "title": title[:90] or doc_id, "content": content, "citation": f"{split}:{doc_id}",
                     "source_type": source_type, "question_id": question_id, "module_code": module_of.get(question_id, "")})

    for q in questions.to_dict("records"):
        add(f"{q['question_id']}#ref", q["question_text"], q["reference_answer"], "reference_answer", q["question_id"])
        # The rubric file only holds a generic placeholder criterion, so the question-level expected concepts are
        # the usable "rubric knowledge" document.
        concepts = q.get("expected_concepts", "").strip()
        if concepts and concepts.lower() not in ("nan", "none", "[]"):
            add(f"{q['question_id']}#concepts", q["question_text"], f"Expected concepts: {concepts}", "expected_concepts",
                q["question_id"])

    provenance = {
        "dataset_dir": d.name, "split_used": split, "questions_used": int(len(questions)), "documents": len(docs),
        "duplicates_dropped": dropped, "source_sha256": {qfile.name: _sha256(qfile)},
        "excluded": "validation/test questions, all student answers and all marks",
    }
    return docs, provenance
