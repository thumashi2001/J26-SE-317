
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.subquestion_parser import parse_subquestions


def test_nested_roman_subquestions():
    question = {
        "question_number": 4,
        "heading": "Question 4",
        "text": """
(a) Explain transaction scheduling.

(b) Consider the following schedule.

(i) Identify the conflicting operations.
(ii) Draw the wait-for graph.
(iii) Explain deadlock prevention.

(c) Discuss database locking.
""",
    }

    result = parse_subquestions(question)

    labels = [
        part["label"]
        for part in result["subquestions"]
    ]

    assert labels == ["a", "b", "c"], labels

    children = result["subquestions"][1]["children"]

    child_labels = [
        child["label"]
        for child in children
    ]

    assert child_labels == ["i", "ii", "iii"], child_labels

    assert children[0]["id"] == "Q4(b)(i)"
    assert children[1]["id"] == "Q4(b)(ii)"
    assert children[2]["id"] == "Q4(b)(iii)"

    print("PASS: nested Roman subquestions")


def test_question_context():
    question = {
        "question_number": 2,
        "heading": "Question 2",
        "text": """
Consider the following database schema.

(a) Write an SQL query.
(b) Explain the result.
""",
    }

    result = parse_subquestions(question)

    assert "database schema" in result["context"]
    assert len(result["subquestions"]) == 2

    print("PASS: question context preservation")


if __name__ == "__main__":
    test_nested_roman_subquestions()
    test_question_context()
    print("\nAll hierarchy tests passed.")
