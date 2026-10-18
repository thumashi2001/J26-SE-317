
"""Tests for M11.2.3 synthetic paper assembly."""

import pytest

from services.synthetic_paper_builder import (
    SyntheticPaperBuilder,
)


def fixture_structure():
    return {
        "module_key": "database_systems",
        "module_name": "Database Systems",
        "total_marks": 100,
        "questions": [
            {
                "number": 1,
                "total_marks": 25,
                "subquestion_marks": [5, 10, 10],
            },
            {
                "number": 2,
                "total_marks": 25,
                "subquestion_marks": [5, 10, 10],
            },
            {
                "number": 3,
                "total_marks": 25,
                "subquestion_marks": [5, 10, 10],
            },
            {
                "number": 4,
                "total_marks": 25,
                "subquestion_marks": [5, 10, 10],
            },
        ],
    }


def fixture_batch():
    questions = []

    # Four 5-mark and eight 10-mark questions.
    marks_list = [5] * 4 + [10] * 8

    for index, marks in enumerate(marks_list, start=1):
        questions.append({
            "question_id": f"SYN-TEST-Q{index}",
            "module_key": "database_systems",
            "module_code": "IT3020",
            "module_name": "Database Systems",
            "question_text": (
                f"Development-only question number {index} "
                "about a distinct database scenario."
            ),
            "marks": marks,
            "source_type": "synthetic",
            "verification_status": "unverified",
            "human_review_status": "pending",
            "generation_provenance": {
                "generator": "test_fixture",
                "sequence": index,
            },
        })

    return {
        "dataset_type": "synthetic_question_drafts",
        "module_key": "database_systems",
        "generation_mode": "development_fixture",
        "batch_id": "test-batch-001",
        "question_count": len(questions),
        "release_status": "not_approved",
        "questions": questions,
    }


def test_builds_complete_paper():
    paper = SyntheticPaperBuilder().build(
        fixture_batch(),
        fixture_structure(),
    )

    assert paper["total_marks"] == 100
    assert paper["main_question_count"] == 4
    assert len(paper["questions"]) == 4


def test_each_main_question_has_correct_marks():
    paper = SyntheticPaperBuilder().build(
        fixture_batch(),
        fixture_structure(),
    )

    for main in paper["questions"]:
        assert main["total_marks"] == 25
        assert sum(
            sub["marks"]
            for sub in main["subquestions"]
        ) == 25


def test_paper_has_unique_question_ids():
    paper = SyntheticPaperBuilder().build(
        fixture_batch(),
        fixture_structure(),
    )

    ids = [
        sub["question"]["question_id"]
        for main in paper["questions"]
        for sub in main["subquestions"]
    ]

    assert len(ids) == 12
    assert len(ids) == len(set(ids))


def test_paper_assembly_is_reproducible():
    builder = SyntheticPaperBuilder()

    first = builder.build(
        fixture_batch(),
        fixture_structure(),
        seed=123,
    )

    second = builder.build(
        fixture_batch(),
        fixture_structure(),
        seed=123,
    )

    assert first == second


def test_paper_remains_unapproved():
    paper = SyntheticPaperBuilder().build(
        fixture_batch(),
        fixture_structure(),
    )

    assert paper["source_type"] == "synthetic"
    assert paper["release_status"] == "not_approved"
    assert paper["human_review_status"] == "pending"


def test_rejects_insufficient_marks_pool():
    batch = fixture_batch()

    batch["questions"] = [
        question
        for question in batch["questions"]
        if question["marks"] == 5
    ]

    batch["question_count"] = len(batch["questions"])

    with pytest.raises(
        ValueError,
        match="Insufficient synthetic questions",
    ):
        SyntheticPaperBuilder().build(
            batch,
            fixture_structure(),
        )


def test_rejects_invalid_paper_total():
    structure = fixture_structure()
    structure["total_marks"] = 90

    with pytest.raises(
        ValueError,
        match="Paper total marks",
    ):
        SyntheticPaperBuilder().build(
            fixture_batch(),
            structure,
        )


def test_rejects_duplicate_question_ids():
    batch = fixture_batch()

    batch["questions"][1]["question_id"] = (
        batch["questions"][0]["question_id"]
    )

    with pytest.raises(
        ValueError,
        match="duplicate question ID",
    ):
        SyntheticPaperBuilder().build(
            batch,
            fixture_structure(),
        )


def test_production_assembly_is_blocked():
    with pytest.raises(
        ValueError,
        match="Production paper assembly blocked",
    ):
        SyntheticPaperBuilder().build(
            fixture_batch(),
            fixture_structure(),
            mode="production",
        )


def test_input_batch_is_not_modified():
    batch = fixture_batch()
    original = fixture_batch()

    SyntheticPaperBuilder().build(
        batch,
        fixture_structure(),
    )

    assert batch == original
