
"""Tests for M12.2.1 authentic-question mock generation."""

import pytest

from services.personalized_mock_exam import PersonalizedMockExam


class FakeQuestionBank:
    def __init__(self, questions):
        self.questions = questions

    def list_questions(self, module_key, page=1, page_size=100):
        filtered = [
            q for q in self.questions
            if q.get("module_key") == module_key
        ]
        start = (page - 1) * page_size
        return {
            "total": len(filtered),
            "questions": filtered[start:start + page_size],
        }


def make_question(
    number,
    marks=5,
    source="authentic",
    topic="sql",
    verification="verified",
):
    return {
        "question_id": f"Q-{number}",
        "module_key": "database_systems",
        "question_text": f"Question {number}",
        "marks": marks,
        "marks_status": "extracted",
        "source_type": source,
        "topic_id": topic,
        "verification_status": verification,
        "difficulty": "medium",
    }


def generator(questions):
    return PersonalizedMockExam(
        question_bank=FakeQuestionBank(questions)
    )


def test_complete_mock():
    result = generator([
        make_question(i) for i in range(1, 5)
    ]).generate("database_systems", target_marks=20)

    assert result["status"] == "complete"
    assert result["total_marks"] == 20
    assert result["question_count"] == 4


def test_partial_mock():
    result = generator([
        make_question(1)
    ]).generate("database_systems", target_marks=100)

    assert result["status"] == "partial"
    assert result["total_marks"] == 5


def test_excludes_synthetic_questions():
    result = generator([
        make_question(1, source="synthetic"),
        make_question(2),
    ]).generate("database_systems", target_marks=10)

    assert result["question_count"] == 1
    assert result["questions"][0]["question_id"] == "Q-2"


def test_removes_duplicate_ids():
    result = generator([
        make_question(1),
        make_question(1),
    ]).generate("database_systems", target_marks=10)

    assert result["question_count"] == 1


def test_rejects_unextracted_marks():
    question = make_question(1)
    question["marks_status"] = "needs_review"

    result = generator([question]).generate(
        "database_systems",
        target_marks=10,
    )

    assert result["question_count"] == 0


def test_preferred_topics_prioritized():
    result = generator([
        make_question(1, topic="indexing"),
        make_question(2, topic="sql"),
    ]).generate(
        "database_systems",
        target_marks=5,
        preferred_topics=["sql"],
    )

    assert result["questions"][0]["question_id"] == "Q-2"


def test_unverified_topics_not_used_for_preference():
    result = generator([
        make_question(
            1, topic="sql", verification="unverified"
        ),
        make_question(
            2, topic="indexing", verification="verified"
        ),
    ]).generate(
        "database_systems",
        target_marks=5,
        preferred_topics=["indexing"],
    )

    assert result["questions"][0]["question_id"] == "Q-2"


def test_deterministic_selection():
    questions = [make_question(i) for i in range(1, 10)]
    service = generator(questions)

    first = service.generate(
        "database_systems", target_marks=20, seed=42
    )
    second = service.generate(
        "database_systems", target_marks=20, seed=42
    )

    assert first == second


def test_never_exceeds_target_marks():
    result = generator([
        make_question(1, marks=8),
        make_question(2, marks=8),
    ]).generate("database_systems", target_marks=10)

    assert result["total_marks"] <= 10


def test_invalid_target_marks():
    with pytest.raises(ValueError):
        generator([]).generate(
            "database_systems", target_marks=0
        )


def test_invalid_seed():
    with pytest.raises(ValueError):
        generator([]).generate(
            "database_systems", seed=True
        )


def test_empty_repository():
    result = generator([]).generate(
        "database_systems", target_marks=100
    )

    assert result["status"] == "partial"
    assert result["questions"] == []
    assert result["total_marks"] == 0


def test_max_questions_respected():
    result = generator([
        make_question(i) for i in range(1, 10)
    ]).generate(
        "database_systems",
        target_marks=100,
        max_questions=3,
    )

    assert result["question_count"] == 3


def test_no_official_structure_claim():
    result = generator([]).generate("database_systems")

    assert result["practice_only"] is True
    assert result["official_exam_structure_verified"] is False
    assert result["personalization"][
        "c1_diagnostic_integrated"
    ] is False
