
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.topic_taxonomy import TopicTaxonomy


def test_taxonomy():
    taxonomy = TopicTaxonomy()

    assert taxonomy.schema_version == "1.0"
    assert len(taxonomy.get_all()) == 8

    keys = [item["module_key"] for item in taxonomy.get_all()]
    assert len(keys) == len(set(keys))

    print("PASS: eight module taxonomies")
    print("PASS: unique module identifiers")

    database = taxonomy.get_module_taxonomy(
        "database_systems"
    )

    assert database is not None
    assert database["verification_status"] == "unverified"
    assert taxonomy.get_topics("database_systems") == []
    assert not taxonomy.is_module_ready("database_systems")

    print("PASS: module taxonomy lookup")
    print("PASS: unverified module readiness")

    assert taxonomy.get_module_taxonomy(
        "unknown_module"
    ) is None

    try:
        taxonomy.get_topics("unknown_module")
        raise AssertionError("Unknown module was accepted")
    except ValueError:
        pass

    print("PASS: unknown module rejection")

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "taxonomies.json"

        data = {
            "schema_version": "1.0",
            "taxonomies": [
                {
                    "module_key": "test_module",
                    "verification_status": "verified",
                    "source_reference": "verified_test_source",
                    "topics": [
                        {
                            "topic_id": "T01",
                            "topic_name": "Test Topic",
                            "subtopics": [
                                "Test Subtopic"
                            ]
                        }
                    ]
                }
            ]
        }

        path.write_text(
            json.dumps(data), encoding="utf-8"
        )

        test_service = TopicTaxonomy(path)

        assert test_service.is_module_ready("test_module")
        assert test_service.get_topic(
            "test_module", "T01"
        )["topic_name"] == "Test Topic"

        print("PASS: verified topic retrieval")

        data["taxonomies"][0]["topics"].append(
            {
                "topic_id": "T01",
                "topic_name": "Duplicate",
                "subtopics": []
            }
        )

        path.write_text(
            json.dumps(data), encoding="utf-8"
        )

        try:
            TopicTaxonomy(path)
            raise AssertionError("Duplicate topic was accepted")
        except ValueError:
            pass

        print("PASS: duplicate topic detection")


if __name__ == "__main__":
    test_taxonomy()

    print("\nAll topic taxonomy tests passed.")
