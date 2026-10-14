
import re


def _match(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def extract_metadata(first_page_text, page_count=None):
    """
    Extract examination metadata from the first page.

    Missing fields remain None instead of being guessed.
    """

    text = first_page_text or ""

    module_match = re.search(
        r"(?im)^\s*(IT\d{4})\s*[-–—]\s*(.+?)\s*$",
        text
    )

    module_code = (
        module_match.group(1) if module_match else None
    )
    module_name = (
        module_match.group(2).strip()
        if module_match else None
    )

    year = _match(
        r"\bYear\s+(\d+)\b",
        text
    )

    semester = _match(
        r"\bSemester\s+(\d+(?:\s*/\s*\d+)?)",
        text
    )

    calendar_year = _match(
        r"\bYear\s+\d+\s*,\s*Semester"
        r"\s+\d+(?:\s*/\s*\d+)?\s*"
        r"\((\d{4})\)",
        text
    )

    duration_hours = _match(
        r"\bDuration\s*:\s*(\d+)\s*Hours?\b",
        text
    )

    exam_month = _match(
        r"\b((?:January|February|March|April|May|June|"
        r"July|August|September|October|November|"
        r"December)\s+\d{4})\b",
        text
    )

    total_marks = _match(
        r"\bTotal\s+marks\s+for\s+the\s+paper"
        r"\s+will\s+be\s+(\d+)",
        text
    )

    question_count = _match(
        r"\bpaper\s+contains\s+(\d+)\s+questions",
        text
    )

    institution = (
        "Sri Lanka Institute of Information Technology"
        if re.search(
            r"Sri Lanka Institute of Information Technology",
            text,
            re.IGNORECASE
        )
        else None
    )

    examination_type = (
        "Final Examination"
        if re.search(
            r"\bFinal Examination\b",
            text,
            re.IGNORECASE
        )
        else None
    )

    return {
        "institution": institution,
        "examination_type": examination_type,
        "module_code": module_code,
        "module_name": module_name,
        "academic_year": int(year) if year else None,
        "semester": semester.replace(" ", "") if semester else None,
        "calendar_year": (
            int(calendar_year) if calendar_year else None
        ),
        "duration_minutes": (
            int(duration_hours) * 60
            if duration_hours else None
        ),
        "exam_month": exam_month,
        "total_marks": (
            int(total_marks) if total_marks else None
        ),
        "question_count": (
            int(question_count) if question_count else None
        ),
        "page_count": page_count,
    }
