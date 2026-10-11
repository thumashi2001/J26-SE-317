
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.topic_coverage_validator import (
    TopicCoverageValidator,
)


validator = TopicCoverageValidator()

print("\n--- TOPIC COVERAGE VALIDATION ---")

summary = validator.validate_all()

assert summary["total_modules"] == 8
print("PASS: eight modules evaluated")

assert summary["valid_modules"] == 8
print("PASS: all taxonomy configurations valid")

assert 0 <= summary["ready_modules"] <= 8
print("PASS: module readiness reporting")

assert 0 <= summary["modules_with_topics"] <= 8
print("PASS: configured topic coverage reporting")

assert summary["total_configured_topics"] >= 0
print("PASS: topic counting")

unknown = validator.validate_module("unknown_module")

assert unknown["valid"] is False
assert unknown["ready"] is False
assert "Unknown module" in unknown["errors"]

print("PASS: unknown module rejection")

for result in summary["results"]:
    assert result["topic_count"] >= 0
    assert result["subtopic_count"] >= 0

    if result["verification_status"] == "unverified":
        assert result["ready"] is False

print("PASS: unverified module readiness handling")

print("\n--- COVERAGE SUMMARY ---")
print("Total modules:", summary["total_modules"])
print("Valid modules:", summary["valid_modules"])
print("Ready modules:", summary["ready_modules"])
print("Modules with topics:", summary["modules_with_topics"])
print(
    "Total configured topics:",
    summary["total_configured_topics"],
)

print("\n--- MODULE DETAILS ---")

for result in summary["results"]:
    print(
        f"{result['module_key']}: "
        f"{result['topic_count']} topics, "
        f"{result['subtopic_count']} subtopics, "
        f"ready={result['ready']}"
    )

print("\nAll topic coverage validator tests passed.")
