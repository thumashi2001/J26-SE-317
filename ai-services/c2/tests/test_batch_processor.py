
import sys
import tempfile
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.batch_processor import process_pdf_directory


BASE_DIR = Path(__file__).resolve().parents[1]
AUTHENTIC_DIR = BASE_DIR / "datasets" / "authentic"


def test_batch_processing():
    result = process_pdf_directory(AUTHENTIC_DIR)

    print("\n--- BATCH PROCESSING SUMMARY ---")

    for key, value in result["summary"].items():
        print(f"{key}: {value}")

    for error in result["errors"]:
        print("ERROR:", error)

    assert result["summary"]["total_files"] >= 1
    assert result["summary"]["successful_files"] >= 1
    assert (
        result["summary"]["total_question_records"]
        == len(result["questions"])
    )

    print("\nPASS: authentic PDF batch processing")


def test_invalid_pdf_isolated():
    """
    A corrupt PDF must not stop the remaining files.
    """
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)

        (folder / "invalid.pdf").write_bytes(
            b"This is not a valid PDF."
        )

        result = process_pdf_directory(folder)

        assert result["summary"]["total_files"] == 1
        assert result["summary"]["failed_files"] == 1
        assert result["summary"]["successful_files"] == 0
        assert len(result["errors"]) == 1

        print("PASS: invalid PDF error isolation")


if __name__ == "__main__":
    test_batch_processing()
    test_invalid_pdf_isolated()
    print("\nAll batch processing tests passed.")
