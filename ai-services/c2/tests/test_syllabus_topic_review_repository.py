
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)


def make_review(
    decision="pending",
    status="unverified",
    reviewer_id=None,
    reviewed_at=None,
):
    return {
        "candidate_id": "database_systems:database_normalization",
        "module_key": "database_systems",
        "candidate_name": "Database Normalization",
        "review_decision": decision,
        "verification_status": status,
        "reviewer_id": reviewer_id,
        "reviewed_at": reviewed_at,
        "review_notes": "",
        "sources": [
            {
                "filename": "lecture1.pdf",
                "line_number": 10,
            }
        ],
    }


def expect_value_error(action):
    try:
        action()
    except ValueError:
        return

    raise AssertionError("Expected ValueError was not raised")


def run_tests():
    print("\n--- M7.3.5.3.3 REVIEW REPOSITORY UNIT TESTS ---")

    # Temporary directory prevents test data from affecting
    # real review decisions or generated review reports.
    with tempfile.TemporaryDirectory() as directory:
        storage_path = Path(directory) / "review_decisions.json"

        repository = SyllabusTopicReviewRepository(
            storage_path=storage_path
        )

        # TEST 1: New repository starts empty.
        assert repository.get_review("unknown") is None
        assert repository.list_reviews() == []
        assert repository.get_history() == []

        print("PASS: empty repository initialization")

        # TEST 2: Save a pending review.
        pending = make_review()
        original = copy.deepcopy(pending)

        saved = repository.save_review(pending)

        assert saved == pending
        assert pending == original
        assert storage_path.exists()

        print("PASS: pending review saved without input mutation")

        # TEST 3: Retrieve saved review.
        loaded = repository.get_review(pending["candidate_id"])

        assert loaded == pending

        print("PASS: saved review retrieved")

        # TEST 4: Repository creates audit history.
        history = repository.get_history(pending["candidate_id"])

        assert len(history) == 1
        assert history[0]["previous_decision"] is None
        assert history[0]["new_decision"] == "pending"
        assert history[0]["review_record"] == pending

        print("PASS: initial audit history recorded")

        # TEST 5: Identical save does not duplicate history.
        repository.save_review(copy.deepcopy(pending))

        assert len(repository.get_history()) == 1

        print("PASS: duplicate saves do not duplicate history")

        # TEST 6: Approve candidate with reviewer metadata.
        approved = make_review(
            decision="approved",
            status="verified",
            reviewer_id="lecturer_001",
            reviewed_at="2026-10-16T10:00:00+05:30",
        )

        repository.save_review(approved)

        assert repository.get_review(
            approved["candidate_id"]
        )["verification_status"] == "verified"

        history = repository.get_history(approved["candidate_id"])

        assert len(history) == 2
        assert history[-1]["previous_decision"] == "pending"
        assert history[-1]["new_decision"] == "approved"
        assert history[-1]["reviewer_id"] == "lecturer_001"

        print("PASS: approved decision and history preserved")

        # TEST 7: Reject a different candidate.
        rejected = make_review(
            decision="rejected",
            status="rejected",
            reviewer_id="lecturer_002",
            reviewed_at="2026-10-16T11:00:00+05:30",
        )
        rejected["candidate_id"] = "database_systems:unrelated_text"
        rejected["candidate_name"] = "Unrelated Text"

        repository.save_review(rejected)

        assert repository.get_review(
            rejected["candidate_id"]
        )["verification_status"] == "rejected"

        print("PASS: rejected review stored")

        # TEST 8: Filter reviews by module.
        architecture = make_review()
        architecture["candidate_id"] = (
            "software_architecture:quality_attributes"
        )
        architecture["module_key"] = "software_architecture"
        architecture["candidate_name"] = "Quality Attributes"

        repository.save_review(architecture)

        assert len(repository.list_reviews()) == 3
        assert len(
            repository.list_reviews("database_systems")
        ) == 2
        assert len(
            repository.list_reviews("software_architecture")
        ) == 1

        print("PASS: module-specific review retrieval")

        # TEST 9: Invalid review is rejected.
        invalid = make_review(
            decision="approved",
            status="verified",
        )

        expect_value_error(
            lambda: repository.save_review(invalid)
        )

        print("PASS: invalid review rejected")

        # TEST 10: Candidate identity cannot change.
        modified_name = copy.deepcopy(approved)
        modified_name["candidate_name"] = "Different Topic"

        expect_value_error(
            lambda: repository.save_review(modified_name)
        )

        print("PASS: candidate identity protected")

        # TEST 11: Source evidence cannot change.
        modified_sources = copy.deepcopy(approved)
        modified_sources["sources"][0]["line_number"] = 999

        expect_value_error(
            lambda: repository.save_review(modified_sources)
        )

        print("PASS: source evidence protected")

        # TEST 12: Returned objects are independent.
        retrieved = repository.get_review(approved["candidate_id"])
        retrieved["candidate_name"] = "Modified Locally"

        assert repository.get_review(
            approved["candidate_id"]
        )["candidate_name"] == "Database Normalization"

        listed = repository.list_reviews()
        listed[0]["candidate_name"] = "Modified List"

        assert all(
            review["candidate_name"] != "Modified List"
            for review in repository.list_reviews()
        )

        print("PASS: returned records are independent copies")

        # TEST 13: Data survives repository reinitialization.
        second_repository = SyllabusTopicReviewRepository(
            storage_path=storage_path
        )

        assert len(second_repository.list_reviews()) == 3
        assert len(second_repository.get_history()) == 4

        print("PASS: review decisions persist across instances")

        # TEST 14: Saved JSON structure is valid.
        with storage_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        assert data["schema_version"] == "1.0"
        assert isinstance(data["reviews"], dict)
        assert isinstance(data["history"], list)
        assert len(data["reviews"]) == 3
        assert len(data["history"]) == 4

        print("PASS: repository JSON structure validated")

        # TEST 15: Invalid repository structure is rejected.
        invalid_path = Path(directory) / "invalid_repository.json"
        invalid_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "reviews": [],
                    "history": {},
                }
            ),
            encoding="utf-8",
        )

        invalid_repository = SyllabusTopicReviewRepository(
            storage_path=invalid_path
        )

        expect_value_error(
            lambda: invalid_repository.list_reviews()
        )

        print("PASS: malformed repository structure rejected")

    print(
        "\nAll M7.3.5.3.3 review repository unit tests passed."
    )


if __name__ == "__main__":
    run_tests()
