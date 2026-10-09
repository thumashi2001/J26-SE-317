
import hashlib


def make_paper_id(paper):
    """
    Generate a stable identifier from the source PDF.
    """
    metadata = paper.get("metadata", {})
    source = paper.get("source", {})

    code = metadata.get("module_code") or "UNKNOWN"
    year = metadata.get("calendar_year") or "UNKNOWN"
    filename = source.get("filename") or "unknown.pdf"

    digest = hashlib.sha256(
        f"{code}|{year}|{filename}".encode("utf-8")
    ).hexdigest()[:12]

    return f"{code}-{year}-{digest}"


def build_question_repository(paper):
    """
    Convert a structured paper into flat question records.

    Preserve question hierarchy, provenance, and
    mark-validation status.
    """
    metadata = paper.get("metadata", {})
    source = paper.get("source", {})

    paper_id = make_paper_id(paper)
    records = []

    def add_part(part, question_number, parent_id):
        part_id = part["id"]

        record = {
            "question_id": f"{paper_id}-{part_id}",
            "paper_id": paper_id,
            "module_code": metadata.get("module_code"),
            "module_name": metadata.get("module_name"),
            "calendar_year": metadata.get("calendar_year"),
            "semester": metadata.get("semester"),
            "question_number": question_number,
            "part_id": part_id,
            "parent_id": parent_id,
            "question_text": part.get("text", ""),
            "context": part.get("context", ""),
            "marks": part.get("marks"),
            "marks_status": part.get(
                "marks_status", "unknown"
            ),
            "topic": None,
            "bloom_level": None,
            "difficulty": None,
            "source_type": source.get("source_type"),
            "source_filename": source.get("filename"),
        }

        records.append(record)

        for child in part.get("children", []):
            add_part(child, question_number, part_id)

    for question in paper.get("questions", []):
        question_number = question["question_number"]
        parent_id = f"Q{question_number}"

        for part in question.get("subquestions", []):
            add_part(part, question_number, parent_id)

    return {
        "schema_version": "1.0",
        "paper_id": paper_id,
        "record_count": len(records),
        "questions": records,
    }
