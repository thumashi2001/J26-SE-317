
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.marks_parser import extract_marks, assign_marks


def test_extract_marks():
    assert extract_marks("(5 marks)") == [5]
    assert extract_marks("(4 Marks)") == [4]
    assert extract_marks("25 marks") == [25]
    assert extract_marks("(1'marks)") == [1]
    assert extract_marks("(2 marks) (3 marks)") == [2, 3]
    assert extract_marks("No marks specified") == []

    print("PASS: mark extraction formats")


def test_assign_marks():
    question = {
        "question_number": 1,
        "subquestions": [
            {
                "id": "Q1(a)",
                "label": "a",
                "text": "Explain indexing. (5 marks)",
                "children": [],
            },
            {
                "id": "Q1(b)",
                "label": "b",
                "text": "Discuss transactions.",
                "children": [],
            },
        ],
    }

    result = assign_marks(question)

    assert result["subquestions"][0]["marks"] == 5
    assert result["subquestions"][0]["marks_status"] == "extracted"

    assert result["subquestions"][1]["marks"] is None
    assert result["subquestions"][1]["marks_status"] == "missing"

    print("PASS: marks assignment")


def test_spaced_marks():
    assert extract_marks("( 10 marks)") == [10]
    assert extract_marks("( 1 0 marks)") == [10]
    assert extract_marks("(1'marks)") == [1]

    print("PASS: spaced and noisy mark formats")


def test_question_total_candidate():
    question = {
        "question_number": 1,
        "subquestions": [
            {
                "id": "Q1(a)",
                "label": "a",
                "text": "Explain a concept. (3 marks)",
                "children": [],
            },
            {
                "id": "Q1(e)",
                "label": "e",
                "text": (
                    "Critically analyse the models.\n"
                    "(5 Marks)\n"
                    "25 marks"
                ),
                "children": [],
            },
        ],
    }

    result = assign_marks(question)

    final_part = result["subquestions"][-1]

    assert final_part["marks"] == 5
    assert final_part["marks_status"] == "needs_review"
    assert result["total_marks"] == 25
    assert result["total_marks_status"] == "candidate"

    print("PASS: candidate question total")


def test_grouped_marks_remain_ambiguous():
    question = {
        "question_number": 4,
        "subquestions": [
            {
                "id": "Q4(d)",
                "label": "d",
                "text": (
                    "i. Search 58\n"
                    "ii. Insert 30\n"
                    "iii. Delete 41\n"
                    "(1'marks)\n"
                    "(2 marks)\n"
                    "(2 marks)"
                ),
                "children": [
                    {
                        "id": "Q4(d)(i)",
                        "label": "i",
                        "text": "Search 58",
                    },
                    {
                        "id": "Q4(d)(ii)",
                        "label": "ii",
                        "text": "Insert 30",
                    },
                    {
                        "id": "Q4(d)(iii)",
                        "label": "iii",
                        "text": (
                            "Delete 41\n"
                            "(1'marks)\n"
                            "(2 marks)\n"
                            "(2 marks)"
                        ),
                    },
                ],
            }
        ],
    }

    result = assign_marks(question)
    part = result["subquestions"][0]

    assert part["marks"] is None
    assert part["marks_status"] == "needs_review"
    assert part["children"][2]["marks"] is None
    assert part["children"][2]["marks_status"] == "ambiguous"

    print("PASS: grouped marks remain ambiguous")


if __name__ == "__main__":
    test_extract_marks()
    test_assign_marks()
    test_spaced_marks()
    test_question_total_candidate()
    test_grouped_marks_remain_ambiguous()

    print("\nAll marks parser tests passed.")
