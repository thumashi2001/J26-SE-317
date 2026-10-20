
import json
from pathlib import Path


DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "topic_taxonomies.json"
)


class TopicTaxonomy:
    def __init__(self, config_path=None):
        self.config_path = Path(config_path or DEFAULT_CONFIG)

        with self.config_path.open(
            "r", encoding="utf-8"
        ) as file:
            data = json.load(file)

        self.schema_version = data["schema_version"]
        self.taxonomies = data["taxonomies"]

        self._validate()

    def _validate(self):
        if self.schema_version != "1.0":
            raise ValueError("Unsupported taxonomy schema version")

        if not isinstance(self.taxonomies, list):
            raise ValueError("Taxonomies must be a list")

        keys = set()

        for taxonomy in self.taxonomies:
            key = taxonomy["module_key"]

            if not isinstance(key, str) or not key.strip():
                raise ValueError("Invalid module key")

            if key in keys:
                raise ValueError(f"Duplicate module: {key}")

            keys.add(key)

            if taxonomy["verification_status"] not in {
                "unverified",
                "partially_verified",
                "verified",
            }:
                raise ValueError(
                    f"Invalid verification status for {key}"
                )

            topics = taxonomy["topics"]

            if not isinstance(topics, list):
                raise ValueError(
                    f"Topics must be a list for {key}"
                )

            topic_ids = set()

            for topic in topics:
                topic_id = topic["topic_id"]

                if not isinstance(topic_id, str) or not topic_id.strip():
                    raise ValueError("Invalid topic ID")

                if topic_id in topic_ids:
                    raise ValueError(
                        f"Duplicate topic ID: {topic_id}"
                    )

                topic_ids.add(topic_id)

                if not isinstance(topic["topic_name"], str):
                    raise ValueError("Invalid topic name")

                if not topic["topic_name"].strip():
                    raise ValueError("Empty topic name")

                if not isinstance(topic["subtopics"], list):
                    raise ValueError("Subtopics must be a list")

                for subtopic in topic["subtopics"]:
                    if not isinstance(subtopic, str):
                        raise ValueError("Invalid subtopic")

                    if not subtopic.strip():
                        raise ValueError("Empty subtopic")

    def get_all(self):
        return self.taxonomies

    def get_module_taxonomy(self, module_key):
        alias_map = {
            "case_studies_in_software_engineering": "case_studies_software_engineering",
            "case_studies_software_engineering": "case_studies_in_software_engineering",
            "software_engineering_process_and_quality_management": "software_engineering_process_quality_management",
            "software_engineering_process_quality_management": "software_engineering_process_and_quality_management",
        }
        target_keys = {module_key}
        if module_key in alias_map:
            target_keys.add(alias_map[module_key])

        base_tax = None
        for taxonomy in self.taxonomies:
            if taxonomy["module_key"] in target_keys:
                base_tax = taxonomy
                break

        if base_tax is None:
            return None

        # Check if an explicit lecturer approval exists in the approval repository
        try:
            from services.taxonomy_approval_repository import TaxonomyApprovalRepository
            repo = TaxonomyApprovalRepository()
            appr = repo.get_approval(base_tax["module_key"])
            if appr and appr.get("status") == "approved":
                import copy
                approved_tax = copy.deepcopy(base_tax)
                approved_tax["verification_status"] = "verified"
                approved_topics = appr.get("topics")
                if approved_topics and isinstance(approved_topics, list):
                    approved_tax["topics"] = approved_topics
                return approved_tax
        except Exception:
            pass

        return base_tax

    def get_topics(self, module_key):
        taxonomy = self.get_module_taxonomy(module_key)

        if taxonomy is None:
            raise ValueError(
                f"Unknown module: {module_key}"
            )

        return taxonomy["topics"]

    def get_topic(self, module_key, topic_id):
        for topic in self.get_topics(module_key):
            if topic["topic_id"] == topic_id:
                return topic

        return None

    def is_module_ready(self, module_key):
        taxonomy = self.get_module_taxonomy(module_key)

        if taxonomy is None:
            return False

        return (
            taxonomy["verification_status"] == "verified"
            and len(taxonomy["topics"]) > 0
        )

