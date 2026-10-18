
"""Tests for M11.2.5 batch generation."""

from copy import deepcopy

import pytest

from services.synthetic_batch_generator import (
    SyntheticBatchGenerator,
)
from services.synthetic_paper_builder import (
    SyntheticPaperBuilder,
)
from tests.test_synthetic_paper_builder import (
    fixture_batch,
    fixture_structure,
)


def fixture_factory(module_key, paper_index, seed):
    batch = deepcopy(fixture_batch())
    structure = deepcopy(fixture_structure())

    batch["module_key"] = module_key
    batch["batch_id"] = (
        f"development-{module_key}-{paper_index}"
    )

    structure["module_key"] = module_key
    structure["module_name"] = (
        f"Development Fixture: {module_key}"
    )

    for question in batch["questions"]:
        question["module_key"] = module_key
        question["question_id"] = (
            f"{module_key}-{paper_index}-"
            f"{question['question_id']}"
        )
        question["question_text"] = (
            f"Paper {paper_index}: "
            + question["question_text"]
        )

    return SyntheticPaperBuilder().build(
        batch,
        structure,
        seed=seed,
    )


def test_generates_multiple_papers(tmp_path):
    generator = SyntheticBatchGenerator(tmp_path)

    report = generator.generate(
        {"database_systems": 3},
        fixture_factory,
    )

    assert report["requested_papers"] == 3
    assert report["generated_papers"] == 3
    assert report["failed_attempts"] == 0


def test_generates_multiple_modules(tmp_path):
    report = SyntheticBatchGenerator(
        tmp_path
    ).generate(
        {
            "database_systems": 2,
            "software_architecture": 2,
        },
        fixture_factory,
    )

    assert report["module_count"] == 2
    assert report["generated_papers"] == 4


def test_unique_paper_ids(tmp_path):
    report = SyntheticBatchGenerator(
        tmp_path
    ).generate(
        {"database_systems": 5},
        fixture_factory,
    )

    ids = [
        paper["paper_id"]
        for module in report["modules"]
        for paper in module["papers"]
    ]

    assert len(ids) == 5
    assert len(set(ids)) == 5


def test_reproducible_batches(tmp_path):
    generator = SyntheticBatchGenerator(tmp_path)

    first = generator.generate(
        {"database_systems": 3},
        fixture_factory,
        base_seed=123,
    )

    second = generator.generate(
        {"database_systems": 3},
        fixture_factory,
        base_seed=123,
    )

    assert first == second


def test_dry_run_creates_no_files(tmp_path):
    SyntheticBatchGenerator(
        tmp_path
    ).generate(
        {"database_systems": 2},
        fixture_factory,
        export=False,
    )

    assert list(tmp_path.iterdir()) == []


def test_exports_to_module_folder(tmp_path):
    report = SyntheticBatchGenerator(
        tmp_path
    ).generate(
        {"database_systems": 2},
        fixture_factory,
        export=True,
    )

    files = list(
        (tmp_path / "database_systems").glob("*.json")
    )

    assert report["exported_papers"] == 2
    assert len(files) == 2


def test_rejects_invalid_targets(tmp_path):
    generator = SyntheticBatchGenerator(tmp_path)

    with pytest.raises(ValueError):
        generator.generate(
            {"database_systems": 0},
            fixture_factory,
        )


def test_production_mode_is_blocked(tmp_path):
    with pytest.raises(
        ValueError,
        match="development-only",
    ):
        SyntheticBatchGenerator(tmp_path).generate(
            {"database_systems": 2},
            fixture_factory,
            mode="production",
        )


def test_records_factory_failures(tmp_path):
    def broken_factory(module_key, paper_index, seed):
        raise ValueError("Fixture generation failed")

    report = SyntheticBatchGenerator(
        tmp_path
    ).generate(
        {"database_systems": 2},
        broken_factory,
    )

    assert report["generated_papers"] == 0
    assert report["failed_attempts"] == 2
    assert len(report["modules"][0]["errors"]) == 2


def test_rejects_duplicate_papers(tmp_path):
    def duplicate_factory(module_key, paper_index, seed):
        return fixture_factory(module_key, 1, 42)

    report = SyntheticBatchGenerator(
        tmp_path
    ).generate(
        {"database_systems": 2},
        duplicate_factory,
    )

    assert report["generated_papers"] == 1
    assert report["failed_attempts"] == 1
    assert "Duplicate paper ID" in (
        report["modules"][0]["errors"][0]["error"]
    )
