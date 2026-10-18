
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DEFAULT_REVIEWS_PATH = (
    BASE_DIR
    / "outputs/question_classification_reviews/review_decisions.json"
)

DEFAULT_TAXONOMY_PATH = BASE_DIR / "config/topic_taxonomies.json"


class TrustedQuestionVerification:
    """
    Resolve lecturer-approved question/topic assignments.

    A classification JSON's verification_status is never
    sufficient evidence of approval.
    """

    def __init__(self, reviews_path=None, taxonomy_path=None):
        self.reviews_path = Path(
            reviews_path or DEFAULT_REVIEWS_PATH
        )
        self.taxonomy_path = Path(
            taxonomy_path or DEFAULT_TAXONOMY_PATH
        )

    @staticmethod
    def _load(path):
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def approved_labels(self):
        # Missing reviews mean no verified labels.
        if not self.reviews_path.exists():
            return {}

        reviews_data = self._load(self.reviews_path)
        taxonomy_data = self._load(self.taxonomy_path)

        if not isinstance(reviews_data, dict):
            raise ValueError("Invalid review document")

        if not isinstance(taxonomy_data, dict):
            raise ValueError("Invalid taxonomy document")

        reviews = reviews_data.get("reviews")
        taxonomies = taxonomy_data.get("taxonomies")

        if not isinstance(reviews, list):
            raise ValueError("Invalid review records")

        if not isinstance(taxonomies, list):
            raise ValueError("Invalid taxonomies")

        approved_topics = {}

        for taxonomy in taxonomies:
            if not isinstance(taxonomy, dict):
                raise ValueError("Invalid module taxonomy")

            if taxonomy.get("verification_status") != "verified":
                continue

            module_key = taxonomy.get("module_key")
            topics = taxonomy.get("topics", [])

            if not isinstance(module_key, str):
                raise ValueError("Invalid taxonomy module key")

            if not isinstance(topics, list):
                raise ValueError("Invalid taxonomy topics")

            approved_topics[module_key] = {
                topic["topic_id"]
                for topic in topics
                if isinstance(topic, dict)
                and isinstance(topic.get("topic_id"), str)
                and topic["topic_id"].strip()
            }

        labels = {}
        seen = set()

        for review in reviews:
            if not isinstance(review, dict):
                raise ValueError("Invalid question review")

            question_id = review.get("question_id")

            if not isinstance(question_id, str) or not question_id:
                raise ValueError("Invalid reviewed question ID")

            if question_id in seen:
                raise ValueError(
                    f"Duplicate question review: {question_id}"
                )

            seen.add(question_id)

            if review.get("decision") != "approved":
                continue

            module_key = review.get("module_key")
            topic_id = review.get("topic_id")
            reviewer_id = review.get("reviewer_id")

            if (
                not isinstance(module_key, str)
                or not isinstance(topic_id, str)
                or not isinstance(reviewer_id, str)
                or not reviewer_id.strip()
            ):
                raise ValueError(
                    "Invalid approved review metadata"
                )

            if topic_id not in approved_topics.get(module_key, set()):
                continue

            labels[question_id] = {
                "module_key": module_key,
                "topic_id": topic_id,
                "reviewer_id": reviewer_id,
                "reviewed_at": review.get("reviewed_at"),
            }

        return labels

    def verify(self, question_id, module_key, topic_id):
        label = self.approved_labels().get(question_id)

        if not label:
            return False

        return (
            label["module_key"] == module_key
            and label["topic_id"] == topic_id
        )
