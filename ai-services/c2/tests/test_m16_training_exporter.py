"""Tests for M16 synthetic training export service."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from services.m16_question_generator import M16QuestionGenerator
from services.m16_training_exporter import (
    FORBIDDEN_DIRECTORIES,
    M16TrainingExporter,
)


@pytest.fixture
def dataset():
    return M16QuestionGenerator().generate(seed=42, max_per_module=100)


@pytest.fixture
def exporter():
    return M16TrainingExporter()


def test_split_deterministic(dataset, exporter):
    split1 = exporter.split(dataset, seed=42)
    split2 = exporter.split(dataset, seed=42)

    assert len(split1["train"]) == len(split2["train"])
    assert len(split1["validation"]) == len(split2["validation"])
    assert len(split1["test"]) == len(split2["test"])

    ids1_train = [q["question_id"] for q in split1["train"]]
    ids2_train = [q["question_id"] for q in split2["train"]]
    assert ids1_train == ids2_train


def test_group_aware_scenario_disjointness(dataset, exporter):
    """Crucial ML safety test: questions from the same scenario must not cross splits."""
    split = exporter.split(dataset, seed=42)

    train_scenarios = {q["scenario_group_id"] for q in split["train"]}
    val_scenarios = {q["scenario_group_id"] for q in split["validation"]}
    test_scenarios = {q["scenario_group_id"] for q in split["test"]}

    assert train_scenarios.isdisjoint(val_scenarios)
    assert train_scenarios.isdisjoint(test_scenarios)
    assert val_scenarios.isdisjoint(test_scenarios)
    assert not split["metadata"]["scenario_leakage_detected"]


def test_split_counts_and_ratios(dataset, exporter):
    split = exporter.split(
        dataset, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42
    )
    total = dataset["total_questions"]

    n_train = len(split["train"])
    n_val = len(split["validation"])
    n_test = len(split["test"])

    assert n_train + n_val + n_test == total
    assert 0.65 <= (n_train / total) <= 0.75
    assert 0.10 <= (n_val / total) <= 0.20
    assert 0.10 <= (n_test / total) <= 0.20


def test_rejects_authentic_questions(dataset, exporter):
    corrupted = deepcopy(dataset)
    corrupted["modules"][0]["questions"][0]["source_type"] = "authentic"

    with pytest.raises(ValueError, match="Non-synthetic question detected"):
        exporter.split(corrupted)


def test_rejects_verified_questions(dataset, exporter):
    corrupted = deepcopy(dataset)
    corrupted["modules"][0]["questions"][0]["verification_status"] = "verified"

    with pytest.raises(ValueError, match="Verified question detected"):
        exporter.split(corrupted)


def test_rejects_non_synthetic_dataset(dataset, exporter):
    corrupted = deepcopy(dataset)
    corrupted["source_type"] = "authentic"

    with pytest.raises(ValueError, match="synthetic"):
        exporter.split(corrupted)


def test_rejects_invalid_ratios(dataset, exporter):
    with pytest.raises(ValueError, match="must sum to 1.0"):
        exporter.split(dataset, train_ratio=0.5, val_ratio=0.2, test_ratio=0.1)

    with pytest.raises(ValueError, match="train_ratio must be positive"):
        exporter.split(dataset, train_ratio=0.0, val_ratio=0.5, test_ratio=0.5)


def test_rejects_insufficient_groups(dataset, exporter):
    reduced = deepcopy(dataset)
    # Force module to have only 1 scenario group
    for q in reduced["modules"][0]["questions"]:
        q["scenario_group_id"] = "single_scenario_group"

    with pytest.raises(ValueError, match="Insufficient independent scenario groups"):
        exporter.split(reduced)


def test_output_path_safeguards(dataset, exporter, tmp_path):
    for forbidden in FORBIDDEN_DIRECTORIES:
        with pytest.raises(ValueError, match="forbidden directory"):
            exporter.export(dataset, output_dir=forbidden)


def test_export_creates_valid_files(dataset, exporter, tmp_path):
    export_dir = tmp_path / "training_export"
    result = exporter.export(dataset, output_dir=export_dir, seed=42)

    assert export_dir.exists()
    train_file = export_dir / "train.json"
    val_file = export_dir / "validation.json"
    test_file = export_dir / "test.json"
    meta_file = export_dir / "split_metadata.json"

    assert train_file.exists()
    assert val_file.exists()
    assert test_file.exists()
    assert meta_file.exists()

    train_data = json.loads(train_file.read_text(encoding="utf-8"))
    val_data = json.loads(val_file.read_text(encoding="utf-8"))
    test_data = json.loads(test_file.read_text(encoding="utf-8"))
    meta_data = json.loads(meta_file.read_text(encoding="utf-8"))

    assert train_data["split_name"] == "train"
    assert val_data["split_name"] == "validation"
    assert test_data["split_name"] == "test"
    assert train_data["source_type"] == "synthetic"
    assert "disclaimer" in train_data
    assert meta_data["schema_version"] == "1.0"
    assert not meta_data["scenario_leakage_detected"]
    assert "leakage_risk_report" in meta_data
    assert "class_distributions" in meta_data
