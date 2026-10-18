
"""Tests for M12.4.1 synthetic practice preview."""

import pytest

from services.synthetic_practice_preview import (
    SyntheticPracticePreview,
)


@pytest.fixture(scope="module")
def preview():
    return SyntheticPracticePreview()


def test_eight_modules_available(preview):
    modules = preview.available_modules()

    assert len(modules) == 8
    assert len({
        item["module_key"]
        for item in modules
    }) == 8


@pytest.mark.parametrize(
    "module_key",
    [
        "application_frameworks",
        "case_studies_software_engineering",
        "database_systems",
        "distributed_systems",
        "software_architecture",
        "software_engineering_process_quality_management",
        "software_project_management",
        "user_experience_engineering",
    ],
)
def test_preview_for_each_module(preview, module_key):
    result = preview.generate(module_key, seed=42)

    assert result["module_key"] == module_key
    assert result["preview_type"] == (
        "synthetic_development_preview"
    )

    assert result["structural_valid"] is True
    assert result["diversity_valid"] is True

    assert result["question_count"] == 12
    assert result["unique_scenario_count"] == 12
    assert result["total_marks"] == 100

    assert result["paper"]["main_question_count"] == 4
    assert result["paper"]["release_status"] == "not_approved"

    assert result["academic_review_status"] == "pending"
    assert result["release_status"] == "not_approved"

    assert result["production_ready"] is False
    assert result["student_release_allowed"] is False
    assert result["authentic_past_paper"] is False
    assert result["official_exam_structure_verified"] is False


def test_generation_is_deterministic(preview):
    first = preview.generate(
        "database_systems",
        seed=42,
    )

    second = preview.generate(
        "database_systems",
        seed=42,
    )

    assert first["paper"] == second["paper"]


def test_questions_are_synthetic_and_unverified(preview):
    result = preview.generate(
        "database_systems",
        seed=42,
    )

    paper = result["paper"]

    # The generated paper contains main-question groups.
    # Validate source and review status recursively.
    def find_question_records(value):
        if isinstance(value, dict):
            if (
                value.get("source_type") == "synthetic"
                and "question_text" in value
            ):
                yield value

            for child in value.values():
                yield from find_question_records(child)

        elif isinstance(value, list):
            for child in value:
                yield from find_question_records(child)

    questions = list(find_question_records(paper))

    assert len(questions) == 12

    for question in questions:
        assert question["source_type"] == "synthetic"
        assert question["verification_status"] == "unverified"
        assert question["human_review_status"] == "pending"


def test_production_mode_is_blocked(preview):
    with pytest.raises(ValueError):
        preview.generate(
            "database_systems",
            mode="production",
        )


def test_unknown_module_is_rejected(preview):
    with pytest.raises(ValueError):
        preview.generate(
            "unknown_module",
        )


@pytest.mark.parametrize(
    "module_key",
    ["", " ", None, 123],
)
def test_invalid_module_key_is_rejected(
    preview,
    module_key,
):
    with pytest.raises(ValueError):
        preview.generate(module_key)


@pytest.mark.parametrize(
    "seed",
    [None, "42", 3.5, True],
)
def test_invalid_seed_is_rejected(preview, seed):
    with pytest.raises(ValueError):
        preview.generate(
            "database_systems",
            seed=seed,
        )


def test_preview_disclaimers_present(preview):
    result = preview.generate(
        "database_systems",
    )

    assert len(result["limitations"]) >= 3
    assert result["student_release_allowed"] is False

