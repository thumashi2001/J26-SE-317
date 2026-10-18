
import json
from pathlib import Path

from services.question_classification_review_repository import (
    QuestionClassificationReviewRepository,
)

BASE_DIR = Path(__file__).resolve().parents[1]


class QuestionClassificationReviewService:
    def __init__(
        self,
        questions_path=None,
        modules_path=None,
        taxonomy_path=None,
        repository=None,
    ):
        self.questions_path = Path(
            questions_path or BASE_DIR / "datasets/processed/questions.json"
        )
        self.modules_path = Path(
            modules_path or BASE_DIR / "config/modules.json"
        )
        self.taxonomy_path = Path(
            taxonomy_path or BASE_DIR / "config/topic_taxonomies.json"
        )
        self.repository = (
            repository or QuestionClassificationReviewRepository()
        )

    @staticmethod
    def _read_json(path):
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def review(
        self,
        *,
        question_id,
        module_key,
        topic_id,
        decision,
        reviewer_id,
        review_notes="",
    ):
        if decision not in ("approved", "rejected"):
            raise ValueError("Invalid review decision")

        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                question_id,
                module_key,
                topic_id,
                reviewer_id,
            )
        ):
            raise ValueError("Required review fields are invalid")

        if not isinstance(review_notes, str):
            raise ValueError("Review notes must be a string")

        if decision == "rejected" and not review_notes.strip():
            raise ValueError("Rejection requires review notes")

        questions = self._read_json(self.questions_path)

        if not isinstance(questions, list):
            raise ValueError("Invalid question repository")

        matches = [
            question for question in questions
            if question.get("question_id") == question_id
        ]

        if len(matches) != 1:
            raise ValueError(
                "Question does not exist uniquely in repository"
            )

        question = matches[0]

        if question.get("source_type") != "authentic":
            raise ValueError(
                "Only authentic questions may be reviewed"
            )

        modules_document = self._read_json(self.modules_path)

        modules = modules_document.get("modules", [])

        matching_modules = [
            module for module in modules
            if module.get("module_key") == module_key
        ]

        if len(matching_modules) != 1:
            raise ValueError("Unknown or ambiguous module")

        module_code = matching_modules[0].get("module_code")

        if (
            not module_code
            or question.get("module_code") != module_code
        ):
            raise ValueError(
                "Question does not belong to selected module"
            )

        taxonomy_document = self._read_json(self.taxonomy_path)

        taxonomies = taxonomy_document.get("taxonomies", [])

        matching_taxonomies = [
            taxonomy for taxonomy in taxonomies
            if taxonomy.get("module_key") == module_key
        ]

        if len(matching_taxonomies) != 1:
            raise ValueError(
                "Module taxonomy is missing or ambiguous"
            )

        taxonomy = matching_taxonomies[0]

        if decision == "approved":
            if taxonomy.get("verification_status") != "verified":
                raise ValueError(
                    "Module taxonomy is not verified"
                )

            topics = taxonomy.get("topics", [])

            matching_topics = [
                topic for topic in topics
                if topic.get("topic_id") == topic_id
            ]

            if len(matching_topics) != 1:
                raise ValueError(
                    "Topic is not present in approved taxonomy"
                )

        return self.repository.save_review({
            "question_id": question_id,
            "module_key": module_key,
            "topic_id": topic_id,
            "decision": decision,
            "reviewer_id": reviewer_id,
            "review_notes": review_notes,
        })
