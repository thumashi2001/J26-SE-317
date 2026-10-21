
import copy
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_review_report import (
    SyllabusTopicReviewReport,
)


def make_candidate(name, rank=1, module_key="database_systems"):
    return {
        "module_key": module_key,
        "candidate_name": name,
        "rank": rank,
        "ranking_score": 85,
        "occurrence_count": 2,
        "document_count": 1,
        "sources": [
            {"filename": "lecture1.pdf", "line_number": 10},
            {"filename": "lecture1.pdf", "line_number": 20},
        ],
        "verification_status": "unverified",
    }


def run_tests():
    print("\n--- M7.3.5.2.4.2 REVIEW REPORT UNIT TESTS ---")

    generator = SyllabusTopicReviewReport()

    module_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate("Database Normalization"),
            make_candidate("SQL Joins", rank=2),
        ],
        "excluded_candidates": [
            {
                "module_key": "database_systems",
                "candidate_name": "Subject Name",
                "verification_status": "unverified",
                "sources": [
                    {"filename": "lecture1.pdf", "line_number": 1}
                ],
            }
        ],
    }

    original = copy.deepcopy(module_data)

    # TEST 1: Module report generation.
    report = generator.build_module_report(module_data)

    assert report["module_key"] == "database_systems"
    assert len(report["review_candidates"]) == 2
    assert report["summary"]["pending_review_count"] == 2

    print("PASS: module review report generated")

    # TEST 2: Review safeguards.
    for candidate in report["review_candidates"]:
        assert candidate["verification_status"] == "unverified"
        assert candidate["review_decision"] == "pending"
        assert candidate["review_notes"] == ""

    print("PASS: review safeguards preserved")

    # TEST 3: Source evidence preserved.
    assert (
        report["review_candidates"][0]["sources"]
        == module_data["candidates"][0]["sources"]
    )

    print("PASS: source evidence preserved")

    # TEST 4: Excluded candidates retained.
    assert len(report["excluded_candidates"]) == 1
    assert (
        report["excluded_candidates"][0]["candidate_name"]
        == "Subject Name"
    )

    print("PASS: excluded candidates retained for audit")

    # TEST 5: Input data unchanged.
    assert module_data == original

    print("PASS: original data unchanged")

    # TEST 6: Multiple module reports.
    all_data = {
        "modules": {
            "database_systems": module_data,
            "software_architecture": {
                "module_key": "software_architecture",
                "candidates": [
                    make_candidate(
                        "Microservices Architecture",
                        module_key="software_architecture",
                    )
                ],
                "excluded_candidates": [],
            },
        }
    }

    all_reports = generator.build_all_reports(all_data)

    assert all_reports["summary"]["module_count"] == 2
    assert all_reports["summary"]["total_review_candidates"] == 3
    assert all_reports["summary"]["total_excluded_candidates"] == 1

    print("PASS: multi-module review reports")

    # TEST 7: JSON export.
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "review_report.json"

        generator.export_json(all_reports, output_path)

        assert output_path.exists()

        with output_path.open("r", encoding="utf-8") as file:
            exported = json.load(file)

        assert exported == all_reports

    print("PASS: JSON report export")

    print(
        "\nAll M7.3.5.2.4.2 review report unit tests passed."
    )


if __name__ == "__main__":
    run_tests()
