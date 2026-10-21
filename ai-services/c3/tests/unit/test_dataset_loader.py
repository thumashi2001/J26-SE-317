"""
Unit tests for C3 synthetic dataset loader utility.
"""

import pytest
from datasets.loader import (
    get_dataset_summary,
    get_question_bundle,
    get_synthetic_dataset_dir,
    load_controlled_answers,
    load_manifest,
    load_question_bank,
    load_replacement_audit,
    load_rubric_criteria,
    parse_concepts,
    parse_marks,
)


def test_synthetic_dir_exists():
    path = get_synthetic_dataset_dir()
    assert path.exists()
    assert path.is_dir()


def test_load_manifest():
    manifest = load_manifest()
    assert manifest["dataset_version"] == "C3-Phase3-v5-FINAL"
    assert manifest["questions"] == 167
    assert manifest["answers"] == 1002
    assert manifest["variants_per_question"] == 6
    assert manifest["train_questions"] == 117
    assert manifest["validation_questions"] == 25
    assert manifest["test_questions"] == 25
    assert manifest["expert_validation"] is False


def test_load_question_bank_all():
    qb = load_question_bank()
    assert len(qb) == 167
    sample = qb[0]
    assert "question_id" in sample
    assert "question_text" in sample
    assert "reference_answer" in sample
    assert "expected_concepts_parsed" in sample
    assert isinstance(sample["expected_concepts_parsed"], list)


def test_load_question_bank_splits():
    train_qb = load_question_bank(split="train")
    val_qb = load_question_bank(split="validation")
    test_qb = load_question_bank(split="test")
    assert len(train_qb) == 117
    assert len(val_qb) == 25
    assert len(test_qb) == 25
    assert len(train_qb) + len(val_qb) + len(test_qb) == 167


def test_load_controlled_answers_all():
    ca = load_controlled_answers()
    assert len(ca) == 1002
    sample = ca[0]
    assert "answer_id" in sample
    assert "student_answer" in sample
    assert "answer_quality" in sample
    assert "expected_mark" in sample
    assert "demonstrated_concepts_parsed" in sample


def test_load_controlled_answers_filtering():
    train_ca = load_controlled_answers(split="train")
    assert len(train_ca) == 702

    full_ca = load_controlled_answers(quality="FULL")
    assert len(full_ca) == 167

    mostly_ca = load_controlled_answers(quality="MOSTLY_CORRECT")
    assert len(mostly_ca) == 167

    partial_ca = load_controlled_answers(quality="PARTIAL")
    assert len(partial_ca) == 167

    missing_ca = load_controlled_answers(quality="MISSING_CONCEPT")
    assert len(missing_ca) == 167

    misconception_ca = load_controlled_answers(quality="MISCONCEPTION")
    assert len(misconception_ca) == 167

    irrelevant_ca = load_controlled_answers(quality="IRRELEVANT")
    assert len(irrelevant_ca) == 167


def test_load_rubric_criteria():
    rc = load_rubric_criteria()
    assert len(rc) == 230


def test_load_replacement_audit():
    ra = load_replacement_audit()
    assert len(ra) == 63


def test_get_dataset_summary():
    summary = get_dataset_summary()
    assert summary["dataset_version"] == "C3-Phase3-v5-FINAL"
    assert summary["total_questions"] == 167
    assert summary["total_answers"] == 1002
    assert summary["question_splits"] == {"train": 117, "validation": 25, "test": 25}
    assert summary["answer_splits"] == {"train": 702, "validation": 150, "test": 150}
    assert summary["expert_validation_claimed"] is False


def test_get_question_bundle():
    bundle = get_question_bundle("PP-SE3040-001")
    assert bundle is not None
    assert bundle["question"]["question_id"] == "PP-SE3040-001"
    assert len(bundle["controlled_answers"]) == 6
    qualities = {a["answer_quality"] for a in bundle["controlled_answers"]}
    assert qualities == {"FULL", "MOSTLY_CORRECT", "PARTIAL", "MISSING_CONCEPT", "MISCONCEPTION", "IRRELEVANT"}


def test_parse_concepts_json_and_semicolon():
    json_str = '["Software Engineering", "REST"]'
    assert parse_concepts(json_str) == ["Software Engineering", "REST"]

    semi_str = "HDFS; MapReduce; Fault tolerance"
    assert parse_concepts(semi_str) == ["HDFS", "MapReduce", "Fault tolerance"]

    assert parse_concepts("") == []
    assert parse_concepts("nan") == []


def test_parse_marks_json_and_comma():
    json_marks = '[{"criterion_id": "C01", "mark": 10.0}]'
    assert parse_marks(json_marks) == [{"criterion_id": "C01", "mark": 10.0}]

    comma_marks = "5, 5"
    assert parse_marks(comma_marks) == [{"mark": 5.0}, {"mark": 5.0}]

    single_mark = "10.0"
    assert parse_marks(single_mark) == [{"mark": 10.0}]
