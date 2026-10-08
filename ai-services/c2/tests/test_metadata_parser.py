
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from services.pdf_extractor import extract_text_from_pdf
from services.metadata_parser import extract_metadata


PDF_PATH = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "authentic"
    / "sample.pdf"
)


def test_authentic_metadata():
    pdf = extract_text_from_pdf(str(PDF_PATH))

    metadata = extract_metadata(
        pdf["pages"][0]["text"],
        page_count=pdf["page_count"]
    )

    print("\n--- EXAMINATION METADATA ---")

    for key, value in metadata.items():
        print(f"{key}: {value}")

    assert metadata["module_code"] == "IT3020"
    assert metadata["module_name"] == "Database Systems"
    assert metadata["academic_year"] == 3
    assert metadata["semester"] == "1/2"
    assert metadata["calendar_year"] == 2023
    assert metadata["duration_minutes"] == 120
    assert metadata["total_marks"] == 100
    assert metadata["question_count"] == 4
    assert metadata["page_count"] == 6

    print("\nPASS: authentic paper metadata extraction")


if __name__ == "__main__":
    test_authentic_metadata()
