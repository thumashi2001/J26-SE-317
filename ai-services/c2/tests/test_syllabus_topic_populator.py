import json
import sys
import tempfile
from pathlib import Path

# Add the C2 root directory to Python's import path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.syllabus_topic_populator import (
    SyllabusTopicPopulator,
)


def run_tests():
    print("\n--- M7.2.2 SYLLABUS TOPIC POPULATOR TEST ---")

    populator = SyllabusTopicPopulator()
    result = populator.populate()

    assert result["schema_version"] == "1.0"
    print("PASS: schema version")

    assert len(result["taxonomies"]) == 8
    print("PASS: eight module taxonomies preserved")

    assert result["summary"]["total_collections"] == 0
    assert result["summary"]["populated"] == 0
    print("PASS: empty collection handling")

    original = populator.taxonomy.get_all()

    assert all(
        len(module["topics"]) == 0
        for module in original
    )
    print("PASS: original taxonomy unchanged")

    sample_collection = {
        "schema_version": "1.0",
        "collections": [
            {
                "module_key": "database_systems",
                "source_reference": "TEST_FIXTURE_ONLY",
                "verification_status": "unverified",
                "topics": [
                    {
                        "topic_id": "TEST_DB_01",
                        "topic_name": "Sample Test Topic",
                        "subtopics": [
                            "Sample Test Subtopic"
                        ]
                    }
                ]
            }
        ]
    }

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "collections.json"

        path.write_text(
            json.dumps(sample_collection),
            encoding="utf-8"
        )

        test_populator = SyllabusTopicPopulator(
            collection_path=path
        )

        populated = test_populator.populate()

        database = next(
            item
            for item in populated["taxonomies"]
            if item["module_key"] == "database_systems"
        )

        assert len(database["topics"]) == 1
        assert database["verification_status"] == "unverified"
        print("PASS: sample topic population")
        print("PASS: verification status preserved")

        assert test_populator.taxonomy.get_topic(
            "database_systems", "TEST_DB_01"
        ) is None
        print("PASS: source taxonomy not modified")

    print("\nAll M7.2.2 tests passed.")


if __name__ == "__main__":
    run_tests()