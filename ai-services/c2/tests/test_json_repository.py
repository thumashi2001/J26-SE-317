
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.batch_processor import process_pdf_directory
from services.json_repository import save_batch_results


BASE_DIR = Path(__file__).resolve().parents[1]

AUTHENTIC_DIR = (
    BASE_DIR / "datasets" / "authentic"
)


def test_json_persistence():
    batch_result = process_pdf_directory(
        AUTHENTIC_DIR
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        paths = save_batch_results(
            batch_result,
            temp_dir
        )

        for path in paths.values():
            assert Path(path).exists()

        with open(
            paths["papers"],
            encoding="utf-8"
        ) as file:
            papers = json.load(file)

        with open(
            paths["questions"],
            encoding="utf-8"
        ) as file:
            questions = json.load(file)

        with open(
            paths["report"],
            encoding="utf-8"
        ) as file:
            report = json.load(file)

        assert len(papers) == 1
        assert len(questions) == 25

        assert (
            report["summary"]["successful_files"]
            == 1
        )

        assert (
            report["summary"]["total_question_records"]
            == len(questions)
        )

        print("\n--- JSON PERSISTENCE RESULT ---")
        print("Papers saved:", len(papers))
        print("Questions saved:", len(questions))
        print("Successful files:",
              report["summary"]["successful_files"])

        print("\nPASS: JSON files created")
        print("PASS: saved JSON content validated")


if __name__ == "__main__":
    test_json_persistence()
