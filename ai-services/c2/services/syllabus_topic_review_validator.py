
import json
from datetime import datetime
from pathlib import Path


class SyllabusTopicReviewValidator:
    """
    Validate manual syllabus topic review records.

    Validation does not approve candidates or change their
    verification status.
    """

    def __init__(self, schema_path=None):
        if schema_path is None:
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "config"
                / "syllabus_topic_review_schema.json"
            )

        with Path(schema_path).open("r", encoding="utf-8") as file:
            self.schema = json.load(file)

        if self.schema.get("schema_version") != "1.0":
            raise ValueError("Unsupported review schema version")

        if self.schema.get("schema_name") != "syllabus_topic_review":
            raise ValueError("Invalid review schema name")

    def validate(self, record):
        errors = []

        if not isinstance(record, dict):
            return {
                "valid": False,
                "errors": ["Review record must be a dictionary"],
            }

        required_fields = self.schema["required_fields"]

        for field in required_fields:
            if field not in record:
                errors.append(f"Missing required field: {field}")

        if errors:
            return {"valid": False, "errors": errors}

        for field in ("candidate_id", "module_key", "candidate_name"):
            value = record[field]

            if not isinstance(value, str) or not value.strip():
                errors.append(f"Invalid {field}")

        decision = record["review_decision"]
        status = record["verification_status"]

        allowed_decisions = self.schema["fields"]["review_decision"][
            "allowed_values"
        ]

        allowed_statuses = self.schema["fields"]["verification_status"][
            "allowed_values"
        ]

        if decision not in allowed_decisions:
            errors.append("Invalid review decision")

        if status not in allowed_statuses:
            errors.append("Invalid verification status")

        rules = self.schema["decision_rules"].get(decision)

        if rules:
            if status != rules["verification_status"]:
                errors.append(
                    "Verification status does not match review decision"
                )

            if rules["reviewer_required"]:
                reviewer_id = record["reviewer_id"]

                if (
                    not isinstance(reviewer_id, str)
                    or not reviewer_id.strip()
                ):
                    errors.append("Reviewer ID is required")

            if rules["reviewed_at_required"]:
                reviewed_at = record["reviewed_at"]

                if not isinstance(reviewed_at, str):
                    errors.append("Review timestamp is required")
                else:
                    try:
                        parsed = datetime.fromisoformat(
                            reviewed_at.replace("Z", "+00:00")
                        )

                        if parsed.tzinfo is None:
                            errors.append(
                                "Review timestamp must include timezone"
                            )
                    except ValueError:
                        errors.append("Invalid review timestamp")

        if decision == "pending":
            if record["reviewer_id"] is not None:
                errors.append(
                    "Pending review must not have a reviewer"
                )

            if record["reviewed_at"] is not None:
                errors.append(
                    "Pending review must not have a timestamp"
                )

        if not isinstance(record["review_notes"], str):
            errors.append("Review notes must be a string")

        sources = record["sources"]

        if not isinstance(sources, list) or not sources:
            errors.append("At least one source reference is required")
        else:
            for index, source in enumerate(sources):
                if not isinstance(source, dict):
                    errors.append(
                        f"Invalid source reference at index {index}"
                    )
                    continue

                filename = source.get("filename")
                line_number = source.get("line_number")

                if (
                    not isinstance(filename, str)
                    or not filename.strip()
                    or not isinstance(line_number, int)
                    or isinstance(line_number, bool)
                    or line_number < 1
                ):
                    errors.append(
                        f"Invalid source evidence at index {index}"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
