import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.pdf_extractor import extract_text_from_pdf
from services.question_detector import detect_questions


PDF_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "authentic"
    / "sample.pdf"
)


pdf_result = extract_text_from_pdf(str(PDF_PATH))

questions = detect_questions(pdf_result["text"])


print("\n--- QUESTION DETECTION RESULT ---")
print("Questions detected:", len(questions))


for question in questions:

    print("\n" + "=" * 60)

    print(
        f"QUESTION {question['question_number']}"
    )

    print("=" * 60)

    print(question["text"][:500])