import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = (
    ROOT / "config" / "syllabus_topic_collections.json"
)


def run_tests():
    print("\n--- M7.2.1 SYLLABUS TOPIC COLLECTION TEST ---")

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["schema_version"] == "1.0"
    print("PASS: schema version")

    assert "collections" in data
    assert isinstance(data["collections"], list)
    print("PASS: collection structure")

    module_keys = set()

    for collection in data["collections"]:
        module_key = collection["module_key"]

        assert isinstance(module_key, str)
        assert module_key.strip()
        assert module_key not in module_keys

        module_keys.add(module_key)

        assert isinstance(collection["topics"], list)

        assert collection["verification_status"] in {
            "unverified",
            "partially_verified",
            "verified",
        }

        topic_ids = set()

        for topic in collection["topics"]:
            assert isinstance(topic["topic_id"], str)
            assert topic["topic_id"].strip()
            assert topic["topic_id"] not in topic_ids
            topic_ids.add(topic["topic_id"])

            assert isinstance(topic["topic_name"], str)
            assert topic["topic_name"].strip()

            assert isinstance(topic["subtopics"], list)

            for subtopic in topic["subtopics"]:
                assert isinstance(subtopic, str)
                assert subtopic.strip()

    print("PASS: collection entry structure")
    print("PASS: unique module and topic identifiers")

    print(f"\nConfigured collections: {len(data['collections'])}")
    print("All M7.2.1 tests passed.")


if __name__ == "__main__":
    run_tests()