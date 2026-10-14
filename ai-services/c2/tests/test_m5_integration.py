
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.exam_structure_validator import (
    load_exam_structures,
    validate_exam_structure,
)
from services.topic_taxonomy import TopicTaxonomy
from services.topic_coverage_validator import TopicCoverageValidator


print("\n--- M5 INTEGRATION TESTING ---")

# -------------------------------------------------
# TEST 1: Load all examination and topic structures
# -------------------------------------------------

exam_data = load_exam_structures()
taxonomy_service = TopicTaxonomy()
coverage_validator = TopicCoverageValidator()

exam_modules = {
    item["module_key"]
    for item in exam_data["structures"]
}

topic_modules = {
    item["module_key"]
    for item in taxonomy_service.get_all()
}

assert len(exam_modules) == 8
assert len(topic_modules) == 8
assert exam_modules == topic_modules

print("PASS: eight-module configuration consistency")


# -------------------------------------------------
# TEST 2: Validate examination structures
# -------------------------------------------------

for module_key in exam_modules:
    result = validate_exam_structure(module_key)

    assert result["valid"] is True

print("PASS: examination structure integration")


# -------------------------------------------------
# TEST 3: Validate topic coverage
# -------------------------------------------------

coverage_summary = coverage_validator.validate_all()

assert coverage_summary["total_modules"] == 8
assert coverage_summary["valid_modules"] == 8

print("PASS: topic coverage integration")


# -------------------------------------------------
# TEST 4: Cross-service readiness
# -------------------------------------------------

for module_key in exam_modules:
    exam_result = validate_exam_structure(module_key)
    topic_result = coverage_validator.validate_module(
        module_key
    )

    combined_ready = (
        exam_result["ready"]
        and topic_result["ready"]
    )

    if exam_result["verification_status"] != "verified":
        assert combined_ready is False

    if topic_result["verification_status"] != "verified":
        assert combined_ready is False

print("PASS: cross-service readiness checks")


# -------------------------------------------------
# TEST 5: Database Systems verification status
# -------------------------------------------------

database_exam = validate_exam_structure(
    "database_systems"
)

database_topics = coverage_validator.validate_module(
    "database_systems"
)

assert database_exam["valid"] is True
assert database_exam["ready"] is False
assert database_exam["verification_status"] == (
    "partially_verified"
)

assert database_topics["ready"] is False

print("PASS: Database Systems verification safeguards")


# -------------------------------------------------
# TEST 6: Populated taxonomy fixture
# -------------------------------------------------

fixture = {
    "schema_version": "1.0",
    "taxonomies": [
        {
            "module_key": "database_systems",
            "verification_status": "verified",
            "topics": [
                {
                    "topic_id": "test_topic_1",
                    "topic_name": "Test Topic One",
                    "subtopics": [
                        "Subtopic A",
                        "Subtopic B",
                    ],
                },
                {
                    "topic_id": "test_topic_2",
                    "topic_name": "Test Topic Two",
                    "subtopics": [
                        "Subtopic C",
                    ],
                },
            ],
        }
    ],
}

with tempfile.TemporaryDirectory() as temp_dir:
    fixture_path = Path(temp_dir) / "taxonomy_fixture.json"

    fixture_path.write_text(
        json.dumps(fixture, indent=2),
        encoding="utf-8",
    )

    fixture_validator = TopicCoverageValidator(
        fixture_path
    )

    fixture_result = fixture_validator.validate_module(
        "database_systems"
    )

    assert fixture_result["valid"] is True
    assert fixture_result["topic_count"] == 2
    assert fixture_result["subtopic_count"] == 3
    assert fixture_result["ready"] is True

print("PASS: populated taxonomy fixture validation")


# -------------------------------------------------
# TEST 7: Unknown module rejection
# -------------------------------------------------

unknown_exam = validate_exam_structure(
    "unknown_module"
)

unknown_topics = coverage_validator.validate_module(
    "unknown_module"
)

assert unknown_exam["valid"] is False
assert unknown_topics["valid"] is False
assert unknown_exam["ready"] is False
assert unknown_topics["ready"] is False

print("PASS: unknown module rejection")


# -------------------------------------------------
# TEST 8: Current dataset baseline
# -------------------------------------------------

print("\n--- CURRENT DATASET STATUS ---")

print("Total modules:", coverage_summary["total_modules"])
print("Valid taxonomies:", coverage_summary["valid_modules"])
print("Ready topic modules:", coverage_summary["ready_modules"])
print(
    "Modules with topics:",
    coverage_summary["modules_with_topics"],
)
print(
    "Configured topics:",
    coverage_summary["total_configured_topics"],
)

if coverage_summary["total_configured_topics"] == 0:
    print(
        "WARNING: No verified syllabus topics have "
        "been configured yet."
    )

print("\nAll M5 integration tests passed.")
