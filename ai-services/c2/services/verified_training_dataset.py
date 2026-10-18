
from collections import Counter

from services.trusted_question_verification import (
    TrustedQuestionVerification,
)


class VerifiedTrainingDatasetBuilder:
    """
    Build a training dataset from authentic questions
    with lecturer-approved topic classifications.

    Classification JSON flags alone are never
    accepted as proof of verification.
    """

    def __init__(self, verification=None):
        self.verification = (
            verification
            if verification is not None
            else TrustedQuestionVerification()
        )

    def build(self, questions, classification_results):
        if not isinstance(questions, list):
            raise ValueError("questions must be a list")

        if not isinstance(classification_results, list):
            raise ValueError(
                "classification_results must be a list"
            )

        question_index = {}

        for question in questions:
            if not isinstance(question, dict):
                raise ValueError("Invalid question record")

            question_id = question.get("question_id")

            if (
                not isinstance(question_id, str)
                or not question_id.strip()
            ):
                raise ValueError("Invalid question ID")

            if question_id in question_index:
                raise ValueError(
                    f"Duplicate question ID: {question_id}"
                )

            question_index[question_id] = question

        approved_labels = self.verification.approved_labels()

        records = []
        excluded = Counter()
        seen_classifications = set()

        for item in classification_results:
            if not isinstance(item, dict):
                excluded["invalid_classification_record"] += 1
                continue

            if item.get("valid") is not True:
                excluded["invalid_classification_record"] += 1
                continue

            classification = item.get("classification")

            if not isinstance(classification, dict):
                excluded["missing_classification"] += 1
                continue

            question_id = classification.get("question_id")

            if (
                not isinstance(question_id, str)
                or not question_id.strip()
            ):
                excluded["missing_question_id"] += 1
                continue

            if (
                item.get("question_id") is not None
                and item["question_id"] != question_id
            ):
                excluded["question_id_mismatch"] += 1
                continue

            if question_id in seen_classifications:
                raise ValueError(
                    f"Duplicate classification: {question_id}"
                )

            seen_classifications.add(question_id)

            question = question_index.get(question_id)

            if question is None:
                excluded["question_not_found"] += 1
                continue

            if question.get("source_type") != "authentic":
                excluded["non_authentic_source"] += 1
                continue

            approved = approved_labels.get(question_id)

            if approved is None:
                excluded["not_lecturer_approved"] += 1
                continue

            topic_id = classification.get("topic_id")
            module_key = classification.get("module_key")

            if (
                not isinstance(topic_id, str)
                or not topic_id.strip()
            ):
                excluded["missing_topic_label"] += 1
                continue

            if (
                not isinstance(module_key, str)
                or not module_key.strip()
            ):
                excluded["missing_module_key"] += 1
                continue

            if (
                approved["module_key"] != module_key
                or approved["topic_id"] != topic_id
            ):
                excluded["review_classification_mismatch"] += 1
                continue

            question_text = question.get("question_text")

            if (
                not isinstance(question_text, str)
                or not question_text.strip()
            ):
                excluded["missing_question_text"] += 1
                continue

            paper_id = question.get("paper_id")

            if (
                not isinstance(paper_id, str)
                or not paper_id.strip()
            ):
                excluded["missing_paper_id"] += 1
                continue

            records.append({
                "question_id": question_id,
                "paper_id": paper_id,
                "module_key": module_key,
                "topic_id": topic_id,
                "question_text": question_text.strip(),
                "source_type": "authentic",
                "verification_status": "verified",
                "classification_method": "lecturer_verified",
            })

        records.sort(
            key=lambda item: (
                item["module_key"],
                item["paper_id"],
                item["question_id"],
            )
        )

        return {
            "schema_version": "1.0",
            "dataset_type": "verified_authentic_topic_labels",
            "record_count": len(records),
            "source_paper_count": len({
                record["paper_id"]
                for record in records
            }),
            "topic_count": len({
                (record["module_key"], record["topic_id"])
                for record in records
            }),
            "excluded": dict(sorted(excluded.items())),
            "records": records,
        }
