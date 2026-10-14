
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.pdf_extractor import extract_text_from_pdf
from services.question_detector import detect_questions
from services.subquestion_parser import parse_subquestions
from services.marks_parser import assign_marks


PDF_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "authentic"
    / "sample.pdf"
)


def main():
    pdf_result = extract_text_from_pdf(str(PDF_PATH))
    questions = detect_questions(pdf_result["text"])

    print("\n--- AUTHENTIC PAPER MARKS VALIDATION ---")

    for question in questions:
        parsed = parse_subquestions(question)
        marked = assign_marks(parsed)

        print(f"\nQUESTION {question['question_number']}")

        for part in marked["subquestions"]:
            print(
                f"  {part['id']}: "
                f"{part['marks']} marks "
                f"[{part['marks_status']}]"
            )

            for child in part["children"]:
                print(
                    f"    {child['id']}: "
                    f"{child['marks']} marks "
                    f"[{child['marks_status']}]"
                )


if __name__ == "__main__":
    main()
