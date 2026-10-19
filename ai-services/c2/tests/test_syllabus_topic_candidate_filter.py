
import sys
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.syllabus_topic_candidate_filter import (
    SyllabusTopicCandidateFilter,
)


def make_candidate(name, module_key="database_systems"):
    return {
        "module_key": module_key,
        "candidate_name": name,
        "verification_status": "unverified",
        "extraction_method": "rule_based",
        "sources": [
            {"filename": "lecture01.pdf", "line_number": 5}
        ],
    }


def run_tests():
    print("\n--- M7.3.5.1 TOPIC CANDIDATE FILTER TEST ---")

    topic_filter = SyllabusTopicCandidateFilter()

    valid_topics = [
        "Database Normalization",
        "Software Architecture Patterns",
        "Third Normal Form",
        "Unit Testing",
        "Design Patterns",
        "Example-Based Testing",
    ]

    for name in valid_topics:
        assert topic_filter.get_rejection_reason(name) is None

    print("PASS: valid technical topics preserved")

    noise_examples = [
        "All rights reserved",
        "Click here to continue",
        "Figure 3: Example Output",
        "www.example.com",
        "What is a database?",
        "Slide 12 of 30",
        "contact@example.com",
        "Example 2: Sample Output",
    ]

    for name in noise_examples:
        assert topic_filter.get_rejection_reason(name) is not None

    print("PASS: obvious noise detected")

    candidates = [
        make_candidate(name)
        for name in valid_topics + noise_examples
    ]

    extraction_result = {
        "schema_version": "1.0",
        "module_key": "database_systems",
        "candidate_count": len(candidates),
        "candidates": candidates,
    }

    original = deepcopy(extraction_result)

    filtered = topic_filter.filter(extraction_result)

    assert filtered["summary"]["total_candidates"] == 14
    assert filtered["summary"]["kept"] == 6
    assert filtered["summary"]["rejected"] == 8

    print("PASS: filtering summary consistency")

    assert all(
        candidate["verification_status"] == "unverified"
        for candidate in filtered["candidates"]
    )

    print("PASS: verification safeguards preserved")

    assert all(
        item["rejection_reason"]
        for item in filtered["rejected_candidates"]
    )

    print("PASS: rejection reasons preserved")

    assert extraction_result == original

    print("PASS: original candidates unchanged")

    multi_module_result = {
        "schema_version": "1.0",
        "modules": {
            "database_systems": extraction_result,
            "software_architecture": {
                "schema_version": "1.0",
                "module_key": "software_architecture",
                "candidate_count": 1,
                "candidates": [
                    make_candidate(
                        "Architectural Patterns",
                        "software_architecture",
                    )
                ],
            },
        },
    }

    multi_filtered = topic_filter.filter_all(multi_module_result)

    assert multi_filtered["summary"]["total_modules"] == 2
    assert multi_filtered["summary"]["total_candidates"] == 15
    assert multi_filtered["summary"]["kept"] == 7
    assert multi_filtered["summary"]["rejected"] == 8

    print("PASS: multi-module filtering")

    invalid = deepcopy(extraction_result)
    invalid["candidate_count"] = 999

    try:
        topic_filter.filter(invalid)
    except ValueError:
        print("PASS: inconsistent candidate count rejected")
    else:
        raise AssertionError("Invalid candidate count accepted")

    print("\nAll M7.3.5.1 filtering tests passed.")


if __name__ == "__main__":
    run_tests()
