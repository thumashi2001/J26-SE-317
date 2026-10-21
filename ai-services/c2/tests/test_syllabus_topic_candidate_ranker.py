
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_candidate_ranker import (
    SyllabusTopicCandidateRanker,
)


def make_candidate(name, sources, module_key="database_systems"):
    return {
        "module_key": module_key,
        "candidate_name": name,
        "verification_status": "unverified",
        "extraction_method": "rule_based",
        "sources": sources,
    }


def make_source(filename, line_number):
    return {
        "filename": filename,
        "line_number": line_number,
    }


def assert_raises_value_error(callback):
    try:
        callback()
    except ValueError:
        return

    raise AssertionError("Expected ValueError was not raised")


def test_administrative_filter_safety():
    ranker = SyllabusTopicCandidateRanker()

    legitimate_candidates = [
        "MS Project Features",
        "MS Project provides comprehensive tools for project scheduling",
        "by joining each row of the nested table with the row that",
        "by creating temporary queues and topics",
        "by default a subscriber gets only messages published on a",
        "by Don Norman and Jakob Nielsen",
        "Security Testing",
        "Quality Attributes",
        "PMBOK Process",
        "Database Normalization",
    ]

    for name in legitimate_candidates:
        assert not ranker.is_administrative_candidate(name), name

    administrative_candidates = [
        "Subject Name",
        "Semester 2, 2025",
        "SLIIT - Faculty of Computing",
        "Department of Software Engineering",
        "References & Further reading",
        "Acknowledgments",
        "Thank you …",
        "This Lecture…",
        "This Week",
        "Example",
        "Mr. Suresh Fernando",
        "by Chathura R De Silva",
    ]

    for name in administrative_candidates:
        assert ranker.is_administrative_candidate(name), name

    print("PASS: administrative filter safety")


def test_administrative_exclusion_and_preservation():
    ranker = SyllabusTopicCandidateRanker()

    module_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate(
                "Database Normalization",
                [make_source("lecture1.pdf", 10)],
            ),
            make_candidate(
                "Subject Name",
                [make_source("lecture1.pdf", 1)],
            ),
            make_candidate(
                "MS Project Features",
                [make_source("lecture2.pdf", 20)],
            ),
        ],
    }

    original = copy.deepcopy(module_data)
    result = ranker.rank_module(module_data)

    assert result["summary"]["input_candidate_count"] == 3
    assert result["summary"]["ranked_candidate_count"] == 2
    assert result["summary"]["excluded_candidate_count"] == 1
    assert result["summary"]["merged_duplicate_count"] == 0

    ranked_names = {
        candidate["candidate_name"]
        for candidate in result["candidates"]
    }

    assert "Database Normalization" in ranked_names
    assert "MS Project Features" in ranked_names
    assert "Subject Name" not in ranked_names

    excluded = result["excluded_candidates"]

    assert len(excluded) == 1
    assert excluded[0]["candidate_name"] == "Subject Name"
    assert excluded[0]["verification_status"] == "unverified"
    assert excluded[0]["sources"] == [
        make_source("lecture1.pdf", 1)
    ]

    assert module_data == original

    print("PASS: administrative exclusion and evidence preservation")


def test_invalid_excluded_candidate_source():
    ranker = SyllabusTopicCandidateRanker()

    invalid_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate(
                "Subject Name",
                [make_source("lecture1.pdf", 0)],
            ),
        ],
    }

    assert_raises_value_error(
        lambda: ranker.rank_module(invalid_data)
    )

    print("PASS: excluded candidate source validation")


def test_ranking_count_consistency():
    ranker = SyllabusTopicCandidateRanker()

    module_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate(
                "Database Normalization",
                [make_source("lecture1.pdf", 10)],
            ),
            make_candidate(
                "database normalization",
                [make_source("lecture2.pdf", 20)],
            ),
            make_candidate(
                "Subject Name",
                [make_source("lecture1.pdf", 1)],
            ),
            make_candidate(
                "SQL Joins",
                [make_source("lecture3.pdf", 30)],
            ),
        ],
    }

    result = ranker.rank_module(module_data)
    summary = result["summary"]

    assert summary["input_candidate_count"] == 4
    assert summary["ranked_candidate_count"] == 2
    assert summary["excluded_candidate_count"] == 1
    assert summary["merged_duplicate_count"] == 1

    assert (
        summary["input_candidate_count"]
        == summary["ranked_candidate_count"]
        + summary["excluded_candidate_count"]
        + summary["merged_duplicate_count"]
    )

    print("PASS: ranking count consistency")


def run_tests():
    print("\n--- M7.3.5.2.3c RANKING UNIT TESTS ---")

    ranker = SyllabusTopicCandidateRanker()

    # TEST 1: Ranking score boundaries.
    for name in [
        "Database Normalization",
        "SQL",
        "B+ Tree",
        "Distributed Transactions",
        "A long explanatory sentence describing how something works",
    ]:
        score = ranker.heading_quality_score(name)
        assert 0 <= score <= 40

    assert ranker.occurrence_score(0) == 0
    assert ranker.document_coverage_score(0) == 0
    assert ranker.occurrence_score(100) <= 30
    assert ranker.document_coverage_score(100) <= 30

    print("PASS: ranking score boundaries")

    # TEST 2: Duplicate merging and source preservation.
    module_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate(
                "Database Normalization",
                [
                    make_source("lecture1.pdf", 10),
                    make_source("lecture2.pdf", 20),
                ],
            ),
            make_candidate(
                "database normalization",
                [
                    make_source("lecture3.pdf", 30),
                ],
            ),
        ],
    }

    original = copy.deepcopy(module_data)
    result = ranker.rank_module(module_data)

    assert result["summary"]["input_candidate_count"] == 2
    assert result["summary"]["ranked_candidate_count"] == 1
    assert result["summary"]["excluded_candidate_count"] == 0
    assert result["summary"]["merged_duplicate_count"] == 1

    candidate = result["candidates"][0]

    assert candidate["ranking_score"] == 87
    assert candidate["occurrence_count"] == 3
    assert candidate["document_count"] == 3
    assert len(candidate["sources"]) == 3
    assert candidate["verification_status"] == "unverified"

    print("PASS: duplicate merging and source preservation")

    # TEST 3: Input data must remain unchanged.
    assert module_data == original

    print("PASS: original candidate data unchanged")

    # TEST 4: Duplicate source references must be removed.
    duplicate_source_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate(
                "SQL Joins",
                [
                    make_source("lecture1.pdf", 15),
                    make_source("lecture1.pdf", 15),
                    make_source("lecture1.pdf", 20),
                ],
            ),
        ],
    }

    result = ranker.rank_module(duplicate_source_data)
    candidate = result["candidates"][0]

    assert candidate["occurrence_count"] == 2
    assert candidate["document_count"] == 1
    assert len(candidate["sources"]) == 2

    print("PASS: duplicate source references removed")

    # TEST 5: Higher evidence scores should rank first.
    ranking_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate(
                "Database Indexing",
                [make_source("lecture1.pdf", 10)],
            ),
            make_candidate(
                "Database Normalization",
                [
                    make_source("lecture1.pdf", 20),
                    make_source("lecture2.pdf", 30),
                    make_source("lecture3.pdf", 40),
                ],
            ),
        ],
    }

    result = ranker.rank_module(ranking_data)

    assert result["candidates"][0]["candidate_name"] == (
        "Database Normalization"
    )
    assert result["candidates"][0]["rank"] == 1
    assert result["candidates"][1]["rank"] == 2

    print("PASS: evidence-based ranking order")

    # TEST 6: Verified candidates must be rejected.
    invalid_data = {
        "module_key": "database_systems",
        "candidates": [
            {
                **make_candidate(
                    "Database Normalization",
                    [make_source("lecture1.pdf", 10)],
                ),
                "verification_status": "verified",
            },
        ],
    }

    assert_raises_value_error(
        lambda: ranker.rank_module(invalid_data)
    )

    print("PASS: verification safeguards")

    # TEST 7: Module mismatches must be rejected.
    mismatch_data = {
        "module_key": "database_systems",
        "candidates": [
            make_candidate(
                "Software Architecture",
                [make_source("lecture1.pdf", 10)],
                module_key="software_architecture",
            ),
        ],
    }

    assert_raises_value_error(
        lambda: ranker.rank_module(mismatch_data)
    )

    print("PASS: module consistency validation")

    # TEST 8: Multiple modules ranked independently.
    all_data = {
        "schema_version": "1.0",
        "modules": {
            "database_systems": ranking_data,
            "software_architecture": {
                "module_key": "software_architecture",
                "candidates": [
                    make_candidate(
                        "Microservices Architecture",
                        [make_source("architecture.pdf", 5)],
                        module_key="software_architecture",
                    ),
                ],
            },
        },
    }

    result = ranker.rank_all(all_data)

    assert result["summary"]["module_count"] == 2
    assert result["summary"]["input_candidate_count"] == 3
    assert result["summary"]["ranked_candidate_count"] == 3
    assert result["summary"]["excluded_candidate_count"] == 0
    assert result["summary"]["merged_duplicate_count"] == 0

    assert result["modules"]["database_systems"]["module_key"] == (
        "database_systems"
    )
    assert result["modules"]["software_architecture"]["module_key"] == (
        "software_architecture"
    )

    print("PASS: multi-module ranking")

    # TEST 9: Administrative filter false-positive protection.
    test_administrative_filter_safety()

    # TEST 10: Excluded candidates remain auditable.
    test_administrative_exclusion_and_preservation()

    # TEST 11: Invalid excluded sources are rejected.
    test_invalid_excluded_candidate_source()

    # TEST 12: Ranking counts remain consistent.
    test_ranking_count_consistency()

    print(
        "\nAll M7.3.5.2.3c ranking unit tests passed."
    )


if __name__ == "__main__":
    run_tests()
