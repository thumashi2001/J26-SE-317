import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_candidate_filter import (
    SyllabusTopicCandidateFilter,
)


def run_tests():
    print("--- M7.3.5.1b CANDIDATE QUALITY FILTER TEST ---")

    candidate_filter = SyllabusTopicCandidateFilter()

    rejected_cases = {
        "$gte": "quality_noise_pattern",
        "$push": "quality_noise_pattern",
        "<catalog>": "quality_noise_pattern",
        '<doc id="123">': "quality_noise_pattern",
        "( empid NUMBER,": "quality_noise_pattern",
        "3rd Year – Semester 1": "quality_noise_pattern",
        "(contd.)": "quality_noise_pattern",
        "11 IIS Web Servers": "quality_noise_pattern",
        "2 Firewalls": "quality_noise_pattern",
        "A collection of tactics an Architectural Strategy":
            "quality_noise_pattern",
        "(discussed later)": "quality_noise_pattern",
        "Some incomplete text,": "incomplete_fragment",
    }

    for text, expected_reason in rejected_cases.items():
        actual = candidate_filter.get_rejection_reason(text)

        assert actual == expected_reason, (
            f"Expected {expected_reason} for {text!r}, "
            f"got {actual!r}"
        )

    print("PASS: obvious technical and presentation noise rejected")

    valid_topics = [
        "Database Normalization",
        "First Normal Form",
        "Second Normal Form",
        "B+ Tree",
        "4+1 View Model",
        "REST API",
        "Software Architecture",
        "Quality Attribute Scenarios",
        "Microservices Architecture",
        "Distributed Transactions",
        "SOLID Principles",
        "SQL",
        "MongoDB Aggregation",
        "User Experience Design",
    ]

    for topic in valid_topics:
        actual = candidate_filter.get_rejection_reason(topic)

        assert actual is None, (
            f"Valid topic incorrectly rejected: {topic!r} "
            f"({actual})"
        )

    print("PASS: legitimate technical topics preserved")
    print("\nAll M7.3.5.1b quality filtering tests passed.")


if __name__ == "__main__":
    run_tests()