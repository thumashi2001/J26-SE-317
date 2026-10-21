import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.syllabus_topic_collection_validator import (
    SyllabusTopicCollectionValidator,
)


def run_tests():
    print("\n--- M7.2.3 COLLECTION VALIDATOR TEST ---")

    validator = SyllabusTopicCollectionValidator()

    valid_collection = {
        "module_key": "database_systems",
        "source_reference": "TEST_FIXTURE_ONLY",
        "verification_status": "unverified",
        "topics": [
            {
                "topic_id": "TEST_DB_01",
                "topic_name": "Sample Topic",
                "subtopics": ["Sample Subtopic"],
            }
        ],
    }

    assert validator.validate(valid_collection)["valid"]
    print("PASS: valid unverified collection")

    cases = [
        ("unknown module", {"module_key": "unknown"}),
        ("missing source", {"source_reference": ""}),
        ("unsupported verification", {
            "verification_status": "verified"
        }),
        ("duplicate topic ID", {
            "topics": [
                valid_collection["topics"][0],
                deepcopy(valid_collection["topics"][0]),
            ]
        }),
        ("duplicate subtopic", {
            "topics": [{
                "topic_id": "TEST_DB_01",
                "topic_name": "Sample Topic",
                "subtopics": ["Normalization", " normalization "],
            }]
        }),
        ("invalid topic name", {
            "topics": [{
                "topic_id": "TEST_DB_01",
                "topic_name": "",
                "subtopics": [],
            }]
        }),
        ("invalid subtopics", {
            "topics": [{
                "topic_id": "TEST_DB_01",
                "topic_name": "Sample Topic",
                "subtopics": "invalid",
            }]
        }),
    ]

    for name, changes in cases:
        collection = deepcopy(valid_collection)
        collection.update(changes)

        result = validator.validate(collection)

        assert not result["valid"], name
        print(f"PASS: {name} rejected")

    print("\nAll M7.2.3 validator tests passed.")


if __name__ == "__main__":
    run_tests()