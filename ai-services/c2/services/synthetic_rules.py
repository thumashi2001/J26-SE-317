
import json
from pathlib import Path

from services.module_registry import ModuleRegistry


DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "synthetic_rules.json"
)


class SyntheticRules:
    """
    Validate synthetic examination generation readiness.
    """

    def __init__(
        self,
        rules_path=DEFAULT_RULES_PATH,
        registry=None,
    ):
        self.rules_path = Path(rules_path)
        self.registry = registry or ModuleRegistry()

        with self.rules_path.open(
            "r", encoding="utf-8"
        ) as file:
            self.rules = json.load(file)

        self.validate_configuration()

    def validate_configuration(self):
        if self.rules.get("schema_version") != "1.0":
            raise ValueError(
                "Unsupported synthetic rules version"
            )

        policy = self.rules.get("generation_policy")
        quality = self.rules.get("quality_rules")

        if not isinstance(policy, dict):
            raise ValueError(
                "Missing generation policy"
            )

        if not isinstance(quality, dict):
            raise ValueError(
                "Missing quality rules"
            )

        if policy.get("source_type") != "synthetic":
            raise ValueError(
                "Generated content must be labeled synthetic"
            )

        if policy.get("allow_unverified_exam_structures") is not False:
            raise ValueError(
                "Unverified exam structures must not be allowed"
            )

        if quality.get("require_unique_question_ids") is not True:
            raise ValueError(
                "Unique question IDs must be required"
            )

        if quality.get("require_positive_marks") is not True:
            raise ValueError(
                "Positive marks validation must be required"
            )

        return True

    def check_module_readiness(self, module_key):
        module = self.registry.get_by_key(module_key)

        if module is None:
            raise ValueError(
                f"Unknown module: {module_key}"
            )

        missing = []

        if not module.get("module_code"):
            missing.append("module_code")

        if not module.get("topics"):
            missing.append("verified_topics")

        if not module.get("exam_structure"):
            missing.append("verified_exam_structure")

        defaults = self.rules.get(
            "generation_defaults", {}
        )

        if defaults.get("target_papers_per_module") is None:
            missing.append("generation_target")

        return {
            "module_key": module_key,
            "ready": len(missing) == 0,
            "missing_requirements": missing,
        }

    def validate_generated_question(self, question):
        """
        Validate an individual generated question.
        """
        errors = []

        if question.get("source_type") != "synthetic":
            errors.append(
                "Question must have synthetic provenance"
            )

        question_id = question.get("question_id")
        if not isinstance(question_id, str) or not question_id.strip():
            errors.append("Missing question ID")

        text = question.get("question_text")

        min_length = self.rules["quality_rules"].get(
            "minimum_question_text_length", 20
        )

        if not isinstance(text, str) or len(text.strip()) < min_length:
            errors.append("Question text is too short")

        marks = question.get("marks")

        if isinstance(marks, bool) or not isinstance(
            marks, (int, float)
        ) or marks <= 0:
            errors.append("Marks must be positive")

        module_key = question.get("module_key")
        module = self.registry.get_by_key(module_key)

        if module is None:
            errors.append("Unknown module")
        else:
            if question.get("module_code") != module.get("module_code"):
                errors.append("Module code mismatch")

            topics = module.get("topics") or []
            if not question.get("topic") or question["topic"] not in topics:
                errors.append("Topic is not in verified module topics")

        if not question.get("generation_provenance"):
            errors.append("Missing generation provenance")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
