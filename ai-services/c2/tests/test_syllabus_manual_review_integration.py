
import copy
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_review_queue import (
    SyllabusTopicReviewQueue,
)
from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)
from services.syllabus_topic_review_validator import (
    SyllabusTopicReviewValidator,
)


BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "outputs" / "syllabus_reviews"

MODULE_KEYS = [
    "application_frameworks",
    "case_studies_software_engineering",
    "database_systems",
    "distributed_systems",
    "software_architecture",
    "software_engineering_process_quality_management",
    "software_project_management",
    "user_experience_engineering",
]


def make_decision(candidate, decision, reviewer_id):
    if decision not in ("approved", "rejected"):
        raise ValueError("Invalid test decision")

    return {
        "candidate_id": candidate["candidate_id"],
        "module_key": candidate["module_key"],
        "candidate_name": candidate["candidate_name"],
        "review_decision": decision,
        "verification_status": (
            "verified" if decision == "approved" else "rejected"
        ),
        "reviewer_id": reviewer_id,
        "reviewed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "review_notes": (
            "Simulated decision for integration testing only"
        ),
        "sources": copy.deepcopy(candidate["sources"]),
    }


def run_tests():
    print(
        "\n--- M7.3.5.3.5 MANUAL REVIEW INTEGRATION TEST ---"
    )

    validator = SyllabusTopicReviewValidator()

    # Use temporary storage. Never write test decisions
    # into the real review decision repository.
    with tempfile.TemporaryDirectory() as directory:
        storage_path = (
            Path(directory) / "test_review_decisions.json"
        )

        repository = SyllabusTopicReviewRepository(
            storage_path=storage_path
        )

        queue = SyllabusTopicReviewQueue(
            reports_dir=REPORTS_DIR,
            repository=repository,
        )

        print("PASS: isolated test repository initialized")

        # TEST 1: Load real reports for all eight modules.
        initial_counts = {}
        total_candidates = 0
        total_excluded = 0

        for module_key in MODULE_KEYS:
            result = queue.get_queue(
                module_key,
                page=1,
                page_size=10,
            )

            assert result["module_key"] == module_key
            assert result["total_candidates"] > 0
            assert len(result["candidates"]) <= 10

            initial_counts[module_key] = (
                result["total_candidates"]
            )
            total_candidates += result["total_candidates"]

            excluded = queue.get_excluded_candidates(
                module_key
            )
            total_excluded += excluded[
                "excluded_candidate_count"
            ]

        assert len(initial_counts) == 8

        print("PASS: real reports loaded for eight modules")
        print("PASS: review queue pagination across modules")

        # TEST 2: Confirm initial records are unverified.
        module_key = "database_systems"

        initial_queue = queue.get_queue(
            module_key,
            page=1,
            page_size=3,
        )

        assert len(initial_queue["candidates"]) == 3

        first_candidate = initial_queue["candidates"][0]
        second_candidate = initial_queue["candidates"][1]

        assert (
            first_candidate["candidate_id"]
            != second_candidate["candidate_id"]
        )

        for candidate in initial_queue["candidates"]:
            assert candidate["review_decision"] == "pending"
            assert candidate["verification_status"] == "unverified"
            assert candidate["sources"]

        print("PASS: initial candidates remain unverified")

        # TEST 3: Simulate a human approval decision.
        approved_record = make_decision(
            first_candidate,
            decision="approved",
            reviewer_id="integration_test_reviewer",
        )

        assert validator.validate(
            approved_record
        )["valid"] is True

        repository.save_review(approved_record)

        stored_approval = repository.get_review(
            first_candidate["candidate_id"]
        )

        assert stored_approval == approved_record
        assert (
            stored_approval["verification_status"]
            == "verified"
        )

        print("PASS: simulated approval validated and stored")

        # TEST 4: Approved candidate leaves pending queue.
        pending_after_approval = queue.get_queue(
            module_key,
            page=1,
            page_size=10,
        )

        assert (
            pending_after_approval["total_candidates"]
            == initial_counts[module_key] - 1
        )

        assert all(
            candidate["candidate_id"]
            != first_candidate["candidate_id"]
            for candidate in pending_after_approval["candidates"]
        )

        print("PASS: approved candidate removed from pending queue")

        # TEST 5: Simulate a human rejection decision.
        rejected_record = make_decision(
            second_candidate,
            decision="rejected",
            reviewer_id="integration_test_reviewer",
        )

        assert validator.validate(
            rejected_record
        )["valid"] is True

        repository.save_review(rejected_record)

        stored_rejection = repository.get_review(
            second_candidate["candidate_id"]
        )

        assert (
            stored_rejection["verification_status"]
            == "rejected"
        )

        print("PASS: simulated rejection validated and stored")

        # TEST 6: Both reviewed candidates leave pending queue.
        pending_after_both = queue.get_queue(
            module_key,
            page=1,
            page_size=10,
        )

        assert (
            pending_after_both["total_candidates"]
            == initial_counts[module_key] - 2
        )

        print("PASS: pending queue updated after decisions")

        # TEST 7: Reviewed candidates remain accessible.
        all_candidates = queue.get_queue(
            module_key,
            page=1,
            page_size=10,
            include_reviewed=True,
        )

        assert (
            all_candidates["total_candidates"]
            == initial_counts[module_key]
        )

        reviewed_by_id = {
            candidate["candidate_id"]: candidate
            for candidate in all_candidates["candidates"]
        }

        assert (
            reviewed_by_id[first_candidate["candidate_id"]][
                "review_decision"
            ]
            == "approved"
        )

        assert (
            reviewed_by_id[second_candidate["candidate_id"]][
                "review_decision"
            ]
            == "rejected"
        )

        print("PASS: reviewed candidates remain accessible")

        # TEST 8: Source evidence is preserved.
        assert (
            stored_approval["sources"]
            == first_candidate["sources"]
        )

        assert (
            stored_rejection["sources"]
            == second_candidate["sources"]
        )

        print("PASS: source evidence preserved")

        # TEST 9: Review history is maintained.
        approval_history = repository.get_history(
            first_candidate["candidate_id"]
        )

        rejection_history = repository.get_history(
            second_candidate["candidate_id"]
        )

        assert len(approval_history) == 1
        assert len(rejection_history) == 1

        assert (
            approval_history[0]["new_decision"]
            == "approved"
        )

        assert (
            rejection_history[0]["new_decision"]
            == "rejected"
        )

        print("PASS: audit history preserved")

        # TEST 10: Invalid approval is rejected.
        invalid_approval = copy.deepcopy(approved_record)
        invalid_approval["reviewer_id"] = None

        assert validator.validate(
            invalid_approval
        )["valid"] is False

        try:
            repository.save_review(invalid_approval)
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Invalid approval was accepted"
            )

        print("PASS: invalid approval prevented")

        # TEST 11: Other modules are unaffected.
        for other_module in MODULE_KEYS:
            if other_module == module_key:
                continue

            result = queue.get_queue(
                other_module,
                page=1,
                page_size=5,
            )

            assert (
                result["total_candidates"]
                == initial_counts[other_module]
            )

        print("PASS: other module queues unaffected")

        # TEST 12: Original reports remain unchanged.
        report_path = (
            REPORTS_DIR
            / "database_systems_review_report.json"
        )

        with report_path.open(
            "r", encoding="utf-8"
        ) as file:
            original_report = json.load(file)

        assert all(
            candidate["verification_status"] == "unverified"
            and candidate["review_decision"] == "pending"
            for candidate in original_report[
                "review_candidates"
            ]
        )

        print("PASS: original exported report unchanged")

        # TEST 13: Temporary storage is separate.
        assert storage_path.exists()

        real_storage_path = (
            REPORTS_DIR / "review_decisions.json"
        )

        assert storage_path != real_storage_path

        print("PASS: test decisions isolated from real storage")

        print("\n--- INTEGRATION SUMMARY ---")
        print("Modules:", len(MODULE_KEYS))
        print("Initial review candidates:", total_candidates)
        print("Excluded candidates:", total_excluded)
        print("Simulated approvals:", 1)
        print("Simulated rejections:", 1)
        print("Stored audit events:", len(repository.get_history()))

    print(
        "\nAll M7.3.5.3.5 manual review integration tests passed."
    )


if __name__ == "__main__":
    run_tests()
