"""Tests for M16 synthetic dataset validation."""

from copy import deepcopy

import pytest

from services.m16_dataset_validator import M16DatasetValidator
from services.m16_question_generator import M16QuestionGenerator


@pytest.fixture
def dataset():
    return M16QuestionGenerator().generate(seed=42, max_per_module=100)


@pytest.fixture
def validator():
    return M16DatasetValidator()


def test_valid_generated_dataset(dataset, validator):
    report = validator.validate(dataset)

    assert report["valid"]
    assert report["structural_validity"]
    assert not report["educational_quality_verified"]
    assert report["error_count"] == 0
    assert report["question_count"] == 800
    assert report["module_count"] == 8
    assert not report["production_ready"]
    assert report["near_duplicate_count"] == 0


def test_supports_module_aliases(dataset, validator):
    """Explicit module key aliases must be recognized without validation errors."""
    modified = deepcopy(dataset)
    for m in modified["modules"]:
        if m["module_key"] == "case_studies_software_engineering":
            m["module_key"] = "case_studies_in_software_engineering"
            for q in m["questions"]:
                q["module_key"] = "case_studies_in_software_engineering"

    report = validator.validate(modified)
    assert report["valid"]
    assert report["error_count"] == 0


def test_rejects_authentic_source(dataset, validator):
    modified = deepcopy(dataset)
    modified["modules"][0]["questions"][0]["source_type"] = "authentic"

    report = validator.validate(modified)

    assert not report["valid"]
    assert report["error_count"] > 0


def test_rejects_duplicate_id(dataset, validator):
    modified = deepcopy(dataset)

    questions = modified["modules"][0]["questions"]
    questions[1]["question_id"] = questions[0]["question_id"]

    report = validator.validate(modified)

    assert not report["valid"]
    assert any(
        "Duplicate question ID" in item["message"]
        for item in report["errors"]
    )


def test_rejects_duplicate_text(dataset, validator):
    modified = deepcopy(dataset)

    questions = modified["modules"][0]["questions"]
    questions[1]["question_text"] = questions[0]["question_text"]

    report = validator.validate(modified)

    assert not report["valid"]
    assert any(
        "Duplicate question text" in item["message"]
        for item in report["errors"]
    )


def test_detects_near_duplicate_text(dataset, validator):
    modified = deepcopy(dataset)

    questions = modified["modules"][0]["questions"]
    # Change just 1 word at the very end to create a near-duplicate (> 88% similarity)
    original_text = questions[0]["question_text"]
    questions[1]["question_text"] = original_text + " please."

    report = validator.validate(modified)

    assert report["near_duplicate_count"] > 0
    assert any(
        "Near-duplicate question detected" in item["message"]
        for item in report["warnings"]
    )


def test_rejects_unknown_topic(dataset, validator):
    modified = deepcopy(dataset)
    modified["modules"][0]["questions"][0]["topic"] = "Invented Syllabus Topic"

    report = validator.validate(modified)

    assert not report["valid"]


def test_rejects_verified_status(dataset, validator):
    modified = deepcopy(dataset)
    modified["modules"][0]["questions"][0]["verification_status"] = "verified"

    report = validator.validate(modified)

    assert not report["valid"]


def test_missing_marks_are_warnings(dataset, validator):
    report = validator.validate(dataset)

    assert report["valid"]
    assert report["warning_count"] > 0
    assert any(
        "Marks not yet assigned" in item["message"]
        for item in report["warnings"]
    )


def test_rejects_invalid_marks(dataset, validator):
    modified = deepcopy(dataset)
    modified["modules"][0]["questions"][0]["marks"] = -5

    report = validator.validate(modified)

    assert not report["valid"]


def test_rejects_question_module_mismatch(dataset, validator):
    modified = deepcopy(dataset)
    modified["modules"][0]["questions"][0]["module_key"] = "another_module"

    report = validator.validate(modified)

    assert not report["valid"]
