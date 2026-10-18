
"""Tests for M11.2.2 synthetic question generation."""

import pytest

from services.synthetic_question_generator import (
    SyntheticQuestionGenerator,
)


class FakeRules:
    pass


class FakeReadiness:
    def report(self):
        return {
            "modules": [
                {
                    "module_key": "database_systems",
                    "ready_for_generation": False,
                }
            ]
        }


def fixture_config():
    return {
        "module_key": "database_systems",
        "module_code": "IT3020",
        "module_name": "Database Systems",
        "topics": [
            "SQL Queries",
            "Database Normalization",
            "Transaction Management",
        ],
        "marks_options": [5, 10, 15],
        "question_type_distribution": {
            "explain": 1,
            "apply": 2,
            "analyze": 1,
            "evaluate": 1,
            "design": 1,
        },
        "difficulty_distribution": {
            "easy": 1,
            "medium": 2,
            "hard": 1,
        },
        "blooms_taxonomy_distribution": {
            "understand": 1,
            "apply": 2,
            "analyze": 1,
            "evaluate": 1,
            "create": 1,
        },
    }


def generator():
    return SyntheticQuestionGenerator(
        rules=FakeRules(),
        readiness=FakeReadiness(),
    )


def test_generates_requested_number_of_questions():
    result = generator().generate(
        fixture_config(),
        count=10,
        mode="development_fixture",
    )

    assert result["question_count"] == 10
    assert len(result["questions"]) == 10


def test_generation_is_reproducible():
    first = generator().generate(
        fixture_config(),
        count=8,
        seed=123,
        mode="development_fixture",
    )

    second = generator().generate(
        fixture_config(),
        count=8,
        seed=123,
        mode="development_fixture",
    )

    assert first == second



def test_question_ids_are_unique():
    result = generator().generate(
        fixture_config(),
        count=15,
        seed=42,
        mode="development_fixture",
    )

    ids = [
        question["question_id"]
        for question in result["questions"]
    ]

    texts = [
        question["question_text"]
        for question in result["questions"]
    ]

    assert result["question_count"] == 15
    assert len(ids) == len(set(ids))
    assert len(texts) == len(set(texts))

def test_generated_questions_have_synthetic_provenance():
    result = generator().generate(
        fixture_config(),
        count=5,
        mode="development_fixture",
    )

    for question in result["questions"]:
        assert question["source_type"] == "synthetic"
        assert question["human_review_status"] == "pending"
        assert question["verification_status"] == "unverified"
        assert question["generation_provenance"]["seed"] == 42
        assert question["marks"] > 0

    assert result["release_status"] == "not_approved"


def test_production_generation_is_blocked():
    with pytest.raises(
        ValueError,
        match="Production generation blocked",
    ):
        generator().generate(
            fixture_config(),
            count=5,
            mode="production",
        )


def test_invalid_marks_are_rejected():
    config = fixture_config()
    config["marks_options"] = [0, -5]

    with pytest.raises(ValueError):
        generator().generate(
            config,
            count=5,
            mode="development_fixture",
        )


def test_invalid_question_type_is_rejected():
    config = fixture_config()
    config["question_type_distribution"] = {
        "unsupported_type": 1
    }

    with pytest.raises(
        ValueError,
        match="Unsupported question types",
    ):
        generator().generate(
            config,
            count=5,
            mode="development_fixture",
        )

def test_question_texts_are_unique():
    result = generator().generate(
        fixture_config(),
        count=10,
        seed=42,
        mode="development_fixture",
    )

    texts = [
        question["question_text"]
        for question in result["questions"]
    ]

    assert len(texts) == len(set(texts))


def test_question_types_match_bloom_levels():
    expected = {
        "explain": "understand",
        "apply": "apply",
        "analyze": "analyze",
        "evaluate": "evaluate",
        "design": "create",
    }

    result = generator().generate(
        fixture_config(),
        count=10,
        mode="development_fixture",
    )

    for question in result["questions"]:
        assert question["bloom_level"] == expected[
            question["question_type"]
        ]


def test_rejects_more_questions_than_unique_templates():
    with pytest.raises(
        ValueError,
        match="exceeds available unique",
    ):
        generator().generate(
            fixture_config(),
            count=16,
            mode="development_fixture",
        )