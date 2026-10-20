
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


BASE_DIR = Path(__file__).resolve().parents[1]

DEFAULT_REVIEW_PATH = (
    BASE_DIR
    / "outputs"
    / "question_classification_reviews"
    / "review_decisions.json"
)


class QuestionClassificationReviewRepository:
    """
    Store explicit lecturer review decisions separately
    from automated question classification results.

    This repository does not automatically approve labels.
    Authorization must be enforced by the API layer.
    """

    def __init__(self, path=None):
        self.path = Path(path or DEFAULT_REVIEW_PATH)
        self._lock = Lock()

    def _empty_document(self):
        return {
            "schema_version": "1.0",
            "reviews": [],
        }

    def load(self):
        if not self.path.exists():
            return self._empty_document()

        with self.path.open("r", encoding="utf-8") as file:
            document = json.load(file)

        if (
            not isinstance(document, dict)
            or document.get("schema_version") != "1.0"
            or not isinstance(document.get("reviews"), list)
        ):
            raise ValueError("Invalid question review repository")

        return document

    def get_review(self, question_id):
        document = self.load()

        for review in document["reviews"]:
            if review.get("question_id") == question_id:
                return review

        return None

    def list_reviews(self, module_key=None):
        reviews = self.load()["reviews"]

        if module_key is not None:
            reviews = [
                item
                for item in reviews
                if item.get("module_key") == module_key
            ]

        return reviews

    def save_review(self, record, allow_update=False):
        if not isinstance(record, dict):
            raise ValueError("Review record must be an object")

        decision = record.get("decision")
        if decision not in ("approved", "rejected", "deferred"):
            raise ValueError("Invalid review decision")

        base_required = (
            "question_id",
            "module_key",
            "decision",
            "reviewer_id",
        )

        for field in base_required:
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Missing or invalid review field: {field}"
                )

        raw_topic_id = record.get("topic_id")
        if decision == "approved":
            if not isinstance(raw_topic_id, str) or not raw_topic_id.strip():
                raise ValueError("Missing or invalid review field: topic_id")
            topic_id = raw_topic_id.strip()
        else:
            topic_id = raw_topic_id.strip() if isinstance(raw_topic_id, str) and raw_topic_id.strip() else None

        notes = record.get("review_notes", "")

        if not isinstance(notes, str) or len(notes) > 2000:
            raise ValueError("Invalid review notes")

        if decision == "rejected" and not notes.strip():
            raise ValueError("Rejection requires review notes")

        with self._lock:
            document = self.load()

            existing_idx = None
            for idx, item in enumerate(document["reviews"]):
                if item.get("question_id") == record["question_id"]:
                    existing_idx = idx
                    break

            if existing_idx is not None and not allow_update:
                raise ValueError(
                    "Question already has a review decision"
                )

            saved = {
                "question_id": record["question_id"].strip(),
                "module_key": record["module_key"].strip(),
                "topic_id": topic_id,
                "decision": decision,
                "review_notes": notes.strip(),
                "reviewer_id": record["reviewer_id"].strip(),
                "reviewed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            if "original_ai_suggestion" in record:
                saved["original_ai_suggestion"] = record["original_ai_suggestion"]
            if "taxonomy_version" in record:
                saved["taxonomy_version"] = record["taxonomy_version"]
            if "model_version" in record:
                saved["model_version"] = record["model_version"]
            if "is_correction" in record:
                saved["is_correction"] = bool(record["is_correction"])

            if existing_idx is not None:
                document["reviews"][existing_idx] = saved
            else:
                document["reviews"].append(saved)

            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            fd, temporary_path = tempfile.mkstemp(
                prefix=".question_reviews_",
                suffix=".json",
                dir=self.path.parent,
            )

            try:
                with os.fdopen(
                    fd,
                    "w",
                    encoding="utf-8",
                ) as file:
                    json.dump(
                        document,
                        file,
                        indent=2,
                        ensure_ascii=False,
                    )
                    file.flush()
                    os.fsync(file.fileno())

                os.replace(
                    temporary_path,
                    self.path,
                )

            finally:
                if os.path.exists(temporary_path):
                    os.unlink(temporary_path)

            return saved
