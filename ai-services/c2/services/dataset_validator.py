
from collections import Counter


VALID_MARK_STATUSES = {
    "extracted",
    "calculated",
    "missing",
    "ambiguous",
    "needs_review",
    "unknown",
}


def validate_question_repository(repository):
    """
    Validate a flat question repository.

    Errors indicate structural problems.
    Warnings indicate incomplete or uncertain data.
    """
    records = repository.get("questions", [])

    errors = []
    warnings = []

    ids = [
        record.get("question_id")
        for record in records
    ]

    counts = Counter(ids)

    for question_id, count in counts.items():
        if question_id is None:
            errors.append("Question record has no ID")
        elif count > 1:
            errors.append(
                f"Duplicate question ID: {question_id}"
            )

    record_by_part = {
        (r.get("paper_id"), r.get("part_id")): r
        for r in records
    }

    for record in records:
        question_id = record.get("question_id", "UNKNOWN")

        if not record.get("module_code"):
            warnings.append(
                f"{question_id}: missing module code"
            )

        if not record.get("question_text", "").strip():
            warnings.append(
                f"{question_id}: empty question text"
            )

        marks_status = record.get(
            "marks_status", "unknown"
        )

        if marks_status not in VALID_MARK_STATUSES:
            errors.append(
                f"{question_id}: invalid marks status"
            )

        if marks_status in {
            "missing",
            "ambiguous",
            "needs_review",
            "unknown",
        }:
            warnings.append(
                f"{question_id}: marks {marks_status}"
            )

        marks = record.get("marks")

        if marks is not None and (
            isinstance(marks, bool)
            or not isinstance(marks, int)
            or marks < 0
        ):
            errors.append(
                f"{question_id}: invalid marks value"
            )

        parent_id = record.get("parent_id")

        if parent_id:
            parent_key = (
                record.get("paper_id"),
                parent_id,
            )

            # Top-level Q1, Q2 etc. are not stored
            # as individual repository records.
            top_level = (
                parent_id
                == f"Q{record.get('question_number')}"
            )

            if (
                not top_level
                and parent_key not in record_by_part
            ):
                errors.append(
                    f"{question_id}: missing parent "
                    f"{parent_id}"
                )

    return {
        "record_count": len(records),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0,
    }
