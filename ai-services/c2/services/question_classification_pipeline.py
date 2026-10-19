
import json
from pathlib import Path

from services.batch_topic_classifier import BatchTopicClassifier


BASE_DIR = Path(__file__).resolve().parents[1]

DEFAULT_QUESTIONS_PATH = (
    BASE_DIR / "datasets" / "processed" / "questions.json"
)

DEFAULT_MODULES_PATH = BASE_DIR / "config" / "modules.json"

DEFAULT_OUTPUT_PATH = (
    BASE_DIR / "datasets" / "processed" / "topic_classifications.json"
)


class QuestionClassificationPipeline:
    """Integrate stored examination questions with batch topic classification."""

    def __init__(self, classifier=None, modules_path=None):
        self.classifier = (
            classifier if classifier is not None
            else BatchTopicClassifier()
        )

        self.modules_path = Path(modules_path or DEFAULT_MODULES_PATH)

    def load_questions(self, questions_path=None):
        path = Path(questions_path or DEFAULT_QUESTIONS_PATH)

        with path.open("r", encoding="utf-8") as file:
            questions = json.load(file)

        if not isinstance(questions, list):
            raise ValueError("Question repository must contain a list")

        return questions

    
    def load_module_mapping(self):
        """
        Build a mapping from verified module codes to module keys.

        Modules with unknown codes are skipped.
        """
        with self.modules_path.open("r", encoding="utf-8") as file:
            config = json.load(file)

        if not isinstance(config, dict):
            raise ValueError("Module configuration must be an object")

        modules = config.get("modules")

        if not isinstance(modules, list):
            raise ValueError(
                "Module configuration must contain a modules list"
            )

        mapping = {}

        for module in modules:
            if not isinstance(module, dict):
                raise ValueError("Each module must be an object")

            module_key = module.get("module_key")
            module_code = module.get("module_code")

            if not isinstance(module_key, str) or not module_key.strip():
                raise ValueError("Invalid module_key in configuration")

            # Unknown module codes are allowed in M4 configuration.
            if module_code is not None:
                if not isinstance(module_code, str) or not module_code.strip():
                    raise ValueError(
                        f"Invalid module_code for {module_key}"
                    )

                if module_code in mapping:
                    raise ValueError(
                        f"Duplicate module code: {module_code}"
                    )

                mapping[module_code] = module_key

            # Support aliases (e.g. SE3060 alongside IT3020 for database_systems)
            for alias in module.get("aliases", []):
                if isinstance(alias, str) and alias.strip() and alias not in mapping:
                    mapping[alias] = module_key

        return mapping


    def prepare_questions(self, questions):
        if not isinstance(questions, list):
            raise ValueError("Questions must be a list")

        mapping = self.load_module_mapping()
        prepared = []

        for question in questions:
            if not isinstance(question, dict):
                prepared.append(question)
                continue

            module_code = question.get("module_code")
            module_key = mapping.get(module_code)

            prepared.append({
                "question_id": question.get("question_id"),
                "module_key": module_key,
                "question_text": question.get("question_text"),
                "source_type": question.get("source_type"),
            })


        return prepared

    def run(self, questions_path=None, output_path=None):
        questions = self.load_questions(questions_path)
        prepared = self.prepare_questions(questions)

        batch_result = self.classifier.classify_questions(prepared)

        output = {
            "schema_version": "1.0",
            "source_repository": str(
                Path(questions_path or DEFAULT_QUESTIONS_PATH)
            ),
            "summary": batch_result["summary"],
            "results": batch_result["results"],
        }

        destination = Path(output_path or DEFAULT_OUTPUT_PATH)
        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("w", encoding="utf-8") as file:
            json.dump(output, file, indent=2, ensure_ascii=False)

        return output
