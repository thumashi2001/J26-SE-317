
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.syllabus_topic_review_validator import (
    SyllabusTopicReviewValidator,
)


def make_review_record(
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


def run_tests():
    print("\n--- M7.3.5.3.2 REVIEW VALIDATOR UNIT TESTS ---")

    validator = SyllabusTopicReviewValidator()

    # TEST 1: Valid pending review.
    record = make_review_record()
    result = validator.validate(record)

    assert result["valid"] is True
    assert result["errors"] == []

    print("PASS: valid pending review")

    # TEST 2: Valid approved review.
    approved = make_review_record(
        decision="approved",
        status="verified",
        reviewer_id="lecturer_001",
        reviewed_at="2026-10-16T10:00:00+05:30",
    )

    assert validator.validate(approved)["valid"] is True

    print("PASS: valid approved review")

    # TEST 3: Valid rejected review.
    rejected = make_review_record(
        decision="rejected",
        status="rejected",
        reviewer_id="lecturer_001",
        reviewed_at="2026-10-16T10:00:00+05:30",
    )

    assert validator.validate(rejected)["valid"] is True

    print("PASS: valid rejected review")

    # TEST 4: Invalid status combination.
    invalid_status = make_review_record(
        decision="approved",
        status="unverified",
        reviewer_id="lecturer_001",
        reviewed_at="2026-10-16T10:00:00+05:30",
    )

    assert validator.validate(invalid_status)["valid"] is False

    print("PASS: invalid status combination rejected")

    # TEST 5: Approval requires reviewer.
    missing_reviewer = make_review_record(
        decision="approved",
        status="verified",
        reviewed_at="2026-10-16T10:00:00+05:30",
    )

    assert validator.validate(missing_reviewer)["valid"] is False

    print("PASS: reviewer requirement enforced")

    # TEST 6: Approval requires timestamp.
    missing_timestamp = make_review_record(
        decision="approved",
        status="verified",
        reviewer_id="lecturer_001",
    )

    assert validator.validate(missing_timestamp)["valid"] is False

    print("PASS: review timestamp requirement enforced")

    # TEST 7: Pending review cannot have reviewer metadata.
    pending_with_reviewer = make_review_record(
        reviewer_id="lecturer_001",
    )

    assert validator.validate(pending_with_reviewer)["valid"] is False

    print("PASS: pending review safeguards")

    # TEST 8: Invalid decision rejected.
    invalid_decision = make_review_record(
        decision="auto_approved",
    )

    assert validator.validate(invalid_decision)["valid"] is False

    print("PASS: invalid review decision rejected")

    # TEST 9: Missing source evidence rejected.
    missing_sources = make_review_record()
    missing_sources["sources"] = []

    assert validator.validate(missing_sources)["valid"] is False

    print("PASS: missing source evidence rejected")

    # TEST 10: Invalid source line number rejected.
    invalid_source = make_review_record()
    invalid_source["sources"][0]["line_number"] = 0

    assert validator.validate(invalid_source)["valid"] is False

    print("PASS: invalid source evidence rejected")

    # TEST 11: Missing required field rejected.
    missing_field = make_review_record()
    del missing_field["candidate_id"]

    assert validator.validate(missing_field)["valid"] is False

    print("PASS: missing required field rejected")

    # TEST 12: Timestamp must include timezone.
    invalid_timezone = make_review_record(
        decision="approved",
        status="verified",
        reviewer_id="lecturer_001",
        reviewed_at="2026-10-16T10:00:00",
    )

    assert validator.validate(invalid_timezone)["valid"] is False

    print("PASS: timezone requirement enforced")

    # TEST 13: Validation must not modify input.
    original = make_review_record()
    snapshot = copy.deepcopy(original)

    validator.validate(original)

    assert original == snapshot

    print("PASS: original review record unchanged")

    print(
        "\nAll M7.3.5.3.2 review validator unit tests passed."
    )


if __name__ == "__main__":
    run_tests()
