
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.dataset_coverage import (
    generate_coverage_report,
    build_coverage_report,
)


def test_authentic_dataset_coverage():
    report = generate_coverage_report()

    modules = report["modules"]
    totals = report["totals"]

    assert len(modules) == 8

    database = next(
        module for module in modules
        if module["module_key"] == "database_systems"
    )

    assert database["authentic_papers"] == 1
    assert database["authentic_questions"] == 25
    assert database["synthetic_papers"] == 0
    assert database["synthetic_questions"] == 0

    assert totals["authentic_papers"] == 1
    assert totals["authentic_questions"] == 25
    assert totals["modules_with_authentic_papers"] == 1

    print("PASS: authentic dataset coverage")
    print("PASS: eight-module coverage reporting")
    print("PASS: paper and question counting")


def test_synthetic_source_separation():
    papers = [
        {
            "metadata": {
                "module_code": "IT3020"
            },
            "source": {
                "filename": "generated_001.pdf",
                "source_type": "synthetic"
            }
        }
    ]

    questions = [
        {
            "question_id": "SYN-Q1",
            "module_code": "IT3020",
            "source_type": "synthetic",
            "source_filename": "generated_001.pdf",
            "marks_status": "extracted",
        }
    ]

    report = build_coverage_report(papers, questions)
    totals = report["totals"]

    assert totals["synthetic_papers"] == 1
    assert totals["synthetic_questions"] == 1
    assert totals["authentic_papers"] == 0
    assert totals["authentic_questions"] == 0

    print("PASS: authentic/synthetic source separation")


def test_duplicate_question_detection():
    question = {
        "question_id": "TEST-Q1",
        "module_code": "IT3020",
        "source_type": "authentic",
        "marks_status": "extracted",
    }

    report = build_coverage_report(
        papers=[],
        questions=[question, question.copy()],
    )

    assert report["totals"]["authentic_questions"] == 1

    assert any(
        "Duplicate question_id" in warning
        for warning in report["warnings"]
    )

    print("PASS: duplicate question detection")


def test_unknown_module_detection():
    papers = [
        {
            "metadata": {
                "module_code": "UNKNOWN"
            },
            "source": {
                "filename": "unknown.pdf",
                "source_type": "authentic"
            }
        }
    ]

    report = build_coverage_report(papers, [])

    assert report["totals"]["authentic_papers"] == 0
    assert len(report["warnings"]) == 1

    print("PASS: unknown module detection")


if __name__ == "__main__":
    test_authentic_dataset_coverage()
    test_synthetic_source_separation()
    test_duplicate_question_detection()
    test_unknown_module_detection()

    print("\nAll dataset coverage tests passed.")
