import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_candidate_filter import (
    SyllabusTopicCandidateFilter,
)


def run_tests():
    topic_filter = SyllabusTopicCandidateFilter()

    noise_examples = [
        "$ne not equal to",
        "(k < B-1 pages)",
        "/BARS/* captures all BAR",
        "(Note that 17 is pushed up and only",
        "4 HAProxy Load Balancers (To support CloudFlare)",
        "A N D Q U A N TA",
    ]

    valid_topics = [
        "4+1 View Model",
        "Abstraction",
        "Database Normalization",
        "Data Partitioning",
        "Clustered and Non-Clustered Indexes",
        "Achieving Quality Goals",
        "Active Reviews for Intermediate Designs (ARID)",
        "SQL",
    ]

    for text in noise_examples:
        reason = topic_filter.get_rejection_reason(text)
        assert reason is not None, (
            f"Noise incorrectly preserved: {text}"
        )

    print("PASS: structural noise rejected")

    for text in valid_topics:
        reason = topic_filter.get_rejection_reason(text)
        assert reason is None, (
            f"Valid topic incorrectly rejected: {text} ({reason})"
        )

    print("PASS: legitimate technical topics preserved")
    print("\nAll M7.3.5.1c structural filtering tests passed.")


if __name__ == "__main__":
    run_tests()