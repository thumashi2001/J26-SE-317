
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)


def make_record(candidate_id, decision="approved"):
    return {
        "candidate_id": candidate_id,
        "module_key": "database_systems",
        "candidate_name": f"Test Topic {candidate_id}",
        "review_decision": decision,
        "verification_status": (
            "verified" if decision == "approved" else "rejected"
        ),
        "reviewer_id": "test_lecturer",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "review_notes": (
            "Relevant syllabus topic"
            if decision == "approved"
            else "Not part of the module syllabus"
        ),
        "sources": [
            {
                "filename": "test_lecture.pdf",
                "line_number": 1,
            }
        ],
    }


def test_first_review_is_saved(tmp_path):
    repo = SyllabusTopicReviewRepository(
        storage_path=tmp_path / "reviews.json"
    )

    record = make_record("test_topic_1")

    saved = repo.save_review(record)

    assert saved["review_decision"] == "approved"
    assert repo.get_review("test_topic_1") is not None
    assert len(repo.get_history()) == 1


def test_duplicate_review_is_rejected(tmp_path):
    repo = SyllabusTopicReviewRepository(
        storage_path=tmp_path / "reviews.json"
    )

    record = make_record("test_topic_2")

    repo.save_review(record)

    with pytest.raises(ValueError, match="already been reviewed"):
        repo.save_review(copy.deepcopy(record))

    assert len(repo.get_history()) == 1


def test_concurrent_different_candidates_preserved(tmp_path):
    repo = SyllabusTopicReviewRepository(
        storage_path=tmp_path / "reviews.json"
    )

    records = [
        make_record(f"concurrent_topic_{i}")
        for i in range(20)
    ]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(repo.save_review, records))

    assert len(results) == 20
    assert len(repo.list_reviews()) == 20
    assert len(repo.get_history()) == 20


def test_concurrent_same_candidate_only_one_succeeds(tmp_path):
    repo = SyllabusTopicReviewRepository(
        storage_path=tmp_path / "reviews.json"
    )

    records = [
        make_record("same_candidate", decision="approved"),
        make_record("same_candidate", decision="rejected"),
    ]

    def attempt_save(record):
        try:
            repo.save_review(record)
            return "saved"
        except ValueError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt_save, records))

    assert sorted(results) == ["duplicate", "saved"]
    assert len(repo.list_reviews()) == 1
    assert len(repo.get_history()) == 1
