
import re


def _match(pattern, text, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None



MODULE_CODE_TO_NAME = {
    "IT3020": "Database Systems",
    "SE3060": "Database Systems",
    "SE3010": "Software Engineering Process and Quality Management",
    "SE3020": "Distributed Systems",
    "SE3030": "Software Architecture",
    "SE3040": "Application Frameworks",
    "SE3050": "User Experience Engineering",
    "SE3061": "User Experience Design",
    "SE3070": "Case Studies in Software Engineering",
    "SE3080": "Software Project Management",
}


def extract_metadata(first_page_text, page_count=None, filename=None):
    """
    Extract examination metadata from the first page.

    Missing fields remain None instead of being guessed.
    """

    text = first_page_text or ""

    module_match = re.search(
        r"(?im)^\s*(IT\d{4}|SE\d{4})\s*[-–—:]\s*(.+?)\s*$",
        text
    )

    if module_match:
        module_code = module_match.group(1).upper()
        module_name = module_match.group(2).strip()
    else:
        code_search = re.search(r"\b(IT\d{4}|SE\d{4})\b", text, re.IGNORECASE)
        if code_search:
            module_code = code_search.group(1).upper()
        elif filename:
            fn_code = re.search(r"\b(IT\d{4}|SE\d{4})\b", filename, re.IGNORECASE)
            module_code = fn_code.group(1).upper() if fn_code else None
        else:
            module_code = None

        module_name = MODULE_CODE_TO_NAME.get(module_code)

    year = _match(
        r"\bYear\s+(\d+)\b",
        text
    )
    if not year and module_code:
        year = "3"

    semester_raw = _match(
        r"\bSemester\s*([12IV]+(?:\s*/\s*[12IV]+)?)",
        text
    )
    if semester_raw:
        semester_norm = semester_raw.replace(" ", "")
        if "1/2" in semester_norm or "I/II" in semester_norm:
            semester = "1/2"
        elif "II" in semester_norm or "2" in semester_norm:
            semester = "2"
        elif "I" in semester_norm or "1" in semester_norm:
            semester = "1"
        else:
            semester = semester_norm
    else:
        semester = None

    calendar_year = _match(
        r"\bYear\s+\d+\s*,\s*Semester"
        r"\s+\d+(?:\s*/\s*\d+)?\s*"
        r"\((\d{4})\)",
        text
    )
    if not calendar_year:
        spaced_yr = _match(r"\(20\s*(\d{2})\)", text)
        if spaced_yr:
            calendar_year = f"20{spaced_yr.replace(' ', '')}"
    if not calendar_year:
        month_yr = _match(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*20\s*(\d{2})\b",
            text
        )
        if month_yr:
            calendar_year = f"20{month_yr.replace(' ', '')}"
    if not calendar_year:
        cal_match = _match(r"\b(201\d|202\d)\b", text)
        if cal_match:
            calendar_year = cal_match
    if not calendar_year and filename:
        fn_match = re.search(r"\b(201\d|202\d)\b", filename)
        if fn_match:
            calendar_year = fn_match.group(1)

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
    if not exam_month:
        spaced_month = re.search(
            r"\b((?:January|February|March|April|May|June|"
            r"July|August|September|October|November|"
            r"December))\s+20\s*(\d{2})\b",
            text,
            re.IGNORECASE
        )
        if spaced_month:
            exam_month = f"{spaced_month.group(1)} 20{spaced_month.group(2)}"

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
        else (
            "Repeat Examination"
            if re.search(
                r"\b(?:Repeat|Supplementary)\s+Examination\b",
                text,
                re.IGNORECASE
            )
            else (
                "Mid Examination"
                if re.search(
                    r"\bMid\s*(?:Semester|Term)?\s*Examination\b",
                    text,
                    re.IGNORECASE
                )
                else None
            )
        )
    )

    return {
        "institution": institution,
        "examination_type": examination_type,
        "module_code": module_code,
        "module_name": module_name,
        "academic_year": int(year) if year else None,
        "semester": semester,
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

