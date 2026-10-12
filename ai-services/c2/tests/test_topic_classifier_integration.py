
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.topic_classifier import TopicClassifier
from services.topic_classification_validator import (
    TopicClassificationValidator,
)


class MockTaxonomy:
    def __init__(self, verified=True):
        self.verified = verified

    def get_module_taxonomy(self, module_key):
        if module_key != "database_systems":
            return None

        return {
            "module_key": "database_systems",
            "verification_status": (
                "verified" if self.verified else "unverified"
            ),
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
        return (
            module_key == "database_systems"
            and self.verified
        )


def test_integration():
    print("--- M6.3 CLASSIFIER INTEGRATION TEST ---")

    taxonomy = MockTaxonomy()
    classifier = TopicClassifier(
        taxonomy=taxonomy,
        min_confidence=0.3,
    )
    validator = TopicClassificationValidator(taxonomy=taxonomy)

    classified = classifier.classify(
        "Q1(a)",
        "database_systems",
        "Explain database normalization and Third Normal Form.",
    )

    validation = validator.validate(classified)

    assert validation["valid"], validation["errors"]
    assert classified["topic_id"] == "DB_TEST_01"
    assert classified["classification_method"] == "rule_based"
    print("PASS: classified record passes M6.2 validation")

    unclassified = classifier.classify(
        "Q2(a)",
        "database_systems",
        "Explain an unrelated concept.",
    )

    validation = validator.validate(unclassified)

    assert validation["valid"], validation["errors"]
    assert unclassified["classification_method"] == "unclassified"
    assert unclassified["topic_id"] is None
    assert unclassified["confidence_score"] is None
    print("PASS: unclassified record passes M6.2 validation")

    unverified_taxonomy = MockTaxonomy(verified=False)
    unverified_classifier = TopicClassifier(
        taxonomy=unverified_taxonomy,
        min_confidence=0.3,
    )
    unverified_validator = TopicClassificationValidator(
        taxonomy=unverified_taxonomy
    )

    result = unverified_classifier.classify(
        "Q3(a)",
        "database_systems",
        "Explain database normalization.",
    )

    validation = unverified_validator.validate(result)

    assert validation["valid"], validation["errors"]
    assert result["classification_method"] == "unclassified"
    print("PASS: unverified taxonomy safeguard")

    ambiguous_taxonomy = MockTaxonomy()
    ambiguous_taxonomy.get_module_taxonomy = lambda key: {
        "module_key": key,
        "verification_status": "verified",
        "topics": [
            {
                "topic_id": "T1",
                "topic_name": "Database Normalization",
                "subtopics": [],
            },
            {
                "topic_id": "T2",
                "topic_name": "Database Transactions",
                "subtopics": [],
            },
        ],
    }

    ambiguous_classifier = TopicClassifier(
        taxonomy=ambiguous_taxonomy,
        min_confidence=0.3,
    )

    result = ambiguous_classifier.classify(
        "Q4(a)",
        "database_systems",
        "Compare database normalization and database transactions.",
    )

    assert result["classification_method"] == "unclassified"
    print("PASS: ambiguous topic handling")

    print("\nAll M6.3 integration tests passed.")


if __name__ == "__main__":
    test_integration()
