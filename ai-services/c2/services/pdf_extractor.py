from pathlib import Path

import fitz


class PDFExtractionError(Exception):
    """Raised when text cannot be extracted from a PDF."""


def extract_text_from_pdf(pdf_path: str) -> dict:
    """
    Extract text from a text-based PDF.

    Returns the complete text together with page-level text so that
    later C2 processing can preserve where questions were found.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise PDFExtractionError(f"PDF file does not exist: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise PDFExtractionError("The supplied file must be a PDF.")

    try:
        document = fitz.open(path)
    except Exception as exc:
        raise PDFExtractionError(f"Unable to open PDF: {exc}") from exc

    try:
        pages = []

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                }
            )

        full_text = "\n\n".join(
            page["text"] for page in pages if page["text"]
        )

        return {
            "filename": path.name,
            "page_count": len(document),
            "character_count": len(full_text),
            "is_text_extractable": bool(full_text.strip()),
            "pages": pages,
            "text": full_text,
        }

    except Exception as exc:
        raise PDFExtractionError(
            f"Failed while extracting PDF text: {exc}"
        ) from exc

    finally:
        document.close()