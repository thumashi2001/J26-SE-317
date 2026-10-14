
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.batch_processor import process_pdf_directory
from services.json_repository import save_batch_results
from services.dataset_validator import validate_question_repository


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = BASE_DIR / "datasets" / "authentic"
OUTPUT_DIR = BASE_DIR / "datasets" / "processed"


def main():
    print("\n--- C2 DATASET BUILD ---")

    batch = process_pdf_directory(INPUT_DIR)

    repository = {
        "questions": batch["questions"]
    }

    validation = validate_question_repository(repository)

    print("\n--- VALIDATION SUMMARY ---")
    print("Records:", validation["record_count"])
    print("Errors:", validation["error_count"])
    print("Warnings:", validation["warning_count"])

    if batch["summary"]["total_files"] == 0:
        raise RuntimeError(
            "No PDFs found. Dataset export cancelled."
        )

    if batch["summary"]["successful_files"] == 0:
        raise RuntimeError(
            "No valid PDFs processed. Dataset export cancelled."
        )

    if not validation["is_valid"]:
        print("\nDATASET BUILD FAILED")

        for error in validation["errors"]:
            print("ERROR:", error)

        raise RuntimeError(
            "Dataset validation failed. Export cancelled."
        )

    paths = save_batch_results(
        batch,
        OUTPUT_DIR
    )

    print("\n--- EXPORTED DATASET ---")

    for name, path in paths.items():
        print(f"{name}: {path}")

    print("\nDATASET BUILD COMPLETED")


if __name__ == "__main__":
    main()
