
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.pdf_extractor import extract_text_from_pdf
from services.question_detector import detect_questions
from services.subquestion_parser import parse_subquestions
from services.marks_parser import extract_marks


PDF_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "authentic"
    / "sample.pdf"
)


def main():
    pdf = extract_text_from_pdf(str(PDF_PATH))
    questions = detect_questions(pdf["text"])

    for question in questions:
        if question["question_number"] not in (1, 3, 4):
            continue

        parsed = parse_subquestions(question)

        print("\n" + "=" * 65)
        print(f"QUESTION {question['question_number']}")
        print("=" * 65)

        for part in parsed["subquestions"]:
            if part["id"] not in (
                "Q1(e)", "Q3(c)", "Q4(d)"
            ):
                continue

            print(f"\n--- {part['id']} ---")
            print("FULL TEXT:")
            print(repr(part["text"]))
            print("MARK VALUES:", extract_marks(part["text"]))

            for child in part["children"]:
                print(f"\n--- {child['id']} ---")
                print("FULL TEXT:")
                print(repr(child["text"]))
                print(
                    "MARK VALUES:",
                    extract_marks(child["text"])
                )


if __name__ == "__main__":
    main()
