import re


QUESTION_PATTERN = re.compile(
    r"(?im)^\s*(?:question\s+|q\s*)(\d{1,2}|[IVX]+)\s*[:.\-]?\s*$"
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
    Convert labels such as 01, 1, I and IV
    into integer question numbers.
    """
    value = value.strip().upper()

    if value.isdigit():
        return int(value)

    return ROMAN_NUMERALS.get(value)


def detect_questions(text: str) -> list:
    """
    Detect top-level examination questions from extracted PDF text.
    """

    matches = []

    for match in QUESTION_PATTERN.finditer(text):

        question_number = normalize_question_number(
            match.group(1)
        )

        if question_number is not None:
            matches.append(
                {
                    "start": match.start(),
                    "content_start": match.end(),
                    "question_number": question_number,
                    "heading": match.group(0).strip(),
                }
            )

    questions = []

    for index, match in enumerate(matches):

        if index + 1 < len(matches):
            end = matches[index + 1]["start"]
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