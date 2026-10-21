
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.pptx_extractor import extract_text_from_pptx


def run_tests():
    syllabus_dir = ROOT / "datasets" / "syllabus"
    pptx_files = sorted(syllabus_dir.rglob("*.pptx"))

    print("--- M7.3.2 PPTX EXTRACTION TEST ---")
    print(f"PPTX files found: {len(pptx_files)}")

    assert pptx_files, "No PPTX lecture files found"

    successful = 0
    failed = 0

    for file_path in pptx_files:
        try:
            result = extract_text_from_pptx(file_path)

            assert result["file_type"] == "pptx"
            assert result["slide_count"] > 0
            assert result["character_count"] >= 0

            print(f"\nPASS: {file_path.name}")
            print(f"  Slides: {result['slide_count']}")
            print(f"  Characters: {result['character_count']}")
            print(f"  Text extractable: {result['is_text_extractable']}")

            successful += 1

        except Exception as error:
            failed += 1
            print(f"\nFAIL: {file_path.name}")
            print(f"  Error: {error}")

    print("\n--- EXTRACTION SUMMARY ---")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    assert failed == 0, "Some PPTX files failed extraction"

    print("\nAll M7.3.2 PPTX extraction tests passed.")


if __name__ == "__main__":
    run_tests()
