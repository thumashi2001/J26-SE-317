import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from services.question_classification_pipeline import (
    QuestionClassificationPipeline,
)


def run_tests():
    print("\n--- M6.5.1 INTEGRATION TEST ---")

    pipeline = QuestionClassificationPipeline()
    result = pipeline.run()

    assert isinstance(result, dict)
    assert "summary" in result

    summary = result["summary"]

    required_fields = {
        "total_questions",
        "classified",
        "unclassified",
        "invalid",
    }

    assert required_fields.issubset(summary.keys())
    print("PASS: classification pipeline execution")

    for field in required_fields:
        assert type(summary[field]) is int
        assert summary[field] >= 0

    print("PASS: summary field validation")

    assert (
        summary["classified"]
        + summary["unclassified"]
        + summary["invalid"]
        == summary["total_questions"]
    )

    print("PASS: classification count consistency")

    assert summary["total_questions"] > 0
    print("PASS: non-empty question repository")

    assert summary["invalid"] == 0
    print("PASS: no invalid classification records")

    print("\n--- CLASSIFICATION SUMMARY ---")
    print("Total questions:", summary["total_questions"])
    print("Classified:", summary["classified"])
    print("Unclassified:", summary["unclassified"])
    print("Invalid:", summary["invalid"])

    if summary["unclassified"] > 0:
        print(
            "WARNING: Some questions remain unclassified. "
            "Check verified syllabus taxonomy coverage."
        )

    print("\nAll M6.5.1 integration tests passed.")


if __name__ == "__main__":
    run_tests()