
import pytest

from services.verified_training_dataset import (
    VerifiedTrainingDatasetBuilder,
)


def make_question(
    question_id="Q1",
    source_type="authentic",
    paper_id="P1",
):
    return {
        "question_id": question_id,
        "question_text": "Explain database indexing.",
        "paper_id": paper_id,
        "source_type": source_type,
    }


def make_classification(
    question_id="Q1",
    status="verified",
    topic_id="database_indexing",
    valid=True,
):
    return {
        "question_id": question_id,
        "valid": valid,
        "classification": {
            "question_id": question_id,
            "module_key": "database_systems",
            "topic_id": topic_id,
            "classification_method": "manual",
            "verification_status": status,
        },
    }


def test_accepts_verified_authentic_question():
    result = VerifiedTrainingDatasetBuilder().build(
        [make_question()],
        [make_classification()],
    )

    assert result["record_count"] == 1
    assert result["source_paper_count"] == 1
    assert result["topic_count"] == 1
    assert result["records"][0]["topic_id"] == (
        "database_indexing"
    )


def test_excludes_unverified_classification():
    result = VerifiedTrainingDatasetBuilder().build(
        [make_question()],
        [make_classification(status="unverified")],
    )

    assert result["record_count"] == 0
    assert result["excluded"]["not_verified"] == 1


def test_excludes_synthetic_question():
    result = VerifiedTrainingDatasetBuilder().build(
        [make_question(source_type="synthetic")],
        [make_classification()],
    )

    assert result["record_count"] == 0
    assert result["excluded"]["non_authentic_source"] == 1


def test_excludes_missing_topic():
    result = VerifiedTrainingDatasetBuilder().build(
        [make_question()],
        [make_classification(topic_id=None)],
    )

    assert result["record_count"] == 0
    assert result["excluded"]["missing_topic_label"] == 1


def test_excludes_invalid_classification():
    result = VerifiedTrainingDatasetBuilder().build(
        [make_question()],
        [make_classification(valid=False)],
    )

    assert result["record_count"] == 0
    assert result["excluded"][
        "invalid_classification_record"
    ] == 1


def test_excludes_missing_question():
    result = VerifiedTrainingDatasetBuilder().build(
        [],
        [make_classification()],
    )

    assert result["record_count"] == 0
    assert result["excluded"]["question_not_found"] == 1


def test_rejects_duplicate_question_ids():
    with pytest.raises(ValueError, match="Duplicate question ID"):
        VerifiedTrainingDatasetBuilder().build(
            [make_question(), make_question()],
            [],
        )


def test_rejects_duplicate_classification_ids():
    with pytest.raises(ValueError, match="Duplicate classification"):
        VerifiedTrainingDatasetBuilder().build(
            [make_question()],
            [
                make_classification(),
                make_classification(),
            ],
        )


def test_empty_dataset():
    result = VerifiedTrainingDatasetBuilder().build([], [])

    assert result["record_count"] == 0
    assert result["source_paper_count"] == 0
    assert result["topic_count"] == 0
    assert result["records"] == []


def test_deterministic_record_order():
    questions = [
        make_question("Q2"),
        make_question("Q1"),
    ]

    classifications = [
        make_classification("Q2"),
        make_classification("Q1"),
    ]

    result = VerifiedTrainingDatasetBuilder().build(
        questions,
        classifications,
    )

    assert [
        record["question_id"]
        for record in result["records"]
    ] == ["Q1", "Q2"]
