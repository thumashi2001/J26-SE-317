
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.topic_taxonomy import TopicTaxonomy
from services.syllabus_topic_populator import (
    SyllabusTopicPopulator,
)


def run_tests():
    print("\n--- M7.2.4 POPULATION INTEGRATION TEST ---")

    # Temporary test data, not an official syllabus.
    sample = {
        "schema_version": "1.0",
        "collections": [
            {
                "module_key": "database_systems",
                "source_reference": "TEST_FIXTURE_ONLY",
                "verification_status": "unverified",
                "topics": [
                    {
                        "topic_id": "TEST_DB_01",
                        "topic_name": "Sample Database Topic",
                        "subtopics": ["Sample Subtopic"],
                    }
                ],
            }
        ],
    }

    with tempfile.TemporaryDirectory() as directory:
        temp_dir = Path(directory)

        collection_path = temp_dir / "collections.json"
        taxonomy_path = temp_dir / "taxonomies.json"
        empty_taxonomy_path = temp_dir / "empty_taxonomies.json"

        # Use the real taxonomy only as a structural template.
        original_taxonomy = TopicTaxonomy()

        original_data = {
            "schema_version": "1.0",
            "taxonomies": original_taxonomy.get_all(),
        }

        # Create an isolated empty taxonomy for testing.
        empty_data = json.loads(json.dumps(original_data))

        for module in empty_data["taxonomies"]:
            module["topics"] = []
            module["verification_status"] = "unverified"

        empty_taxonomy_path.write_text(
            json.dumps(empty_data, indent=2),
            encoding="utf-8",
        )

        collection_path.write_text(
            json.dumps(sample, indent=2),
            encoding="utf-8",
        )

        isolated_taxonomy = TopicTaxonomy(
            config_path=empty_taxonomy_path
        )

        populator = SyllabusTopicPopulator(
            collection_path=collection_path,
            taxonomy=isolated_taxonomy,
        )

        result = populator.populate()

        assert result["summary"]["populated"] == 1
        assert result["summary"]["skipped"] == 0
        print("PASS: topic population execution")

        assert len(result["taxonomies"]) == 8
        print("PASS: eight modules preserved")

        # Save the result to a temporary file and reload it
        # using the existing TopicTaxonomy service.
        taxonomy_path.write_text(
            json.dumps({
                "schema_version": "1.0",
                "taxonomies": result["taxonomies"],
            }),
            encoding="utf-8",
        )

        populated_taxonomy = TopicTaxonomy(
            config_path=taxonomy_path
        )

        topic = populated_taxonomy.get_topic(
            "database_systems",
            "TEST_DB_01",
        )

        assert topic is not None
        assert topic["topic_name"] == "Sample Database Topic"
        print("PASS: populated topic retrieval")

        database = populated_taxonomy.get_module_taxonomy(
            "database_systems"
        )

        assert database["verification_status"] == "unverified"
        assert not populated_taxonomy.is_module_ready(
            "database_systems"
        )
        print("PASS: verification safeguards preserved")

        assert isolated_taxonomy.get_topic(
            "database_systems",
            "TEST_DB_01",
        ) is None

        assert original_taxonomy.get_all() == original_data["taxonomies"]
        print("PASS: original taxonomy unchanged")

        # Existing topics should not be overwritten by default.
        protected_populator = SyllabusTopicPopulator(
            collection_path=collection_path,
            taxonomy=populated_taxonomy,
        )

        protected = protected_populator.populate()

        assert protected["summary"]["skipped"] == 1
        assert protected["summary"]["populated"] == 0
        print("PASS: existing taxonomy overwrite protection")

        # Missing source reference must be rejected.
        sample["collections"][0]["source_reference"] = ""

        collection_path.write_text(
            json.dumps(sample),
            encoding="utf-8",
        )

        try:
            populator.populate()
        except ValueError:
            print("PASS: invalid collection rejected")
        else:
            raise AssertionError(
                "Invalid collection was accepted"
            )

    print("\nAll M7.2.4 integration tests passed.")


if __name__ == "__main__":
    run_tests()
