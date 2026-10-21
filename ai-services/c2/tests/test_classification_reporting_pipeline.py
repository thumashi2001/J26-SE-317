
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from services.classification_reporting_pipeline import (
    ClassificationReportingPipeline,
)
from services.classification_report_exporter import (
    ClassificationReportExporter,
)


def run_tests():
    print("\n--- M6.5.4 FINAL INTEGRATION TEST ---")

    pipeline = ClassificationReportingPipeline()
    exporter = ClassificationReportExporter()

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = (
            Path(temp_dir)
            / "reports"
            / "classification_report.json"
        )

        result = pipeline.run(output_path=output_path)

        assert isinstance(result, dict)
        print("PASS: reporting pipeline execution")

        assert "summary" in result
        assert "report" in result
        assert "report_path" in result
        print("PASS: reporting pipeline output structure")

        summary = result["summary"]
        report = result["report"]

        assert summary["total_questions"] > 0
        print("PASS: question repository processed")

        assert (
            summary["classified"]
            + summary["unclassified"]
            + summary["invalid"]
            == summary["total_questions"]
        )
        print("PASS: classification summary consistency")

        assert exporter.validate_report(report)
        print("PASS: classification report validation")

        saved_path = Path(result["report_path"])

        assert saved_path.exists()
        print("PASS: JSON report generated")

        with saved_path.open(
            "r", encoding="utf-8"
        ) as file:
            saved_report = json.load(file)

        assert saved_report == report
        print("PASS: exported report data preserved")

        assert (
            saved_report["summary"]["total_questions"]
            == summary["total_questions"]
        )
        print("PASS: exported summary consistency")

        assert isinstance(report["modules"], dict)
        print("PASS: module coverage report generated")

        assert isinstance(report["warnings"], list)
        print("PASS: classification warnings preserved")

        print("\n--- FINAL CLASSIFICATION SUMMARY ---")
        print("Total questions:", summary["total_questions"])
        print("Classified:", summary["classified"])
        print("Unclassified:", summary["unclassified"])
        print("Invalid:", summary["invalid"])
        print(
            "Classification coverage:",
            summary["classification_coverage_percentage"],
            "%",
        )

        print("\nAll M6.5.4 integration tests passed.")


if __name__ == "__main__":
    run_tests()
