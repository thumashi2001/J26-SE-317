from services.topic_taxonomy import TopicTaxonomy


class SyllabusTopicCollectionValidator:
    """Validate collected syllabus topics before population."""

    STATUSES = {
        "unverified",
        "partially_verified",
        "verified",
    }

    def __init__(self, taxonomy=None):
        self.taxonomy = (
            taxonomy if taxonomy is not None
            else TopicTaxonomy()
        )

    def validate(self, collection):
        errors = []

        if not isinstance(collection, dict):
            return {
                "valid": False,
                "errors": ["Collection must be an object"],
            }

        module_key = collection.get("module_key")
        status = collection.get("verification_status")
        source = collection.get("source_reference")
        topics = collection.get("topics")

        if (
            not isinstance(module_key, str)
            or not module_key.strip()
            or self.taxonomy.get_module_taxonomy(module_key) is None
        ):
            errors.append("Unknown or invalid module_key")

        if status not in self.STATUSES:
            errors.append("Invalid verification status")

        if not isinstance(source, str) or not source.strip():
            errors.append("Missing source reference")

        if not isinstance(topics, list):
            errors.append("Topics must be a list")
            topics = []

        if status == "verified":
            errors.append(
                "Verified status requires independent source review"
            )

        topic_ids = set()

        for index, topic in enumerate(topics):
            if not isinstance(topic, dict):
                errors.append(f"Invalid topic at index {index}")
                continue

            topic_id = topic.get("topic_id")
            topic_name = topic.get("topic_name")
            subtopics = topic.get("subtopics")

            if not isinstance(topic_id, str) or not topic_id.strip():
                errors.append("Invalid topic ID")
            elif topic_id in topic_ids:
                errors.append(f"Duplicate topic ID: {topic_id}")
            else:
                topic_ids.add(topic_id)

            if (
                not isinstance(topic_name, str)
                or not topic_name.strip()
            ):
                errors.append("Invalid topic name")

            if not isinstance(subtopics, list):
                errors.append("Subtopics must be a list")
                continue

            seen_subtopics = set()

            for subtopic in subtopics:
                if (
                    not isinstance(subtopic, str)
                    or not subtopic.strip()
                ):
                    errors.append("Invalid subtopic")
                    continue

                normalized = subtopic.strip().casefold()

                if normalized in seen_subtopics:
                    errors.append(
                        f"Duplicate subtopic: {subtopic}"
                    )

                seen_subtopics.add(normalized)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }