
import re


LETTER_PATTERN = re.compile(
    r"(?m)^[ \t]*(?:\(([a-hA-H])\)|([a-hA-H])[\).])"
    r"[ \t]+"
)

ROMAN_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:\(([ivx]+)\)|([ivx]+)[\).])"
    r"[ \t]+"
)

ROMAN_VALUES = {
    "i", "ii", "iii", "iv", "v",
    "vi", "vii", "viii", "ix", "x"
}


def find_parts(text, pattern, valid_labels=None):
    matches = []

    for match in pattern.finditer(text):
        label = (match.group(1) or match.group(2)).lower()

        if valid_labels and label not in valid_labels:
            continue

        matches.append({
            "start": match.start(),
            "content_start": match.end(),
            "label": label,
        })

    return matches


def split_parts(text, matches, parent_id):
    parts = []

    for index, match in enumerate(matches):
        end = (
            matches[index + 1]["start"]
            if index + 1 < len(matches)
            else len(text)
        )

        parts.append({
            "id": f"{parent_id}({match['label']})",
            "label": match["label"],
            "text": text[match["content_start"]:end].strip(),
            "children": [],
        })

    return parts


def parse_subquestions(question):
    question_id = f"Q{question['question_number']}"
    text = question["text"]

    letter_matches = find_parts(text, LETTER_PATTERN)

    if not letter_matches:
        return {
            **question,
            "context": text,
            "subquestions": [],
        }

    context = text[:letter_matches[0]["start"]].strip()

    subquestions = split_parts(
        text, letter_matches, question_id
    )

    for part in subquestions:
        roman_matches = find_parts(
            part["text"],
            ROMAN_PATTERN,
            ROMAN_VALUES
        )

        if roman_matches:
            part["context"] = part["text"][
                :roman_matches[0]["start"]
            ].strip()

            part["children"] = split_parts(
                part["text"],
                roman_matches,
                part["id"]
            )
        else:
            part["context"] = part["text"]

    return {
        **question,
        "context": context,
        "subquestions": subquestions,
    }
