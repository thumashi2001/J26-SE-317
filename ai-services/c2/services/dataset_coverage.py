
import json
from collections import Counter
from pathlib import Path

from services.module_registry import ModuleRegistry


BASE_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

SOURCE_TYPES = ("authentic", "synthetic")


def load_json_list(path):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON list")

    return data


def build_coverage_report(
    papers,
    questions,
    registry=None,
):
    """
    Calculate coverage for all configured modules.

    Papers and questions are counted separately.
    Authentic and synthetic sources remain separate.
    """
    registry = registry or ModuleRegistry()

    coverage = {}

    for module in registry.get_all():
        key = module["module_key"]

        coverage[key] = {
            "module_key": key,
            "module_code": module["module_code"],
            "module_name": module["module_name"],
            "semester": module["semester"],
            "authentic_papers": 0,
            "synthetic_papers": 0,
            "authentic_questions": 0,
            "synthetic_questions": 0,
            "marks_warnings": 0,
        }

    warnings = []
    paper_lookup = {}

    # Index known papers and count each paper once.
    for index, paper in enumerate(papers):
        metadata = paper.get("metadata") or {}
        source = paper.get("source") or {}

        code = metadata.get("module_code")
        source_type = source.get("source_type")

        module = registry.get_by_code(code) if code else None

        if module is None:
            warnings.append(
                f"Paper {index}: unknown module code {code!r}"
            )
            continue

        if source_type not in SOURCE_TYPES:
            warnings.append(
                f"Paper {index}: invalid source type {source_type!r}"
            )
            continue

        key = module["module_key"]
        coverage[key][f"{source_type}_papers"] += 1

        filename = source.get("filename")
        if filename:
            paper_lookup[(code, filename)] = source_type

    seen_question_ids = set()

    for index, question in enumerate(questions):
        question_id = question.get("question_id")
        code = question.get("module_code")
        source_type = question.get("source_type")

        if not question_id:
            warnings.append(
                f"Question {index}: missing question_id"
            )
            continue

        if question_id in seen_question_ids:
            warnings.append(
                f"Duplicate question_id: {question_id}"
            )
            continue

        seen_question_ids.add(question_id)

        module = registry.get_by_code(code) if code else None

        if module is None:
            warnings.append(
                f"{question_id}: unknown module code {code!r}"
            )
            continue

        if source_type not in SOURCE_TYPES:
            warnings.append(
                f"{question_id}: invalid source type"
            )
            continue

        key = module["module_key"]
        coverage[key][f"{source_type}_questions"] += 1

        if question.get("marks_status") in (
            "missing",
            "ambiguous",
            "needs_review",
        ):
            coverage[key]["marks_warnings"] += 1

        filename = question.get("source_filename")
        expected_source = paper_lookup.get((code, filename))

        if expected_source and expected_source != source_type:
            warnings.append(
                f"{question_id}: paper/question source mismatch"
            )

    totals = {
        "authentic_papers": sum(
            row["authentic_papers"] for row in coverage.values()
        ),
        "synthetic_papers": sum(
            row["synthetic_papers"] for row in coverage.values()
        ),
        "authentic_questions": sum(
            row["authentic_questions"] for row in coverage.values()
        ),
        "synthetic_questions": sum(
            row["synthetic_questions"] for row in coverage.values()
        ),
        "marks_warnings": sum(
            row["marks_warnings"] for row in coverage.values()
        ),
        "modules_with_authentic_papers": sum(
            row["authentic_papers"] > 0
            for row in coverage.values()
        ),
    }

    return {
        "schema_version": "1.0",
        "modules": list(coverage.values()),
        "totals": totals,
        "warnings": warnings,
    }


def generate_coverage_report(
    processed_dir=PROCESSED_DIR,
    registry=None,
):
    processed_dir = Path(processed_dir)

    papers = load_json_list(
        processed_dir / "papers.json"
    )

    questions = load_json_list(
        processed_dir / "questions.json"
    )

    return build_coverage_report(
        papers,
        questions,
        registry=registry,
    )
