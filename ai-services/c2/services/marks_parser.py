
import re


MARKS_PATTERN = re.compile(
    r"(?i)\(?[ \t]*"
    r"(\d(?:[ \t]*\d){0,2})"
    r"[ \t]*['’]?[ \t]*"
    r"(?:marks?|mks?)"
    r"[ \t]*\)?"
)


def extract_marks(text):
    """Extract explicit mark values, including spaced digits."""
    if not text:
        return []

    values = []

    for match in MARKS_PATTERN.finditer(text):
        digits = re.sub(r"\s+", "", match.group(1))
        values.append(int(digits))

    return values


def _annotate(text):
    values = extract_marks(text)

    if len(values) == 1:
        return values[0], "extracted"

    if len(values) > 1:
        return None, "ambiguous"

    return None, "missing"


def assign_marks(question):
    """
    Assign marks conservatively.

    Never assign a collection of marks to a single
    subquestion without reliable evidence.
    """
    result = {
        **question,
        "subquestions": [],
        "total_marks": None,
        "total_marks_status": "unknown",
    }

    parts = question.get("subquestions", [])

    for index, part in enumerate(parts):
        part_copy = {
            **part,
            "children": [],
        }

        children = part.get("children", [])

        if children:
            for child in children:
                marks, status = _annotate(child["text"])

                part_copy["children"].append({
                    **child,
                    "marks": marks,
                    "marks_status": status,
                })

            child_marks = [
                child["marks"]
                for child in part_copy["children"]
            ]

            if child_marks and all(
                value is not None
                for value in child_marks
            ):
                part_copy["marks"] = sum(child_marks)
                part_copy["marks_status"] = "calculated"
            else:
                part_copy["marks"] = None
                part_copy["marks_status"] = "needs_review"

        else:
            marks, status = _annotate(part["text"])

            # Last-part trailing totals require special handling.
            if index == len(parts) - 1:
                values = extract_marks(part["text"])

                if len(values) == 2:
                    candidate_total = values[-1]

                    if candidate_total > values[0]:
                        # A possible question-level total.
                        # Preserve the candidate without silently
                        # treating it as verified.
                        part_copy["marks"] = values[0]
                        part_copy["marks_status"] = (
                            "needs_review"
                        )

                        result["total_marks"] = candidate_total
                        result["total_marks_status"] = (
                            "candidate"
                        )

                        result["subquestions"].append(part_copy)
                        continue

            part_copy["marks"] = marks
            part_copy["marks_status"] = status

        result["subquestions"].append(part_copy)

    return result
