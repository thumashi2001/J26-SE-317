
import json
from pathlib import Path


def save_json(data, file_path):
    """
    Save JSON-serializable data to a file.
    """
    file_path = Path(file_path)

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with file_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )

    return file_path


def save_batch_results(batch_result, output_directory):
    """
    Persist batch processing results as JSON files.
    """
    output_directory = Path(output_directory)

    papers_path = save_json(
        batch_result["papers"],
        output_directory / "papers.json"
    )

    questions_path = save_json(
        batch_result["questions"],
        output_directory / "questions.json"
    )

    report_path = save_json(
        {
            "summary": batch_result["summary"],
            "errors": batch_result["errors"],
        },
        output_directory / "processing_report.json"
    )

    return {
        "papers": str(papers_path),
        "questions": str(questions_path),
        "report": str(report_path),
    }
