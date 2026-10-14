
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.batch_topic_classifier import BatchTopicClassifier
from services.topic_classifier import TopicClassifier
from services.topic_classification_validator import (
    TopicClassificationValidator,
)


class MockTaxonomy:
    """Controlled fixture, not an official syllabus."""

    def get_module_taxonomy(self, module_key):
        if module_key != "database_systems":
            return None

        return {
            "module_key": "database_systems",
            "verification_status": "verified",
            "topics": [
                {
                    "topic_id": "DB_TEST_01",
                    "topic_name": "Database Normalization",
                    "subtopics": ["Third Normal Form"],
                },
                {
                    "topic_id": "DB_TEST_02",
                    "topic_name": "Database Transactions",
                    "subtopics": ["ACID Properties"],
                },
            ],
        }

    def is_module_ready(self, module_key):
        return module_key == "database_systems"


def run_tests():
    print("--- M6.4 BATCH TOPIC CLASSIFICATION TEST ---")

    taxonomy = MockTaxonomy()

    classifier = TopicClassifier(
        taxonomy=taxonomy,
        min_confidence=0.3,
    )

    validator = TopicClassificationValidator(
        taxonomy=taxonomy
    )

    batch = BatchTopicClassifier(
        classifier=classifier,
        validator=validator,
    )

    questions = [
        {
            "question_id": "Q1(a)",
            "module_key": "database_systems",
            "question_text": (
                "Explain database normalization "
                "and Third Normal Form."
            ),
        },
        {
            "question_id": "Q2(a)",
            "module_key": "database_systems",
            "question_text": "Explain an unrelated concept.",
        },
        {
            "question_id": "Q3(a)",
            "module_key": "unknown_module",
            "question_text": "Explain ACID properties.",
        },
    ]

    result = batch.classify_questions(questions)
    summary = result["summary"]

    assert summary["total_questions"] == 3
    print("PASS: total question count")

    assert summary["classified"] == 1
    print("PASS: classified question count")

    assert summary["unclassified"] == 1
    print("PASS: unclassified question count")

    assert summary["invalid"] == 1
    print("PASS: invalid question count")

    assert len(result["results"]) == 3
    print("PASS: all question results preserved")

    assert result["results"][0]["valid"] is True
    assert result["results"][1]["valid"] is True
    assert result["results"][2]["valid"] is False
    print("PASS: independent question processing")

    empty = batch.classify_questions([])
    assert empty["summary"]["total_questions"] == 0
    assert empty["results"] == []
    print("PASS: empty batch handling")

    try:
        batch.classify_questions({})
        raise AssertionError("Expected ValueError")
    except ValueError:
        print("PASS: invalid batch rejection")

    print("\nAll M6.4 batch classifier tests passed.")


if __name__ == "__main__":
    run_tests()
