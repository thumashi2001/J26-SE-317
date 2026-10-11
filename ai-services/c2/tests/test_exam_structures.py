
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "config" / "exam_structures.json"

VALID_STATUSES = {
    "unverified",
    "partially_verified",
    "verified",
}


def test_exam_structure_configuration():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    assert config["schema_version"] == "1.0"

    structures = config["structures"]

    assert isinstance(structures, list)
    assert len(structures) == 8

    module_keys = [
        item["module_key"] for item in structures
    ]

    assert len(module_keys) == len(set(module_keys))

    for item in structures:
        assert isinstance(item["module_key"], str)
        assert item["module_key"].strip()

        status = item["verification_status"]
        assert status in VALID_STATUSES

        structure = item["structure"]

        if status == "unverified":
            assert structure is None
            assert item["source_reference"] is None
            continue

        assert item["source_reference"]
        assert isinstance(structure, dict)

        required_fields = [
            "examination_type",
            "duration_minutes",
            "total_marks",
            "question_count",
            "questions_to_answer",
            "marks_per_question",
            "question_types",
            "topic_distribution",
        ]

        for field in required_fields:
            assert field in structure

        assert structure["duration_minutes"] > 0
        assert structure["total_marks"] > 0
        assert structure["question_count"] > 0

        assert (
            0 < structure["questions_to_answer"]
            <= structure["question_count"]
        )

        assert structure["marks_per_question"] > 0

        assert isinstance(
            structure["question_types"], list
        )

    print("PASS: examination structure schema")
    print("PASS: eight module configurations")
    print("PASS: unique module identifiers")
    print("PASS: verification status validation")
    print("PASS: verified data structure validation")

    print("\nAll examination structure tests passed.")


if __name__ == "__main__":
    test_exam_structure_configuration()
