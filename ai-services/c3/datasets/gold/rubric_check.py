"""Checks a gold-rubric document before it may be used for blind marking.

Usage: python -m datasets.gold.rubric_check <rubric.json> [--dataset DIR] [--require-gold]

A document is `{format, question_id, provenance, rubric}`. The `rubric` object is the marking engine's own `Rubric`, so it is
validated with the engine's schema (app/schemas/marking.py) and its cross-field checks (validate_rubric), then with a few extra
rules a human-marked rubric needs (several levels, distinct descriptors, concepts for positive levels).

The provenance record is a CLAIM made by a person. This checker confirms that the claim is complete and consistent; it cannot
confirm that a lecturer really reviewed the rubric, and passing it never turns an AI-drafted rubric into a validated one.
Read-only.
"""

import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from app.schemas.marking import Rubric
from services.marking.rubric_validator import RubricValidationError, validate_rubric

FORMAT = "c3-gold-rubric/1"
STATUSES = ("template", "ai_drafted", "lecturer_validated")
MIN_LEVELS = 3
MIN_DESCRIPTOR_CHARS = 20
PLACEHOLDER = re.compile(r"\btodo\b|\btbd\b|fill in|placeholder|lorem ipsum|<[^>]*>|\bxxx+\b", re.IGNORECASE)


def _date(value: object) -> datetime.date | None:
    """Parse an ISO date, or None when it is not valid."""
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def _provenance_problems(doc: dict) -> list[str]:
    """Problems with who wrote and approved the rubric and when."""
    prov = doc.get("provenance")
    if not isinstance(prov, dict):
        return ["provenance: missing or not an object"]
    status = prov.get("status")
    if status not in STATUSES:
        return [f"provenance.status {status!r} is not one of {list(STATUSES)}"]
    if status == "template":
        return ["provenance.status is 'template': this is the unfilled template, not a rubric"]
    problems = []
    drafted_by, validated_by = str(prov.get("drafted_by", "")).strip(), str(prov.get("validated_by", "")).strip()
    drafted_on, validated_on = _date(prov.get("drafted_on")), _date(prov.get("validated_on"))
    if not drafted_by:
        problems.append("provenance.drafted_by is required (the person, or the AI tool and version, that drafted the rubric)")
    if drafted_on is None:
        problems.append("provenance.drafted_on must be an ISO date (YYYY-MM-DD)")
    if status == "ai_drafted":
        if validated_by or str(prov.get("validated_on", "")).strip():
            problems.append("an 'ai_drafted' rubric must not carry validated_by/validated_on; set 'lecturer_validated' only "
                            "after a lecturer has reviewed it")
    else:
        if not validated_by:
            problems.append("provenance.validated_by is required for 'lecturer_validated' (the reviewing lecturer)")
        elif drafted_by and validated_by.casefold() == drafted_by.casefold():
            problems.append("provenance.validated_by must be a different person from drafted_by")
        if validated_on is None:
            problems.append("provenance.validated_on must be an ISO date (YYYY-MM-DD)")
        elif drafted_on is not None and validated_on < drafted_on:
            problems.append("provenance.validated_on is earlier than drafted_on")
    return problems


def _engine_problems(raw: object) -> tuple[Rubric | None, list[str]]:
    """Check the rubric loads in the marking engine; return it with any problems."""
    try:
        rubric = Rubric.model_validate(raw)
    except ValidationError as exc:
        return None, [f"rubric.{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
    try:
        validate_rubric(rubric)
    except RubricValidationError as exc:
        return rubric, [f"rubric: {message}" for message in exc.errors]
    return rubric, []


def _gold_problems(rubric: Rubric) -> list[str]:
    """Gold-rubric rules: a zero level and a full-marks level, distinct labels and descriptors, concepts for positive levels, no placeholder text."""
    problems = []
    texts = [("rubric_id", rubric.rubric_id), ("title", rubric.title)]
    for c in rubric.criteria:
        texts += [(f"{c.criterion_id}.description", c.description)] + [(f"{c.criterion_id}.required_concepts", t) for t in c.required_concepts]
        levels = c.scoring_levels
        if len(levels) < MIN_LEVELS:
            problems.append(f"criterion {c.criterion_id}: needs at least {MIN_LEVELS} levels (a 2-level criterion is binary)")
        marks = [lv.mark for lv in levels]
        if len(set(marks)) != len(marks):
            problems.append(f"criterion {c.criterion_id}: level marks must be distinct")
        if 0 not in marks:
            problems.append(f"criterion {c.criterion_id}: needs a level worth 0 marks")
        if c.max_marks not in marks:
            problems.append(f"criterion {c.criterion_id}: needs a level worth the criterion's max_marks ({c.max_marks})")
        if len({lv.label.casefold() for lv in levels}) != len(levels):
            problems.append(f"criterion {c.criterion_id}: level labels must be distinct")
        if len({lv.descriptor.casefold() for lv in levels}) != len(levels):
            problems.append(f"criterion {c.criterion_id}: level descriptors must be distinct")
        for lv in levels:
            texts += [(f"{c.criterion_id}.{lv.level_id}.label", lv.label), (f"{c.criterion_id}.{lv.level_id}.descriptor", lv.descriptor)]
            texts += [(f"{c.criterion_id}.{lv.level_id}.required_concepts", t) for t in lv.required_concepts]
            if len(lv.descriptor.strip()) < MIN_DESCRIPTOR_CHARS:
                problems.append(f"level {c.criterion_id}.{lv.level_id}: descriptor is shorter than {MIN_DESCRIPTOR_CHARS} characters")
            if lv.mark > 0 and not (lv.required_concepts or c.required_concepts):
                problems.append(f"level {c.criterion_id}.{lv.level_id}: a positive level needs required_concepts "
                                "(on the level or on the criterion)")
    problems += [f"{where}: contains placeholder text" for where, text in texts if PLACEHOLDER.search(text)]
    return problems


def load_question(dataset_dir: Path, question_id: str) -> dict | None:
    """The question's row from 01_question_bank.csv, or None if it is absent or not eligible."""
    with open(Path(dataset_dir) / "01_question_bank.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["question_id"] == question_id and row["eligibility_status"] == "eligible":
                return row
    return None


def check_document(doc: object, question: dict | None = None) -> list[str]:
    """Every problem found in a gold-rubric document (empty list = complete and consistent)."""
    if not isinstance(doc, dict):
        return ["document must be a JSON object"]
    problems = []
    if doc.get("format") != FORMAT:
        problems.append(f"format must be {FORMAT!r}")
    question_id = str(doc.get("question_id", "")).strip()
    if not question_id:
        problems.append("question_id is required")
    elif PLACEHOLDER.search(question_id):
        problems.append("question_id: contains placeholder text")
    problems += _provenance_problems(doc)
    rubric, engine = _engine_problems(doc.get("rubric"))
    problems += engine
    if rubric is not None:
        problems += _gold_problems(rubric)
        if question is not None:
            if question["question_id"] != question_id:
                problems.append("question_id does not match the question it was checked against")
            total = sum(c.max_marks for c in rubric.criteria)
            if abs(total - float(question["marks"])) > 1e-9:
                problems.append(f"criterion max_marks add up to {total:g}, but the question is worth {question['marks']}")
    return problems


def usable_as_gold(doc: dict, problems: list[str]) -> bool:
    """True only for a problem-free document whose provenance claims lecturer validation."""
    return not problems and isinstance(doc, dict) and doc.get("provenance", {}).get("status") == "lecturer_validated"


def check_file(path: Path, dataset_dir: Path | None = None) -> tuple[dict | None, list[str]]:
    """Check one gold-rubric file and list its problems."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"cannot read {path}: {exc}"]
    question = None
    if dataset_dir is not None and isinstance(doc, dict):
        question = load_question(dataset_dir, str(doc.get("question_id", "")))
        if question is None:
            return doc, check_document(doc) + [f"question_id {doc.get('question_id')!r} is not an eligible question in {dataset_dir}"]
    return doc, check_document(doc, question)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description="Check a gold-rubric document")
    ap.add_argument("file", type=Path)
    ap.add_argument("--dataset", type=Path, default=None, help="dataset directory; also checks the question exists and its marks")
    ap.add_argument("--require-gold", action="store_true", help="fail unless provenance claims lecturer validation")
    args = ap.parse_args(argv)
    doc, problems = check_file(args.file, args.dataset)
    for p in problems:
        print(f"PROBLEM  {p}")
    if problems:
        return 1
    status = doc["provenance"]["status"]
    print(f"OK  complete and consistent (provenance.status = {status}); usable as gold: {'yes' if usable_as_gold(doc, problems) else 'no'}")
    return 0 if usable_as_gold(doc, problems) or not args.require_gold else 1


if __name__ == "__main__":
    sys.exit(main())
