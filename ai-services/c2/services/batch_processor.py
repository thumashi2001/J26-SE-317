
from pathlib import Path

from services.paper_parser import parse_paper
from services.question_repository import build_question_repository


def process_pdf_directory(directory):
    """
    Process every PDF in a directory.

    Continue processing other files if one PDF fails.
    """
    directory = Path(directory)

    if not directory.is_dir():
        raise NotADirectoryError(
            f"PDF directory not found: {directory}"
        )

    pdf_files = sorted(
        path for path in directory.glob("*.pdf")
        if path.is_file()
    )

    papers = []
    questions = []
    errors = []

    for pdf_path in pdf_files:
        try:
            paper = parse_paper(pdf_path)
            repository = build_question_repository(paper)

            papers.append(paper)
            questions.extend(repository["questions"])

            print(
                f"PASS: {pdf_path.name} "
                f"({repository['record_count']} records)"
            )

        except Exception as exc:
            errors.append({
                "filename": pdf_path.name,
                "error": str(exc),
            })

            print(
                f"FAIL: {pdf_path.name} - {exc}"
            )

    return {
        "papers": papers,
        "questions": questions,
        "summary": {
            "total_files": len(pdf_files),
            "successful_files": len(papers),
            "failed_files": len(errors),
            "total_question_records": len(questions),
        },
        "errors": errors,
    }
