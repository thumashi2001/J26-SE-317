
from services.topic_taxonomy import TopicTaxonomy


class TopicCoverageValidator:
    """Evaluate topic taxonomy coverage and readiness."""

    def __init__(self, config_path=None):
        self.taxonomy = TopicTaxonomy(config_path)

    def validate_module(self, module_key):
        taxonomy = self.taxonomy.get_module_taxonomy(module_key)

        result = {
            "module_key": module_key,
            "valid": False,
            "ready": False,
            "verification_status": None,
            "topic_count": 0,
            "subtopic_count": 0,
            "errors": [],
            "warnings": [],
        }

        if taxonomy is None:
            result["errors"].append("Unknown module")
            return result

        topics = taxonomy["topics"]
        status = taxonomy["verification_status"]

        result["verification_status"] = status
        result["topic_count"] = len(topics)
        result["subtopic_count"] = sum(
            len(topic["subtopics"]) for topic in topics
        )

        if not topics:
            result["warnings"].append(
                "No topics configured for this module"
            )

        if status == "unverified":
            result["warnings"].append(
                "Topic taxonomy is unverified"
            )

        elif status == "partially_verified":
            result["warnings"].append(
                "Topic taxonomy is partially verified"
            )

        if topics and any(
            len(topic["subtopics"]) == 0 for topic in topics
        ):
            result["warnings"].append(
                "Some topics have no configured subtopics"
            )

        result["valid"] = True
        result["ready"] = self.taxonomy.is_module_ready(
            module_key
        )

        return result

    def validate_all(self):
        results = [
            self.validate_module(item["module_key"])
            for item in self.taxonomy.get_all()
        ]

        return {
            "total_modules": len(results),
            "valid_modules": sum(
                result["valid"] for result in results
            ),
            "ready_modules": sum(
                result["ready"] for result in results
            ),
            "modules_with_topics": sum(
                result["topic_count"] > 0
                for result in results
            ),
            "total_configured_topics": sum(
                result["topic_count"] for result in results
            ),
            "results": results,
        }
