
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.paper_parser import parse_paper
from services.question_repository import (
    build_question_repository,
)


BASE_DIR = Path(__file__).resolve().parents[1]

PDF_PATH = (
    BASE_DIR
    / "datasets"
    / "authentic"
    / "sample.pdf"
)


def test_question_repository():
    paper = parse_paper(PDF_PATH)

    repository = build_question_repository(paper)

    print("\n--- QUESTION REPOSITORY ---")
    print("Paper ID:", repository["paper_id"])
    print("Record count:", repository["record_count"])

    for record in repository["questions"][:10]:
        print(
            record["question_id"],
            "| marks:", record["marks"],
            "| status:", record["marks_status"]
        )

    assert repository["record_count"] > 0

    assert (
        repository["record_count"]
        == len(repository["questions"])
    )

    ids = [
        record["question_id"]
        for record in repository["questions"]
    ]

    assert len(ids) == len(set(ids)), (
        "Duplicate question IDs detected"
    )

    assert all(
        record["module_code"] == "IT3020"
        for record in repository["questions"]
    )

    nested = [
        record
        for record in repository["questions"]
        if record["part_id"] == "Q4(c)(ii)"
    ]

    assert len(nested) == 1
    assert nested[0]["parent_id"] == "Q4(c)"
    assert nested[0]["marks"] == 2

    assert all(
        record["source_type"] == "authentic"
        for record in repository["questions"]
    )

    print("\nPASS: question repository generation")
    print("PASS: unique question identifiers")
    print("PASS: hierarchical parent relationships")
    print("PASS: source provenance")


if __name__ == "__main__":
    test_question_repository()
