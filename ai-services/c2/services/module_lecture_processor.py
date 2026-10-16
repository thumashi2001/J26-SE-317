
from pathlib import Path

from services.lecture_text_extractor import extract_lecture_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SYLLABUS_DIR = ROOT / "datasets" / "syllabus"

SUPPORTED_EXTENSIONS = {".pdf", ".pptx"}


class ModuleLectureProcessor:
    """Process lecture materials and group extracted content by module."""

    def __init__(self, syllabus_dir=None):
        self.syllabus_dir = Path(
            syllabus_dir if syllabus_dir is not None
            else DEFAULT_SYLLABUS_DIR
        )

    def process(self):
        if not self.syllabus_dir.is_dir():
            raise ValueError("Syllabus directory does not exist")

        modules = {}
        summary = {
            "total_modules": 0,
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "empty_text": 0,
        }

        for module_dir in sorted(self.syllabus_dir.iterdir()):
            if not module_dir.is_dir():
                continue

            module_key = module_dir.name
            documents = []
            errors = []

            files = sorted(
                path for path in module_dir.rglob("*")
                if path.is_file()
                and path.suffix.lower() in SUPPORTED_EXTENSIONS
            )

            for file_path in files:
                summary["total_files"] += 1

                try:
                    extracted = extract_lecture_text(file_path)

                    document = {
                        "filename": extracted["filename"],
                        "relative_path": file_path.relative_to(
                            self.syllabus_dir
                        ).as_posix(),
                        "file_type": extracted["file_type"],
                        "unit_count": extracted["unit_count"],
                        "unit_type": extracted["unit_type"],
                        "character_count": extracted["character_count"],
                        "is_text_extractable": extracted[
                            "is_text_extractable"
                        ],
                        "text": extracted["text"],
                    }

                    documents.append(document)
                    summary["successful"] += 1

                    if not extracted["is_text_extractable"]:
                        summary["empty_text"] += 1

                except Exception as error:
                    summary["failed"] += 1
                    errors.append({
                        "filename": file_path.name,
                        "error": str(error),
                    })

            modules[module_key] = {
                "module_key": module_key,
                "document_count": len(documents),
                "documents": documents,
                "errors": errors,
            }

        summary["total_modules"] = len(modules)

        return {
            "schema_version": "1.0",
            "summary": summary,
            "modules": modules,
        }
