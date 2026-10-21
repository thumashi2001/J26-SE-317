
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.lecture_text_extractor import extract_lecture_text


def run_tests():
    syllabus_dir = ROOT / "datasets" / "syllabus"

    files = sorted(
        path
        for path in syllabus_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".pdf", ".pptx"}
    )

    print("--- M7.3.2 UNIFIED LECTURE EXTRACTION TEST ---")

    assert files, "No lecture materials found"

    successful = 0
    failed = 0
    empty_text = 0
    format_counts = {"pdf": 0, "pptx": 0}

    for file_path in files:
        try:
            result = extract_lecture_text(file_path)

            assert result["file_type"] in format_counts
            assert result["unit_count"] > 0
            assert result["character_count"] >= 0
            assert isinstance(result["text"], str)

            format_counts[result["file_type"]] += 1

            if not result["is_text_extractable"]:
                empty_text += 1
                print(f"WARNING: No text: {file_path.name}")

            successful += 1

        except Exception as error:
            failed += 1
            print(f"FAIL: {file_path.name} - {error}")

    print("\n--- EXTRACTION SUMMARY ---")
    print(f"Total files: {len(files)}")
    print(f"PDF files: {format_counts['pdf']}")
    print(f"PPTX files: {format_counts['pptx']}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Files without extractable text: {empty_text}")

    assert failed == 0, "Some lecture files failed extraction"

    print("\nAll M7.3.2 unified extraction tests passed.")


if __name__ == "__main__":
    run_tests()
