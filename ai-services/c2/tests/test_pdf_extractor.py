import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.pdf_extractor import extract_text_from_pdf


PDF_PATH = Path(__file__).resolve().parents[1] / "datasets" / "authentic" / "sample.pdf"

result = extract_text_from_pdf(str(PDF_PATH))

print("\n--- PDF EXTRACTION RESULT ---")
print("Filename:", result["filename"])
print("Pages:", result["page_count"])
print("Characters:", result["character_count"])
print("Text extractable:", result["is_text_extractable"])

print("\n--- FIRST 1500 CHARACTERS ---")
print(result["text"][:1500])