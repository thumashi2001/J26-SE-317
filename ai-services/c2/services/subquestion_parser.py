
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
    seen_ids = set()

    for index, match in enumerate(matches):
        end = (
            matches[index + 1]["start"]
            if index + 1 < len(matches)
            else len(text)
        )

        base_id = f"{parent_id}({match['label']})"
        part_id = base_id
        counter = 2
        while part_id in seen_ids:
            part_id = f"{parent_id}({match['label']}_{counter})"
            counter += 1
        seen_ids.add(part_id)

        parts.append({
            "id": part_id,
            "label": match["label"],
            "text": text[match["content_start"]:end].strip(),
            "children": [],
        })

    return parts


NUMBER_SUBQ_PATTERN = re.compile(
    r"(?m)^[ \t]*(?:\((\d{1,2})\)|(\d{1,2})[ \t]*[.,)]|[^\w\s\n]*(\d{1,2})[ \t]*,[ \t]*\.)[ \t]*"
)

MCQ_TOP_PATTERN = re.compile(
    r"(?m)^[ \t]*(\d{1,2})\.[ \t]+"
)


def find_numbered_subquestions(text):
    raw_matches = []
    for m in NUMBER_SUBQ_PATTERN.finditer(text):
        lbl = m.group(1) or m.group(2) or m.group(3)
        raw_matches.append({
            "start": m.start(),
            "content_start": m.end(),
            "label": lbl,
        })
    if len(raw_matches) < 2:
        return []
    if raw_matches[0]["label"] != "1":
        return []

    filtered = [raw_matches[0]]
    last_val = 1
    for m in raw_matches[1:]:
        val = int(m["label"])
        if val > last_val and val <= last_val + 2:
            filtered.append(m)
            last_val = val

    if len(filtered) < 2:
        return []

    sections_with_marks = 0
    for i, m in enumerate(filtered):
        end = filtered[i + 1]["start"] if i + 1 < len(filtered) else len(text)
        chunk = text[m["content_start"]:end]
        if re.search(r"\(?\s*\d+\s*marks?\s*\)?", chunk, re.IGNORECASE):
            sections_with_marks += 1

    if sections_with_marks >= len(filtered) // 2 and sections_with_marks >= 2:
        expanded = []
        for i, m in enumerate(filtered):
            expanded.append(m)
            if i + 1 < len(filtered):
                curr_val = int(m["label"])
                next_val = int(filtered[i + 1]["label"])
                if next_val == curr_val + 2:
                    start_offset = m["content_start"]
                    end_offset = filtered[i + 1]["start"]
                    chunk = text[start_offset:end_offset]
                    mark_matches = list(re.finditer(r"(?i)\(?\s*\d+\s*marks?\s*\)?", chunk))
                    if len(mark_matches) >= 2:
                        first_mark = mark_matches[0]
                        inter_start = start_offset + first_mark.end()
                        line_m = re.search(r"\S", text[inter_start:end_offset])
                        content_start = inter_start + (line_m.start() if line_m else 0)
                        expanded.append({
                            "start": inter_start,
                            "content_start": content_start,
                            "label": str(curr_val + 1),
                        })
        return expanded
    return []


def parse_subquestions(question):
    q_num = question["question_number"]
    question_id = f"Q{q_num}"
    text = question["text"]

    # Special handling for Question 0 (Part A / MCQs)
    if q_num == 0:
        mcq_matches = []
        for m in MCQ_TOP_PATTERN.finditer(text):
            mcq_matches.append({
                "start": m.start(),
                "content_start": m.end(),
                "label": m.group(1),
            })
        if mcq_matches and mcq_matches[0]["label"] == "1":
            valid_mcqs = []
            expected = 1
            for m in mcq_matches:
                if int(m["label"]) == expected:
                    valid_mcqs.append(m)
                    expected += 1
                elif int(m["label"]) > expected:
                    break

            if valid_mcqs:
                context = text[:valid_mcqs[0]["start"]].strip()
                subquestions = split_parts(text, valid_mcqs, question_id)
                for sq in subquestions:
                    t = sq["text"]
                    if "Answer Sheet" in t:
                        t = re.split(r"(?i)\n\s*Answer Sheet", t)[0].strip()
                    t = re.sub(r"(?i)\(?\s*1\s*marks?\s*\)?", "", t).strip()
                    t = t + "\n(1 mark)"
                    sq["text"] = t
                return {
                    **question,
                    "context": context,
                    "subquestions": subquestions,
                }

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
            num_matches = find_numbered_subquestions(part["text"])
            if num_matches:
                part["context"] = part["text"][
                    :num_matches[0]["start"]
                ].strip()
                part["children"] = split_parts(
                    part["text"],
                    num_matches,
                    part["id"]
                )
            else:
                part["context"] = part["text"]

    return {
        **question,
        "context": context,
        "subquestions": subquestions,
    }
