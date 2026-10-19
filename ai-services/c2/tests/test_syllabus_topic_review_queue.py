
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_review_queue import (
    SyllabusTopicReviewQueue,
)
from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)


MODULE_KEY = "database_systems"


def make_candidate(name, rank, score, line_number):
    return {
        "module_key": MODULE_KEY,
        "candidate_name": name,
        "rank": rank,
        "ranking_score": score,
        "occurrence_count": 1,
        "document_count": 1,
        "sources": [
            {
                "filename": "lecture1.pdf",
                "line_number": line_number,
            }
        ],
        "verification_status": "unverified",
        "review_decision": "pending",
        "review_notes": "",
    }


def make_report():
    return {
        "schema_version": "1.0",
        "module_key": MODULE_KEY,
        "summary": {
            "review_candidate_count": 3,
            "excluded_candidate_count": 1,
            "pending_review_count": 3,
        },
        "review_candidates": [
            make_candidate("Database Indexing", 2, 70, 20),
            make_candidate("SQL Joins", 3, 60, 30),
            make_candidate("Database Normalization", 1, 90, 10),
        ],
        "excluded_candidates": [
            {
                "module_key": MODULE_KEY,
                "candidate_name": "Example",
                "verification_status": "unverified",
                "extraction_method": "rule_based",
                "sources": [
                    {
                        "filename": "lecture1.pdf",
                        "line_number": 40,
                    }
                ],
            }
        ],
    }


def make_review(candidate, decision, reviewer_id, reviewed_at):
    return {
        "candidate_id": candidate["candidate_id"],
        "module_key": candidate["module_key"],
        "candidate_name": candidate["candidate_name"],
        "review_decision": decision,
        "verification_status": (
            "verified" if decision == "approved" else "rejected"
        ),
        "reviewer_id": reviewer_id,
        "reviewed_at": reviewed_at,
        "review_notes": "Reviewed against lecture evidence",
        "sources": copy.deepcopy(candidate["sources"]),
    }


def expect_value_error(action):
    try:
        action()
    except ValueError:
        return

    raise AssertionError("Expected ValueError was not raised")


def run_tests():
    print("\n--- M7.3.5.3.4 REVIEW QUEUE UNIT TESTS ---")

    with tempfile.TemporaryDirectory() as directory:
        base_path = Path(directory)
        reports_dir = base_path / "reports"
        reports_dir.mkdir()

        report_path = (
            reports_dir / "database_systems_review_report.json"
        )

        report = make_report()

        report_path.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

        repository = SyllabusTopicReviewRepository(
            storage_path=base_path / "review_decisions.json"
        )

        queue = SyllabusTopicReviewQueue(
            reports_dir=reports_dir,
            repository=repository,
        )

        # TEST 1: Stable candidate IDs.
        first_id = queue.candidate_id(
            MODULE_KEY, "Database Normalization"
        )
        second_id = queue.candidate_id(
            MODULE_KEY, "  database   normalization "
        )

        assert first_id == second_id
        assert first_id.startswith("database_systems:")

        print("PASS: stable normalized candidate IDs")

        # TEST 2: Queue is sorted by ranking priority.
        result = queue.get_queue(MODULE_KEY)

        names = [
            candidate["candidate_name"]
            for candidate in result["candidates"]
        ]

        assert names == [
            "Database Normalization",
            "Database Indexing",
            "SQL Joins",
        ]

        print("PASS: evidence-based queue ordering")

        # TEST 3: Pagination.
        page_one = queue.get_queue(
            MODULE_KEY, page=1, page_size=2
        )
        page_two = queue.get_queue(
            MODULE_KEY, page=2, page_size=2
        )

        assert page_one["total_candidates"] == 3
        assert page_one["total_pages"] == 2
        assert len(page_one["candidates"]) == 2
        assert len(page_two["candidates"]) == 1

        assert (
            page_one["candidates"][0]["candidate_name"]
            == "Database Normalization"
        )
        assert (
            page_two["candidates"][0]["candidate_name"]
            == "SQL Joins"
        )

        print("PASS: queue pagination")

        # TEST 4: New candidates remain pending.
        for candidate in result["candidates"]:
            assert candidate["review_decision"] == "pending"
            assert candidate["verification_status"] == "unverified"
            assert candidate["reviewer_id"] is None
            assert candidate["reviewed_at"] is None

        print("PASS: unreviewed candidates remain pending")

        # TEST 5: Source evidence is preserved.
        normalization = result["candidates"][0]

        assert normalization["sources"] == [
            {
                "filename": "lecture1.pdf",
                "line_number": 10,
            }
        ]

        print("PASS: source evidence preserved")

        # TEST 6: Invalid pagination is rejected.
        expect_value_error(
            lambda: queue.get_queue(MODULE_KEY, page=0)
        )
        expect_value_error(
            lambda: queue.get_queue(MODULE_KEY, page_size=0)
        )
        expect_value_error(
            lambda: queue.get_queue(MODULE_KEY, page_size=101)
        )
        expect_value_error(
            lambda: queue.get_queue(MODULE_KEY, page=True)
        )

        print("PASS: invalid pagination rejected")

        # TEST 7: Invalid module key is rejected.
        expect_value_error(
            lambda: queue.get_queue("../invalid")
        )

        print("PASS: invalid module key rejected")

        # TEST 8: Approve a candidate through the repository.
        approved_record = make_review(
            normalization,
            decision="approved",
            reviewer_id="lecturer_001",
            reviewed_at="2026-10-16T10:00:00+05:30",
        )

        repository.save_review(approved_record)

        pending_queue = queue.get_queue(MODULE_KEY)

        assert pending_queue["total_candidates"] == 2
        assert all(
            candidate["candidate_name"]
            != "Database Normalization"
            for candidate in pending_queue["candidates"]
        )

        print("PASS: approved candidate removed from pending queue")

        # TEST 9: Reviewed candidates can be included.
        all_candidates = queue.get_queue(
            MODULE_KEY,
            include_reviewed=True,
        )

        assert all_candidates["total_candidates"] == 3

        reviewed = next(
            candidate
            for candidate in all_candidates["candidates"]
            if candidate["candidate_name"]
            == "Database Normalization"
        )

        assert reviewed["review_decision"] == "approved"
        assert reviewed["verification_status"] == "verified"
        assert reviewed["reviewer_id"] == "lecturer_001"

        print("PASS: saved review decision displayed")

        # TEST 10: Rejected candidates are also omitted.
        indexing = next(
            candidate
            for candidate in all_candidates["candidates"]
            if candidate["candidate_name"] == "Database Indexing"
        )

        rejected_record = make_review(
            indexing,
            decision="rejected",
            reviewer_id="lecturer_002",
            reviewed_at="2026-10-16T11:00:00+05:30",
        )

        repository.save_review(rejected_record)

        pending_queue = queue.get_queue(MODULE_KEY)

        assert pending_queue["total_candidates"] == 1
        assert (
            pending_queue["candidates"][0]["candidate_name"]
            == "SQL Joins"
        )

        print("PASS: rejected candidate removed from pending queue")

        # TEST 11: Administrative exclusions remain available.
        excluded = queue.get_excluded_candidates(MODULE_KEY)

        assert excluded["excluded_candidate_count"] == 1
        assert excluded["candidates"][0]["candidate_name"] == "Example"
        assert (
            excluded["candidates"][0]["verification_status"]
            == "unverified"
        )
        assert (
            excluded["candidates"][0]["review_decision"]
            == "pending"
        )

        print("PASS: excluded candidates retained for inspection")

        # TEST 12: Report file remains unchanged.
        saved_report = json.loads(
            report_path.read_text(encoding="utf-8")
        )

        assert saved_report == report

        print("PASS: original review report unchanged")

        # TEST 13: Saved review evidence mismatch is rejected.
        modified_report = copy.deepcopy(report)
        modified_report["review_candidates"][2]["sources"][0][
            "line_number"
        ] = 999

        report_path.write_text(
            json.dumps(modified_report),
            encoding="utf-8",
        )

        expect_value_error(
            lambda: queue.get_queue(
                MODULE_KEY, include_reviewed=True
            )
        )

        print("PASS: saved review evidence mismatch rejected")

    print(
        "\nAll M7.3.5.3.4 review queue unit tests passed."
    )


if __name__ == "__main__":
    run_tests()
