
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.paper_parser import parse_paper
from services.question_repository import (
    build_question_repository,
)
from services.dataset_validator import (
    validate_question_repository,
)


BASE_DIR = Path(__file__).resolve().parents[1]
PDF_PATH = (
    BASE_DIR / "datasets" / "authentic" / "sample.pdf"
)


def test_authentic_repository_validation():
    paper = parse_paper(PDF_PATH)
    repository = build_question_repository(paper)

    result = validate_question_repository(repository)

    print("\n--- DATASET VALIDATION ---")
    print("Records:", result["record_count"])
    print("Errors:", result["error_count"])
    print("Warnings:", result["warning_count"])

    for warning in result["warnings"]:
        print("WARNING:", warning)

    assert result["record_count"] == 25
    assert result["error_count"] == 0
    assert result["warning_count"] > 0
    assert result["is_valid"] is True

    print("\nPASS: authentic repository validation")


def test_duplicate_detection():
    record = {
        "question_id": "TEST-Q1(a)",
        "paper_id": "TEST",
        "module_code": "IT3020",
        "question_number": 1,
        "part_id": "Q1(a)",
        "parent_id": "Q1",
        "question_text": "Explain database indexing.",
        "marks": 5,
        "marks_status": "extracted",
    }

    repository = {
        "questions": [record.copy(), record.copy()]
    }

    result = validate_question_repository(repository)

    assert result["is_valid"] is False
    assert result["error_count"] > 0

    print("PASS: duplicate question ID detection")


def test_missing_parent_detection():
    repository = {
        "questions": [
            {
                "question_id": "TEST-Q1(a)(i)",
                "paper_id": "TEST",
                "module_code": "IT3020",
                "question_number": 1,
                "part_id": "Q1(a)(i)",
                "parent_id": "Q1(a)",
                "question_text": "Explain indexing.",
                "marks": 2,
                "marks_status": "extracted",
            }
        ]
    }

    result = validate_question_repository(repository)

    assert result["is_valid"] is False

    assert any(
        "missing parent" in error
        for error in result["errors"]
    )

    print("PASS: missing parent detection")


if __name__ == "__main__":
    test_authentic_repository_validation()
    test_duplicate_detection()
    test_missing_parent_detection()

    print("\nAll dataset validation tests passed.")
