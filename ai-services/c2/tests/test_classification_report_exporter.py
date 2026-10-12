
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from services.classification_report import ClassificationReport
from services.classification_report_exporter import (
    ClassificationReportExporter,
)


def expect_error(action):
    try:
        action()
    except ValueError:
        return

    raise AssertionError("Expected ValueError")


def run_tests():
    print("\n--- M6.5.3 JSON REPORT EXPORT TEST ---")

    reporter = ClassificationReport()
    exporter = ClassificationReportExporter()

    batch_result = {
        "results": [
            {
                "question_id": "Q1",
                "valid": True,
                "classification": {
                    "module_key": "database_systems",
                    "topic_id": "DB_TOPIC_01",
                    "classification_method": "rule_based",
                },
            },
            {
                "question_id": "Q2",
                "valid": True,
                "classification": {
                    "module_key": "database_systems",
                    "topic_id": None,
                    "classification_method": "unclassified",
                },
            },
            {
                "question_id": "Q3",
                "valid": False,
                "classification": None,
                "errors": ["Invalid classification"],
            },
        ]
    }

    questions = [
        {"question_id": "Q1", "module_key": "database_systems"},
        {"question_id": "Q2", "module_key": "database_systems"},
        {"question_id": "Q3", "module_key": "distributed_systems"},
    ]

    report = reporter.generate(batch_result, questions)

    assert exporter.validate_report(report) is True
    print("PASS: valid report validation")

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = (
            Path(temp_dir)
            / "reports"
            / "classification_report.json"
        )

        saved_path = exporter.export(report, output_path)

        assert Path(saved_path).exists()
        print("PASS: JSON file created")

        with open(saved_path, "r", encoding="utf-8") as file:
            loaded = json.load(file)

        assert loaded == report
        print("PASS: report data preserved")

        assert loaded["summary"]["total_questions"] == 3
        assert loaded["summary"]["classified"] == 1
        assert loaded["summary"]["unclassified"] == 1
        assert loaded["summary"]["invalid"] == 1
        print("PASS: summary values preserved")

        assert len(loaded["modules"]) == 2
        print("PASS: module statistics preserved")

        invalid_report = {
            **report,
            "summary": {
                **report["summary"],
                "total_questions": 99,
            },
        }

        expect_error(
            lambda: exporter.export(invalid_report, output_path)
        )
        print("PASS: inconsistent summary rejected")

        invalid_modules = {
            **report,
            "modules": {},
        }

        expect_error(
            lambda: exporter.export(invalid_modules, output_path)
        )
        print("PASS: inconsistent module totals rejected")

        expect_error(
            lambda: exporter.export(report, Path(temp_dir) / "report.txt")
        )
        print("PASS: invalid file extension rejected")

        expect_error(
            lambda: exporter.export(
                {"schema_version": "2.0"},
                output_path,
            )
        )
        print("PASS: invalid schema rejected")

        assert json.loads(output_path.read_text(
            encoding="utf-8"
        )) == report
        print("PASS: invalid exports preserve existing report")

    print("\nAll M6.5.3 JSON report exporter tests passed.")


if __name__ == "__main__":
    run_tests()
