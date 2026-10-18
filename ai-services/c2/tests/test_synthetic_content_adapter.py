
"""M11.3.3A integration tests."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from services.synthetic_content_adapter import (
    SyntheticContentAdapter,
)
from services.synthetic_dataset_exporter import (
    SyntheticDatasetExporter,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "synthetic_content_integration_fixture.json"
)


def fixture_structure():
    return json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )


def build(seed=42):
    return SyntheticContentAdapter().build_paper(
        fixture_structure(),
        seed=seed,
    )


def get_questions(paper):
    return [
        sub["question"]
        for main in paper["questions"]
        for sub in main["subquestions"]
    ]


def test_complete_paper_is_valid():
    result = build()
    assert result["validation"]["valid"] is True
    assert SyntheticDatasetExporter().validate(
        result["paper"]
    )["valid"] is True


def test_100_marks_and_four_main_questions():
    paper = build()["paper"]
    assert paper["total_marks"] == 100
    assert paper["main_question_count"] == 4
    assert all(
        main["total_marks"] == 25
        for main in paper["questions"]
    )


def test_eight_unique_questions():
    result = build()
    questions = get_questions(result["paper"])

    assert len(questions) == 8
    assert result["generated_question_count"] == 8
    assert result["available_content_pairs"] == 8
    assert len({
        q["question_id"] for q in questions
    }) == 8
    assert len({
        q["question_text"] for q in questions
    }) == 8


def test_question_text_uses_content_bank():
    questions = get_questions(build()["paper"])
    assert all(
        q["question_text"].startswith("Scenario: ")
        and "\nTask: " in q["question_text"]
        for q in questions
    )


def test_question_provenance():
    questions = get_questions(build()["paper"])

    assert all(
        q["generation_provenance"]["generator"]
        == "c2_synthetic_content_adapter_v1"
        for q in questions
    )
    assert all(
        q["generation_provenance"][
            "historical_reference_role"
        ] == "question_style_inspiration_only"
        for q in questions
    )


def test_all_content_remains_unapproved():
    paper = build()["paper"]
    questions = get_questions(paper)

    assert paper["release_status"] == "not_approved"
    assert paper["verification_status"] == "unverified"
    assert paper["human_review_status"] == "pending"
    assert all(
        q["source_type"] == "synthetic"
        and q["verification_status"] == "unverified"
        and q["human_review_status"] == "pending"
        for q in questions
    )


def test_deterministic_same_seed():
    assert build(42)["paper"] == build(42)["paper"]


def test_more_questions_than_pairs_rejected():
    structure = deepcopy(fixture_structure())
    structure["questions"][0]["subquestion_marks"] = [
        5, 5, 5, 10
    ]

    with pytest.raises(
        ValueError,
        match="Insufficient distinct scenario/task pairs",
    ):
        SyntheticContentAdapter().build_paper(structure)


def test_production_mode_rejected():
    with pytest.raises(
        ValueError,
        match="development-only",
    ):
        SyntheticContentAdapter().build_paper(
            fixture_structure(),
            mode="production",
        )


def test_invalid_seed_rejected():
    with pytest.raises(ValueError, match="seed"):
        SyntheticContentAdapter().build_paper(
            fixture_structure(),
            seed=True,
        )


def test_unknown_module_rejected():
    structure = deepcopy(fixture_structure())
    structure["module_key"] = "unknown_module"

    with pytest.raises(
        ValueError,
        match="No content bank",
    ):
        SyntheticContentAdapter().build_paper(structure)


def test_exact_marks_per_subquestion():
    paper = build()["paper"]

    for main in paper["questions"]:
        assert [
            sub["marks"]
            for sub in main["subquestions"]
        ] == [10, 15]
        assert all(
            sub["marks"] == sub["question"]["marks"]
            for sub in main["subquestions"]
        )
