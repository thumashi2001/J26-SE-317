"""C2 -> C3 input adapter: turn a C2 question record into the question context C3 needs, without inventing anything.

SIMPLE ENGLISH
    C2 (`ai-services/c2/services/question_repository.py`, `build_question_repository`) produces question records with an id,
    the question text, context, a `marks` figure and its `marks_status`. It does NOT produce a rubric, a reference answer or
    expected concepts. So a C2 record alone can never be marked: this adapter keeps what C2 really provides, refuses a record
    that is unusable, takes the mark total only when C2 says it was extracted or calculated, and returns an explicit list of
    what the lecturer still has to supply. `build_assessment_request` then joins the C2 context with a lecturer-supplied
    rubric and the student's answer; it never fabricates a rubric.

    There is no HTTP endpoint on the C2 side in this repository, so this is a library function, not a network integration.
"""

from __future__ import annotations

from app.schemas.assessment import AssessmentRequest

# marks_status values after which C2's `marks` can be trusted (see ai-services/c2/services/dataset_validator.py).
TRUSTED_MARK_STATUSES = frozenset({"extracted", "calculated"})
# What C2 does not provide and C3 needs before it can mark.
LECTURER_MUST_SUPPLY = ("rubric", "reference_answer", "expected_concepts")


class C2RecordError(ValueError):
    """The C2 record can not be used as a C3 question."""


def question_context_from_c2(record: dict) -> dict:
    """Keep what C2 provides: ids, text, context, a trusted mark total and metadata; list what is still missing."""
    if not isinstance(record, dict):
        raise C2RecordError("C2 record must be an object")
    question_id = record.get("question_id")
    text = record.get("question_text")
    if not isinstance(question_id, str) or not question_id.strip():
        raise C2RecordError("C2 record has no question_id")
    if not isinstance(text, str) or not text.strip():
        raise C2RecordError(f"{question_id}: C2 record has no question text")
    marks, status = record.get("marks"), record.get("marks_status", "unknown")
    trusted = (status in TRUSTED_MARK_STATUSES and isinstance(marks, int) and not isinstance(marks, bool) and marks > 0)
    return {
        "question_id": question_id.strip(),
        "question_text": text.strip(),
        "context": (record.get("context") or "").strip(),
        "max_marks": float(marks) if trusted else None,
        "max_marks_note": None if trusted else f"C2 marks not usable (marks_status={status!r}, marks={marks!r})",
        "metadata": {k: record.get(k) for k in ("paper_id", "module_code", "module_name", "topic", "bloom_level", "difficulty")},
        "lecturer_must_supply": list(LECTURER_MUST_SUPPLY),
    }


def build_assessment_request(context: dict, student_answer: str, rubric: dict,
                             reference_answer: str | None = None, expected_concepts: list[str] | None = None,
                             answer_type: str = "short") -> AssessmentRequest:
    """Join a C2 question context with a lecturer-supplied rubric and a student answer. A missing rubric is an error."""
    if not rubric:
        raise C2RecordError(f"{context.get('question_id')}: a rubric must be supplied; C2 does not provide one")
    return AssessmentRequest(
        question_id=context["question_id"], question_text=context["question_text"], student_answer=student_answer,
        reference_answer=reference_answer, expected_concepts=expected_concepts, answer_type=answer_type,
        rubric=rubric, max_marks=context.get("max_marks"),
    )
