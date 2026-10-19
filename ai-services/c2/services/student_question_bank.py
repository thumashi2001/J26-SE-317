
import json
from pathlib import Path

from services.question_classification_pipeline import (
    DEFAULT_QUESTIONS_PATH,
    DEFAULT_OUTPUT_PATH,
    QuestionClassificationPipeline,
)
from services.trusted_question_verification import (
    TrustedQuestionVerification,
)


class StudentQuestionBank:
    """Read-only question bank with trusted lecturer verification."""

    def __init__(
        self,
        questions_path=None,
        classifications_path=None,
        modules_path=None,
        verification=None,
    ):
        self.questions_path = Path(
            questions_path or DEFAULT_QUESTIONS_PATH
        )
        self.classifications_path = Path(
            classifications_path or DEFAULT_OUTPUT_PATH
        )
        self.pipeline = QuestionClassificationPipeline(
            modules_path=modules_path
        )
        self.verification = (
            verification or TrustedQuestionVerification()
        )

    @staticmethod
    def _load_json(path):
        if not path.exists():
            raise FileNotFoundError(
                f"Question repository file not found at '{path}'. "
                "The authentic question repository has not been generated yet. "
                "Run 'python scripts/ingest_authentic_dataset.py' to extract authentic questions "
                "from authorized past-paper PDFs in datasets/authentic/."
            )
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def list_questions(
        self,
        module_key=None,
        page=1,
        page_size=10,
    ):
        if not isinstance(page, int) or page < 1:
            raise ValueError("Invalid page")

        if not isinstance(page_size, int) or not 1 <= page_size <= 100:
            raise ValueError("Invalid page size")

        questions = self._load_json(self.questions_path)

        if not isinstance(questions, list):
            raise ValueError("Question repository must contain a list")

        classification_data = self._load_json(
            self.classifications_path
        )

        if not isinstance(classification_data, dict):
            raise ValueError("Invalid classification dataset")

        results = classification_data.get("results", [])

        if not isinstance(results, list):
            raise ValueError("Invalid classification results")

        classifications = {}

        for result in results:
            if not isinstance(result, dict):
                continue

            classification = result.get("classification")

            if (
                result.get("valid") is True
                and isinstance(classification, dict)
                and isinstance(result.get("question_id"), str)
                and result["question_id"] == classification.get("question_id")
            ):
                question_id = result["question_id"]

                if question_id in classifications:
                    raise ValueError(
                        f"Duplicate classification: {question_id}"
                    )

                classifications[question_id] = classification

        module_mapping = self.pipeline.load_module_mapping()
        approved_labels = self.verification.approved_labels()

        records = []

        for question in questions:
            if not isinstance(question, dict):
                continue

            question_module = module_mapping.get(
                question.get("module_code")
            )

            if module_key and question_module != module_key:
                continue

            question_id = question.get("question_id")
            classification = classifications.get(question_id, {})

            approved = approved_labels.get(question_id)

            is_verified = (
                question.get("source_type") == "authentic"
                and approved is not None
                and approved["module_key"] == question_module
                and approved["topic_id"] == classification.get("topic_id")
                and classification.get("module_key") == question_module
            )

            records.append({
                "question_id": question_id,
                "module_key": question_module,
                "module_name": question.get("module_name"),
                "question_text": question.get("question_text"),
                "marks": question.get("marks"),
                "marks_status": question.get("marks_status"),
                "topic_id": (
                    approved["topic_id"]
                    if is_verified
                    else None
                ),
                "classification_method": (
                    "lecturer_verified"
                    if is_verified
                    else "unclassified"
                ),
                "verification_status": (
                    "verified"
                    if is_verified
                    else "unverified"
                ),
                "bloom_level": question.get("bloom_level"),
                "difficulty": question.get("difficulty"),
                "calendar_year": question.get("calendar_year"),
                "source_type": question.get("source_type"),
                "source_filename": question.get("source_filename"),
            })

        total = len(records)
        start = (page - 1) * page_size

        return {
            "module_key": module_key,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(
                1,
                (total + page_size - 1) // page_size,
            ),
            "questions": records[start:start + page_size],
        }
