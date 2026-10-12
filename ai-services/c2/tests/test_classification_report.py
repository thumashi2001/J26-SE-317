
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from services.classification_report import ClassificationReport


def make_result(question_id, module_key, method, topic_id=None):
    return {
        "question_id": question_id,
        "valid": True,
        "classification": {
            "question_id": question_id,
            "module_key": module_key,
            "topic_id": topic_id,
            "classification_method": method,
        },
        "errors": [],
        "warnings": [],
    }


def run_tests():
    print("\n--- M6.5.2 CLASSIFICATION REPORT TEST ---")

    reporter = ClassificationReport()

    batch_result = {
        "results": [
            make_result(
                "Q1",
                "database_systems",
                "rule_based",
                "DB_TOPIC_01",
            ),
            make_result(
                "Q2",
                "database_systems",
                "unclassified",
            ),
            make_result(
                "Q3",
                "distributed_systems",
                "unclassified",
            ),
            {
                "question_id": "Q4",
                "valid": False,
                "classification": None,
                "errors": ["Invalid question"],
                "warnings": [],
            },
        ]
    }

    questions = [
        {"question_id": "Q1", "module_key": "database_systems"},
        {"question_id": "Q2", "module_key": "database_systems"},
        {"question_id": "Q3", "module_key": "distributed_systems"},
        {"question_id": "Q4", "module_key": "distributed_systems"},
    ]

    report = reporter.generate(batch_result, questions)
    summary = report["summary"]

    assert summary["total_questions"] == 4
    print("PASS: total question count")

    assert summary["classified"] == 1
    print("PASS: classified question count")

    assert summary["unclassified"] == 2
    print("PASS: unclassified question count")

    assert summary["invalid"] == 1
    print("PASS: invalid question count")

    assert summary["classification_coverage_percentage"] == 25.0
    print("PASS: classification coverage percentage")

    assert summary["unclassified_percentage"] == 50.0
    print("PASS: unclassified percentage")

    assert summary["invalid_percentage"] == 25.0
    print("PASS: invalid percentage")

    db = report["modules"]["database_systems"]

    assert db["total_questions"] == 2
    assert db["classified"] == 1
    assert db["classification_coverage_percentage"] == 50.0
    print("PASS: Database Systems module coverage")

    ds = report["modules"]["distributed_systems"]

    assert ds["total_questions"] == 2
    assert ds["unclassified"] == 1
    assert ds["invalid"] == 1
    print("PASS: Distributed Systems module coverage")

    assert len(report["warnings"]) == 2
    print("PASS: reporting warnings")

    empty_report = reporter.generate({"results": []})

    assert empty_report["summary"]["total_questions"] == 0
    assert empty_report["summary"]["classification_coverage_percentage"] == 0
    print("PASS: empty batch handling")

    try:
        reporter.generate({"results": []}, questions)
        raise AssertionError("Expected count mismatch rejection")
    except ValueError:
        print("PASS: mismatched input rejection")

    print("\nAll M6.5.2 classification report tests passed.")


if __name__ == "__main__":
    run_tests()
