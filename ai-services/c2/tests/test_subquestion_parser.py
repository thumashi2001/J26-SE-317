
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.pdf_extractor import extract_text_from_pdf
from services.question_detector import detect_questions
from services.subquestion_parser import parse_subquestions


PDF_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "authentic"
    / "sample.pdf"
)


def main():
    pdf_result = extract_text_from_pdf(str(PDF_PATH))
    questions = detect_questions(pdf_result["text"])

    print("\n--- SUBQUESTION PARSING RESULT ---")
    print("Top-level questions:", len(questions))

    for question in questions:
        parsed = parse_subquestions(question)

        print(f"\nQUESTION {question['question_number']}")
        print(
            "Subquestions detected:",
            len(parsed["subquestions"])
        )

        for part in parsed["subquestions"]:
            print(f"\n  {part['id']}")
            print("  Text:", part["text"][:120])

            for child in part["children"]:
                print(f"    {child['id']}")
                print("    Text:", child["text"][:100])


if __name__ == "__main__":
    main()
