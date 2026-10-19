import re


QUESTION_PATTERN = re.compile(
    r"(?im)^\s*(?:(?:[qQoO]|Q[^\w\s]{1,5})?(?:uestion|apstion|[^\w\s]{1,5}stion|\bQ)\s*([oO\d]{1,2}|[IVX]+)\b\s*[:.\-–—_]?\s*(?:(?:\[|\()?\s*\d+\s*marks?(?:\]|\))?)?\s*(?:[-–—_].*)?|Part\s+A\b)\s*$"
)


ROMAN_NUMERALS = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
}


def normalize_question_number(value: str):
    """
    Convert labels such as 01, 1, o1, I and IV
    into integer question numbers.
    """
    value = value.strip().upper().replace("O", "0")

    if value.isdigit():
        return int(value)

    return ROMAN_NUMERALS.get(value)


def detect_questions(text: str) -> list:
    """
    Detect top-level examination questions from extracted PDF text.
    """

    matches = []

    for match in QUESTION_PATTERN.finditer(text):
        val = match.group(1)
        if val is None:
            # Matched "Part A"
            question_number = 0
        else:
            question_number = normalize_question_number(val)

        if question_number is not None:
            matches.append(
                {
                    "start": match.start(),
                    "content_start": match.end(),
                    "question_number": question_number,
                    "heading": match.group(0).strip(),
                }
            )

    # Filter out duplicate question numbers (e.g. repeated page headers)
    seen = set()
    unique_matches = []
    for m in matches:
        if m["question_number"] not in seen:
            seen.add(m["question_number"])
            unique_matches.append(m)

    questions = []

    for index, match in enumerate(unique_matches):

        if index + 1 < len(unique_matches):
            end = unique_matches[index + 1]["start"]
        else:
            end = len(text)

        question_text = text[
            match["content_start"]:end
        ].strip()

        questions.append(
            {
                "question_number": match["question_number"],
                "heading": match["heading"],
                "text": question_text,
            }
        )

    return questions