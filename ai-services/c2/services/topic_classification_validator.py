
import json
import math
from pathlib import Path

from services.topic_taxonomy import TopicTaxonomy


DEFAULT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "topic_classification_schema.json"
)


class TopicClassificationValidator:
    def __init__(
        self,
        schema_path=None,
        taxonomy=None,
    ):
        self.schema_path = Path(
            schema_path or DEFAULT_SCHEMA_PATH
        )

        with self.schema_path.open(
            "r", encoding="utf-8"
        ) as file:
            self.schema = json.load(file)

        if self.schema.get("schema_version") != "1.0":
            raise ValueError(
                "Unsupported classification schema version"
            )

        self.taxonomy = (
            taxonomy if taxonomy is not None
            else TopicTaxonomy()
        )

    def validate(self, record):
        errors = []
        warnings = []

        if not isinstance(record, dict):
            return {
                "valid": False,
                "errors": ["Classification must be an object"],
                "warnings": [],
            }

        required = self.schema["required_fields"]
        definitions = self.schema["field_definitions"]

        for field in required:
            if field not in record:
                errors.append(
                    f"Missing required field: {field}"
                )

        if errors:
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
            }

        # Validate fields against the schema.
        for field, definition in definitions.items():
            if field not in record:
                continue

            value = record[field]
            allowed_types = definition["type"]

            if isinstance(allowed_types, str):
                allowed_types = [allowed_types]

            def matches_type(type_name):
                if type_name == "null":
                    return value is None
                if type_name == "string":
                    return isinstance(value, str)
                if type_name == "number":
                    return (
                        isinstance(value, (int, float))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                    )
                return False

            if not any(
                matches_type(t) for t in allowed_types
            ):
                errors.append(
                    f"Invalid type for {field}"
                )
                continue

            if "allowed_values" in definition:
                if value not in definition["allowed_values"]:
                    errors.append(
                        f"Invalid value for {field}: {value}"
                    )

            if (
                value is not None
                and "minimum" in definition
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value < definition["minimum"]
            ):
                errors.append(
                    f"{field} is below the minimum"
                )

            if (
                value is not None
                and "maximum" in definition
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value > definition["maximum"]
            ):
                errors.append(
                    f"{field} exceeds the maximum"
                )

        # Validate question identifier.
        question_id = record["question_id"]

        if (
            not isinstance(question_id, str)
            or not question_id.strip()
        ):
            errors.append("Invalid question_id")

        # Validate module against the taxonomy.
        module_key = record["module_key"]
        taxonomy = None

        if (
            not isinstance(module_key, str)
            or not module_key.strip()
        ):
            errors.append("Invalid module_key")
        else:
            taxonomy = self.taxonomy.get_module_taxonomy(
                module_key
            )

            if taxonomy is None:
                errors.append(
                    f"Unknown module: {module_key}"
                )

        topic_id = record["topic_id"]
        subtopic = record["subtopic"]
        method = record["classification_method"]
        confidence = record["confidence_score"]
        status = record["verification_status"]

        # Unclassified records must not contain topic assignments.
        if method == "unclassified":
            if topic_id is not None:
                errors.append(
                    "Unclassified records cannot have a topic_id"
                )

            if subtopic is not None:
                errors.append(
                    "Unclassified records cannot have a subtopic"
                )

            if confidence is not None:
                errors.append(
                    "Unclassified records cannot have confidence"
                )

            if status == "verified":
                errors.append(
                    "Unclassified records cannot be verified"
                )

        # Validate assigned topics.
        if topic_id is not None:
            if not isinstance(topic_id, str) or not topic_id.strip():
                errors.append("Invalid topic_id")
            elif taxonomy is not None:
                topics = taxonomy["topics"]

                matching_topic = next(
                    (
                        topic for topic in topics
                        if topic["topic_id"] == topic_id
                    ),
                    None,
                )

                if matching_topic is None:
                    errors.append(
                        f"Unknown topic_id for module: {topic_id}"
                    )
                else:
                    if (
                        subtopic is not None
                        and subtopic not in matching_topic["subtopics"]
                    ):
                        errors.append(
                            "Subtopic does not belong to topic"
                        )

                    if (
                        taxonomy["verification_status"]
                        != "verified"
                    ):
                        warnings.append(
                            "Module taxonomy is not verified"
                        )

                        if status == "verified":
                            errors.append(
                                "Cannot verify classification "
                                "against an unverified taxonomy"
                            )

        elif method != "unclassified":
            errors.append(
                "Classified records require a topic_id"
            )

        if isinstance(subtopic, str) and not subtopic.strip():
            errors.append("Empty subtopic")

        if (
            method in {"ml_model", "rule_based", "hybrid"}
            and confidence is None
        ):
            warnings.append(
                "Automated classification has no confidence score"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
