
import json
from pathlib import Path


CONFIG_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "exam_structures.json"
)

VALID_STATUSES = {
    "verified",
    "partially_verified",
    "unverified",
}


def load_exam_structures(config_path=CONFIG_PATH):
    """Load module-specific examination structures."""
    with open(config_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data.get("structures"), list):
        raise ValueError("Missing examination structures list")

    return data


def get_exam_structure(module_key, config_path=CONFIG_PATH):
    """Retrieve a module's examination structure."""
    data = load_exam_structures(config_path)

    for item in data["structures"]:
        if item.get("module_key") == module_key:
            return item

    return None


def validate_exam_structure(module_key, config_path=CONFIG_PATH):
    """Validate a configured examination structure."""
    result = {
        "module_key": module_key,
        "valid": False,
        "ready": False,
        "verification_status": None,
        "errors": [],
        "warnings": [],
    }

    config = get_exam_structure(module_key, config_path)

    if config is None:
        result["errors"].append("Unknown module")
        return result

    status = config.get("verification_status")
    structure = config.get("structure")

    result["verification_status"] = status

    if status not in VALID_STATUSES:
        result["errors"].append("Invalid verification status")

    if structure is None:
        result["warnings"].append(
            "Examination structure is not available"
        )
        result["valid"] = not result["errors"]
        return result

    if not isinstance(structure, dict):
        result["errors"].append(
            "Examination structure must be an object"
        )
        return result

    required_fields = [
        "examination_type",
        "duration_minutes",
        "total_marks",
        "question_count",
        "questions_to_answer",
        "marks_per_question",
    ]

    for field in required_fields:
        if structure.get(field) is None:
            result["errors"].append(
                f"Missing required field: {field}"
            )

    positive_fields = [
        "duration_minutes",
        "total_marks",
        "question_count",
        "questions_to_answer",
        "marks_per_question",
    ]

    for field in positive_fields:
        value = structure.get(field)

        if value is not None and (
            type(value) is not int or value <= 0
        ):
            result["errors"].append(
                f"Invalid positive integer: {field}"
            )

    question_count = structure.get("question_count")
    questions_to_answer = structure.get(
        "questions_to_answer"
    )
    total_marks = structure.get("total_marks")
    marks_per_question = structure.get(
        "marks_per_question"
    )

    if (
        type(question_count) is int
        and type(questions_to_answer) is int
        and questions_to_answer > question_count
    ):
        result["errors"].append(
            "Questions to answer exceeds question count"
        )

    if (
        type(total_marks) is int
        and type(questions_to_answer) is int
        and type(marks_per_question) is int
        and total_marks != (
            questions_to_answer * marks_per_question
        )
    ):
        result["warnings"].append(
            "Total marks do not match the configured "
            "question marks calculation"
        )

    if status == "unverified":
        result["warnings"].append(
            "Structure has not been verified"
        )

    if status == "partially_verified":
        result["warnings"].append(
            "Structure is only partially verified"
        )

    if not config.get("source_reference"):
        result["warnings"].append(
            "Missing source reference"
        )

    result["valid"] = not result["errors"]
    result["ready"] = (
        result["valid"]
        and status == "verified"
    )

    return result
