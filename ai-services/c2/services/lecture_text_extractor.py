
from pathlib import Path

from services.pdf_extractor import extract_text_from_pdf
from services.pptx_extractor import extract_text_from_pptx


SUPPORTED_EXTENSIONS = {".pdf", ".pptx"}


def extract_lecture_text(file_path):
    """
    Extract lecture text from supported document formats.

    Supported:
        PDF  - PyMuPDF
        PPTX - python-pptx
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Lecture file not found: {path}")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported lecture format: {extension}"
        )

    if extension == ".pdf":
        extracted = extract_text_from_pdf(str(path))
        page_count = extracted["page_count"]
        text = extracted["text"]

        return {
            "filename": path.name,
            "file_type": "pdf",
            "unit_count": page_count,
            "unit_type": "page",
            "character_count": len(text),
            "is_text_extractable": bool(text.strip()),
            "text": text,
        }

    extracted = extract_text_from_pptx(str(path))
    text = extracted["text"]

    return {
        "filename": path.name,
        "file_type": "pptx",
        "unit_count": extracted["slide_count"],
        "unit_type": "slide",
        "character_count": len(text),
        "is_text_extractable": bool(text.strip()),
        "text": text,
    }
