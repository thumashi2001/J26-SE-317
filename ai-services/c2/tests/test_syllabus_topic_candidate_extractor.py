
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.syllabus_topic_candidate_extractor import (
    SyllabusTopicCandidateExtractor,
)


def run_tests():
    print("--- M7.3.4 TOPIC CANDIDATE EXTRACTION TEST ---")

    extractor = SyllabusTopicCandidateExtractor()

    documents = [
        {
            "filename": "Lecture_01.pdf",
            "text": (
                "Lecture 1 - Database Normalization\n"
                "First Normal Form\n"
                "Second Normal Form\n"
                "Introduction\n"
                "Explain why normalization is important.\n"
            ),
        },
        {
            "filename": "Lecture_02.pptx",
            "text": (
                "Database Normalization\n"
                "Third Normal Form\n"
                "References\n"
            ),
        },
    ]

    result = extractor.extract(
        module_key="database_systems",
        documents=documents,
    )

    assert result["schema_version"] == "1.0"
    print("PASS: schema version")

    assert result["module_key"] == "database_systems"
    print("PASS: module identification")

    names = {
        item["candidate_name"]
        for item in result["candidates"]
    }

    assert "Database Normalization" in names
    assert "First Normal Form" in names
    assert "Second Normal Form" in names
    assert "Third Normal Form" in names
    print("PASS: topic heading extraction")

    assert "Introduction" not in names
    assert "References" not in names
    print("PASS: generic heading filtering")

    assert (
        "Explain why normalization is important."
        not in names
    )
    print("PASS: sentence filtering")

    assert len([
        item for item in result["candidates"]
        if item["candidate_name"] == "Database Normalization"
    ]) == 1
    print("PASS: duplicate candidate merging")

    normalization = next(
        item for item in result["candidates"]
        if item["candidate_name"] == "Database Normalization"
    )

    assert len(normalization["sources"]) == 2
    print("PASS: source references preserved")

    assert all(
        item["verification_status"] == "unverified"
        for item in result["candidates"]
    )
    print("PASS: verification safeguards")

    assert result["candidate_count"] == len(result["candidates"])
    print("PASS: candidate count consistency")

    try:
        extractor.extract("", documents)
        raise AssertionError("Empty module key was accepted")
    except ValueError:
        print("PASS: invalid module rejected")

    try:
        extractor.extract("database_systems", "invalid")
        raise AssertionError("Invalid documents were accepted")
    except ValueError:
        print("PASS: invalid document collection rejected")

    print("\n--- EXTRACTION SUMMARY ---")
    print(f"Module: {result['module_key']}")
    print(f"Candidates: {result['candidate_count']}")

    for candidate in result["candidates"]:
        print(
            f"- {candidate['candidate_name']} "
            f"({len(candidate['sources'])} source(s))"
        )

    print("\nAll M7.3.4 candidate extraction tests passed.")


if __name__ == "__main__":
    run_tests()
