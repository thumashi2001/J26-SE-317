import json
from copy import deepcopy
from pathlib import Path

from services.topic_taxonomy import TopicTaxonomy
from services.syllabus_topic_collection_validator import (
    SyllabusTopicCollectionValidator,
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_COLLECTION_PATH = (
    ROOT / "config" / "syllabus_topic_collections.json"
)


class SyllabusTopicPopulator:
    """Safely populate module taxonomies from collected topics."""

    def __init__(self, collection_path=None, taxonomy=None):
        self.collection_path = Path(
            collection_path or DEFAULT_COLLECTION_PATH
        )

        self.taxonomy = (
            taxonomy if taxonomy is not None
            else TopicTaxonomy()
        )
        self.validator = SyllabusTopicCollectionValidator(
            taxonomy=self.taxonomy
        )

    def load_collections(self):
        with self.collection_path.open(
            "r", encoding="utf-8"
        ) as file:
            data = json.load(file)

        if data.get("schema_version") != "1.0":
            raise ValueError("Unsupported collection schema version")

        collections = data.get("collections")

        if not isinstance(collections, list):
            raise ValueError("Collections must be a list")

        return collections

    def populate(self, overwrite=False):
        collections = self.load_collections()

        updated_taxonomies = deepcopy(
            self.taxonomy.get_all()
        )

        taxonomy_map = {
            item["module_key"]: item
            for item in updated_taxonomies
        }

        summary = {
            "total_collections": len(collections),
            "populated": 0,
            "skipped": 0,
        }

        seen_modules = set()

        for collection in collections:
            validation = self.validator.validate(collection)

            if not validation["valid"]:
                raise ValueError(
                    "Invalid syllabus collection: "
                    + "; ".join(validation["errors"])
                )
            if not isinstance(collection, dict):
                raise ValueError("Invalid collection")

            module_key = collection.get("module_key")

            if (
                not isinstance(module_key, str)
                or not module_key.strip()
                or module_key not in taxonomy_map
            ):
                raise ValueError(
                    f"Unknown module: {module_key}"
                )

            if module_key in seen_modules:
                raise ValueError(
                    f"Duplicate module collection: {module_key}"
                )

            seen_modules.add(module_key)

            topics = collection.get("topics")
            status = collection.get("verification_status")

            if not isinstance(topics, list):
                raise ValueError("Topics must be a list")

            if status not in {
                "unverified",
                "partially_verified",
                "verified",
            }:
                raise ValueError("Invalid verification status")

            topic_ids = set()

            for topic in topics:
                if not isinstance(topic, dict):
                    raise ValueError("Invalid topic")

                topic_id = topic.get("topic_id")
                topic_name = topic.get("topic_name")
                subtopics = topic.get("subtopics")

                if (
                    not isinstance(topic_id, str)
                    or not topic_id.strip()
                ):
                    raise ValueError("Invalid topic ID")

                if topic_id in topic_ids:
                    raise ValueError(
                        f"Duplicate topic ID: {topic_id}"
                    )

                topic_ids.add(topic_id)

                if (
                    not isinstance(topic_name, str)
                    or not topic_name.strip()
                ):
                    raise ValueError("Invalid topic name")

                if not isinstance(subtopics, list):
                    raise ValueError("Invalid subtopics")

                if any(
                    not isinstance(item, str)
                    or not item.strip()
                    for item in subtopics
                ):
                    raise ValueError("Invalid subtopic")

            target = taxonomy_map[module_key]

            if target["topics"] and not overwrite:
                summary["skipped"] += 1
                continue

            target["topics"] = deepcopy(topics)

            # Verification status must come from reviewed
            # source evidence, not automatic classification.
            target["verification_status"] = status

            summary["populated"] += 1

            

        return {
            "schema_version": "1.0",
            "taxonomies": updated_taxonomies,
            "summary": summary,
        }