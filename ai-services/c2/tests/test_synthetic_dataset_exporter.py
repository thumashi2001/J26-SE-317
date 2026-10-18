
"""Tests for M11.2.4 synthetic dataset validation and export."""

import json
from copy import deepcopy

import pytest

from services.synthetic_dataset_exporter import (
    SyntheticDatasetExporter,
)
from services.synthetic_paper_builder import (
    SyntheticPaperBuilder,
)
from tests.test_synthetic_paper_builder import (
    fixture_batch,
    fixture_structure,
)


def sample_paper():
    return SyntheticPaperBuilder().build(
        fixture_batch(),
        fixture_structure(),
        seed=42,
    )


def test_valid_paper_passes_validation(tmp_path):
    exporter = SyntheticDatasetExporter(tmp_path)

    result = exporter.validate(sample_paper())

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["calculated_total_marks"] == 100
    assert result["unique_question_count"] == 12


def test_export_creates_json_file(tmp_path):
    exporter = SyntheticDatasetExporter(tmp_path)
    paper = sample_paper()

    result = exporter.export(paper)

    assert result["exported"] is True

    with open(
        result["file_path"],
        encoding="utf-8",
    ) as file:
        saved = json.load(file)

    assert saved == paper
    assert saved["release_status"] == "not_approved"


def test_export_does_not_overwrite(tmp_path):
    exporter = SyntheticDatasetExporter(tmp_path)
    paper = sample_paper()

    exporter.export(paper)

    with pytest.raises(FileExistsError):
        exporter.export(paper)


def test_rejects_incorrect_paper_marks(tmp_path):
    paper = sample_paper()
    paper["total_marks"] = 90

    result = SyntheticDatasetExporter(
        tmp_path
    ).validate(paper)

    assert result["valid"] is False
    assert "Paper total marks mismatch" in result["errors"]


def test_rejects_duplicate_question_ids(tmp_path):
    paper = sample_paper()

    first = paper["questions"][0]["subquestions"][0]
    second = paper["questions"][0]["subquestions"][1]

    second["question"]["question_id"] = (
        first["question"]["question_id"]
    )

    result = SyntheticDatasetExporter(
        tmp_path
    ).validate(paper)

    assert result["valid"] is False
    assert "Missing or duplicate question ID" in (
        result["errors"]
    )


def test_rejects_non_synthetic_source(tmp_path):
    paper = sample_paper()
    paper["source_type"] = "authentic"

    with pytest.raises(
        ValueError,
        match="validation failed",
    ):
        SyntheticDatasetExporter(tmp_path).export(paper)

    assert list(tmp_path.iterdir()) == []


def test_rejects_approved_paper(tmp_path):
    paper = sample_paper()
    paper["release_status"] = "approved"

    result = SyntheticDatasetExporter(
        tmp_path
    ).validate(paper)

    assert result["valid"] is False


def test_rejects_production_mode(tmp_path):
    paper = sample_paper()
    paper["generation_mode"] = "production"

    result = SyntheticDatasetExporter(
        tmp_path
    ).validate(paper)

    assert result["valid"] is False


def test_rejects_question_module_mismatch(tmp_path):
    paper = sample_paper()

    paper["questions"][0]["subquestions"][0][
        "question"
    ]["module_key"] = "software_architecture"

    result = SyntheticDatasetExporter(
        tmp_path
    ).validate(paper)

    assert result["valid"] is False
    assert "Question module mismatch" in result["errors"]


def test_export_does_not_modify_input(tmp_path):
    paper = sample_paper()
    original = deepcopy(paper)

    SyntheticDatasetExporter(tmp_path).export(paper)

    assert paper == original
