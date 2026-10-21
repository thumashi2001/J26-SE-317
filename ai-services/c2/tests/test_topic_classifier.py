
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.topic_classifier import TopicClassifier


class MockTaxonomy:
    """Controlled fixture; not an official syllabus."""

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
                    "subtopics": [
                        "Third Normal Form",
                        "Functional Dependencies",
                    ],
                },
                {
                    "topic_id": "DB_TEST_02",
                    "topic_name": "Database Transactions",
                    "subtopics": [
                        "ACID Properties",
                        "Concurrency Control",
                    ],
                },
            ],
        }

    def is_module_ready(self, module_key):
        return module_key == "database_systems"


def run_tests():
    classifier = TopicClassifier(
        taxonomy=MockTaxonomy(),
        min_confidence=0.3,
    )

    print("--- M6.3 TOPIC CLASSIFICATION TEST ---")

    result = classifier.classify(
        question_id="Q1(a)",
        module_key="database_systems",
        question_text=(
            "Explain database normalization "
            "and Third Normal Form."
        ),
    )

    assert result["classification_method"] == "rule_based"
    assert result["topic_id"] == "DB_TEST_01"
    print("PASS: matching syllabus topic")

    result = classifier.classify(
        question_id="Q2(a)",
        module_key="database_systems",
        question_text="Explain ACID properties.",
    )

    assert result["topic_id"] == "DB_TEST_02"
    print("PASS: matching subtopic")

    result = classifier.classify(
        question_id="Q3(a)",
        module_key="database_systems",
        question_text="Discuss an unrelated concept.",
    )

    assert result["classification_method"] == "unclassified"
    print("PASS: unmatched question")

    try:
        classifier.classify(
            question_id="Q4(a)",
            module_key="unknown_module",
            question_text="Explain normalization.",
        )
        raise AssertionError("Expected ValueError")
    except ValueError:
        print("PASS: unknown module rejection")

    try:
        classifier.classify(
            question_id="",
            module_key="database_systems",
            question_text="Explain normalization.",
        )
        raise AssertionError("Expected ValueError")
    except ValueError:
        print("PASS: invalid question identifier")

    print("\nAll M6.3 topic classifier tests passed.")


if __name__ == "__main__":
    run_tests()
