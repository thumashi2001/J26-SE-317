"""Blind annotation sheets out, human returns in (semantic paraphrase benchmark).

SIMPLE ENGLISH
    `blind_rows` makes the sheet an annotator sees: question, concept and answer only. It leaves out the category, the AI-drafted
    proposed label and its rationale, so the annotator is not anchored by them. `ingest_returns` copies what annotators wrote
    into the item records; `ingest_adjudication` does the same for an adjudicator's decision. Nothing here ever creates a label
    by itself: with no returns, every item stays `draft_unreviewed`.
"""

from __future__ import annotations

import copy
import csv
from pathlib import Path

from datasets.paraphrase_benchmark.validate import LABELS, derive_final_label, derive_status

SHEET_COLUMNS = ["item_id", "question_text", "concept", "student_answer", "label", "rationale"]


def blind_rows(items: list[dict], split: str | None = None) -> list[dict]:
    """Annotator-facing rows: no category, no draft label, no group, no split."""
    return [
        {
            "item_id": i["item_id"],
            "question_text": i["question_text"],
            "concept": i["concept"],
            "student_answer": i["student_answer"],
            "label": "",
            "rationale": "",
        }
        for i in items
        if split in (None, i["split"])
    ]


def write_sheet(rows: list[dict], path: Path) -> None:
    """Write a sheet as UTF-8 CSV; refuses to overwrite so returned work can not be lost."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_return(path: Path) -> list[dict]:
    """Read a returned sheet."""
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _refresh(item: dict) -> None:
    """Recompute status and final label from the annotation records."""
    item["label_status"] = derive_status(item)
    item["final_label"] = derive_final_label(item)


def ingest_returns(items: list[dict], annotator_id: str, rows: list[dict]) -> list[dict]:
    """Add one annotator's returned rows to a copy of the items. Rows with a missing or invalid label are rejected loudly."""
    out = copy.deepcopy(items)
    index = {i["item_id"]: i for i in out}
    for row in rows:
        item = index.get(row.get("item_id"))
        if item is None:
            raise ValueError(f"unknown item_id {row.get('item_id')!r}")
        label = (row.get("label") or "").strip()
        if label not in LABELS:
            raise ValueError(f"{item['item_id']}: label {label!r} is not one of {LABELS}")
        if not (row.get("rationale") or "").strip():
            raise ValueError(f"{item['item_id']}: a rationale is required")
        if any(a["annotator_id"] == annotator_id for a in item["annotations"]):
            raise ValueError(f"{item['item_id']}: {annotator_id} already annotated this item")
        item["annotations"].append(
            {"annotator_id": annotator_id, "label": label, "rationale": row["rationale"].strip()}
        )
    for item in out:
        _refresh(item)
    return out


def ingest_adjudication(items: list[dict], adjudicator_id: str, rows: list[dict]) -> list[dict]:
    """Record an adjudicator's decision, only for items whose annotators actually disagree."""
    out = copy.deepcopy(items)
    index = {i["item_id"]: i for i in out}
    for row in rows:
        item = index.get(row.get("item_id"))
        if item is None or derive_status(item) != "needs_adjudication":
            raise ValueError(f"{row.get('item_id')!r} is not waiting for adjudication")
        item["adjudication"] = {
            "adjudicator_id": adjudicator_id,
            "label": (row.get("label") or "").strip(),
            "rationale": (row.get("rationale") or "").strip(),
        }
    for item in out:
        _refresh(item)
    return out


def disagreements(items: list[dict]) -> list[dict]:
    """Items that still need an adjudicator, with the annotators' labels and rationales."""
    return [
        {"item_id": i["item_id"], "annotations": i["annotations"]}
        for i in items
        if derive_status(i) == "needs_adjudication"
    ]
