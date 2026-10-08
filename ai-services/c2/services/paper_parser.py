
from pathlib import Path

from services.pdf_extractor import extract_text_from_pdf
from services.question_detector import detect_questions
from services.subquestion_parser import parse_subquestions
from services.marks_parser import assign_marks
from services.metadata_parser import extract_metadata


def parse_paper(pdf_path):
    """
    Convert an authentic examination PDF into
    structured, JSON-serializable paper data.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        raise FileNotFoundError(
            f"Examination PDF not found: {pdf_path}"
        )

    pdf = extract_text_from_pdf(str(pdf_path))

    if not pdf["is_text_extractable"]:
        raise ValueError(
            f"No extractable text in {pdf_path.name}"
        )

    if not pdf["pages"]:
        raise ValueError("PDF contains no readable pages")

    metadata = extract_metadata(
        pdf["pages"][0]["text"],
        page_count=pdf["page_count"]
    )

    raw_questions = detect_questions(pdf["text"])
    structured_questions = []

    for question in raw_questions:
        parsed = parse_subquestions(question)
        marked = assign_marks(parsed)
        structured_questions.append(marked)

    warnings = []

    expected_count = metadata.get("question_count")

    if (
        expected_count is not None
        and expected_count != len(structured_questions)
    ):
        warnings.append(
            f"Question count mismatch: "
            f"expected {expected_count}, "
            f"detected {len(structured_questions)}"
        )

    def collect_mark_warnings(parts):
        for part in parts:
            status = part.get("marks_status")

            if status in (
                "missing",
                "ambiguous",
                "needs_review"
            ):
                warnings.append(
                    f"{part['id']}: marks {status}"
                )

            collect_mark_warnings(
                part.get("children", [])
            )

    for question in structured_questions:
        collect_mark_warnings(
            question.get("subquestions", [])
        )

        if question.get("total_marks_status") == "candidate":
            warnings.append(
                f"Q{question['question_number']}: "
                "question total requires verification"
            )

    return {
        "schema_version": "1.0",
        "source": {
            "filename": pdf_path.name,
            "source_type": "authentic",
            "page_count": pdf["page_count"],
        },
        "metadata": metadata,
        "questions": structured_questions,
        "validation": {
            "detected_question_count": len(
                structured_questions
            ),
            "warning_count": len(warnings),
            "warnings": warnings,
        },
    }
