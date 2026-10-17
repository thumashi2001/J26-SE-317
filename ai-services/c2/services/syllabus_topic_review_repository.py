
import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from services.syllabus_topic_review_validator import (
    SyllabusTopicReviewValidator,
)


class SyllabusTopicReviewRepository:
    """
    Local JSON repository for manual syllabus topic reviews.

    Maintains current review records and a history of decisions.
    This is a development repository, not an authenticated API.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, storage_path=None):
        if storage_path is None:
            storage_path = (
                Path(__file__).resolve().parents[1]
                / "outputs"
                / "syllabus_reviews"
                / "review_decisions.json"
            )

        self.storage_path = Path(storage_path)
        self.validator = SyllabusTopicReviewValidator()

    def _empty_database(self):
        return {
            "schema_version": self.SCHEMA_VERSION,
            "reviews": {},
            "history": [],
        }

    def _load(self):
        if not self.storage_path.exists():
            return self._empty_database()

        with self.storage_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if (
            not isinstance(data, dict)
            or data.get("schema_version") != self.SCHEMA_VERSION
            or not isinstance(data.get("reviews"), dict)
            or not isinstance(data.get("history"), list)
        ):
            raise ValueError("Invalid review repository format")

        return data

    def _save(self, data):
        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.storage_path.parent,
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                json.dump(
                    data,
                    temp_file,
                    indent=2,
                    ensure_ascii=False,
                )
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)

            os.replace(temp_path, self.storage_path)

        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def get_review(self, candidate_id):
        data = self._load()
        review = data["reviews"].get(candidate_id)

        return copy.deepcopy(review) if review else None

    def list_reviews(self, module_key=None):
        data = self._load()

        reviews = list(data["reviews"].values())

        if module_key is not None:
            reviews = [
                review
                for review in reviews
                if review["module_key"] == module_key
            ]

        return copy.deepcopy(reviews)

    def get_history(self, candidate_id=None):
        data = self._load()
        history = data["history"]

        if candidate_id is not None:
            history = [
                event
                for event in history
                if event["candidate_id"] == candidate_id
            ]

        return copy.deepcopy(history)

    def save_review(self, record):
        """
        Save a validated review record.

        A completed decision requires reviewer metadata.
        The caller is responsible for authenticating the reviewer.
        """
        validation = self.validator.validate(record)

        if not validation["valid"]:
            raise ValueError(
                "Invalid review record: "
                + "; ".join(validation["errors"])
            )

        candidate_id = record["candidate_id"]

        data = self._load()
        previous = data["reviews"].get(candidate_id)
        if previous is not None:
         raise ValueError(
        "Candidate has already been reviewed. "
        "Existing decisions cannot be overwritten."
         )

        if previous is not None:
            if (
                previous["module_key"] != record["module_key"]
                or previous["candidate_name"]
                != record["candidate_name"]
                or previous["sources"] != record["sources"]
            ):
                raise ValueError(
                    "Candidate identity or source evidence cannot change"
                )

        if (
            previous is not None
            and previous == record
        ):
            return copy.deepcopy(previous)

        event = {
            "candidate_id": candidate_id,
            "module_key": record["module_key"],
            "previous_decision": (
                previous["review_decision"]
                if previous is not None
                else None
            ),
            "new_decision": record["review_decision"],
            "reviewer_id": record["reviewer_id"],
            "event_timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "review_record": copy.deepcopy(record),
        }

        data["reviews"][candidate_id] = copy.deepcopy(record)
        data["history"].append(event)

        self._save(data)

        return copy.deepcopy(record)
