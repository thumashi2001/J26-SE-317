
import json
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.paper_parser import parse_paper


BASE_DIR = Path(__file__).resolve().parents[1]

PDF_PATH = (
    BASE_DIR
    / "datasets"
    / "authentic"
    / "sample.pdf"
)


def test_complete_paper_pipeline():
    result = parse_paper(PDF_PATH)

    print("\n--- STRUCTURED PAPER PIPELINE ---")

    print(
        "Module:",
        result["metadata"]["module_name"]
    )

    print(
        "Module code:",
        result["metadata"]["module_code"]
    )

    print(
        "Questions:",
        len(result["questions"])
    )

    print(
        "Pages:",
        result["source"]["page_count"]
    )

    print(
        "Validation warnings:",
        result["validation"]["warning_count"]
    )

    for warning in result["validation"]["warnings"]:
        print("  -", warning)

    # Verify authentic paper metadata.
    assert result["metadata"]["module_code"] == "IT3020"
    assert result["metadata"]["total_marks"] == 100

    # Verify question detection.
    assert len(result["questions"]) == 4

    # Verify hierarchical parsing.
    assert len(
        result["questions"][0]["subquestions"]
    ) == 5

    # Verify extracted marks.
    assert (
        result["questions"][0]["subquestions"][0]["marks"]
        == 3
    )

    # Verify calculated nested marks.
    assert (
        result["questions"][3]["subquestions"][2]["marks"]
        == 9
    )

    # Known ambiguities should remain visible.
    assert result["validation"]["warning_count"] > 0

    # Ensure all data is JSON serializable.
    json_text = json.dumps(
        result,
        indent=2,
        ensure_ascii=False
    )

    restored = json.loads(json_text)

    assert restored == result

    print("\nPASS: complete paper pipeline")
    print("PASS: hierarchical question structure")
    print("PASS: JSON serialization")
    print("PASS: ambiguity warnings preserved")


if __name__ == "__main__":
    test_complete_paper_pipeline()
