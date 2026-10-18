
"""M11.3.2A: read-only analysis of historical examination evidence."""

import json
from pathlib import Path


DEFAULT_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "past_paper_evidence_profiles.json"
)


class PastPaperEvidenceAnalyzer:
    def __init__(self, path=None):
        self.path = Path(path) if path else DEFAULT_PATH

    def load(self):
        data = json.loads(
            self.path.read_text(encoding="utf-8")
        )
        self.validate(data)
        return data

    @staticmethod
    def validate(data):
        if (
            not isinstance(data, dict)
            or data.get("schema_version") != "1.0"
        ):
            raise ValueError("Invalid evidence schema")

        if data.get("academic_verification_status") != "pending":
            raise ValueError(
                "Academic review cannot be bypassed"
            )

        modules = data.get("modules")

        if not isinstance(modules, list) or len(modules) != 8:
            raise ValueError("Expected exactly eight modules")

        seen = set()

        for m in modules:
            key = m.get("module_key")

            if (
                not isinstance(key, str)
                or not key
                or key in seen
            ):
                raise ValueError(
                    "Missing or duplicate module key"
                )

            seen.add(key)

            n = m.get("main_question_count")
            marks = m.get("main_question_marks")

            if (
                type(n) is not int
                or n < 1
                or not isinstance(marks, list)
                or len(marks) != n
            ):
                raise ValueError(
                    f"Invalid question structure: {key}"
                )

            if (
                type(m.get("total_marks")) is not int
                or m["total_marks"] <= 0
            ):
                raise ValueError(
                    f"Invalid total marks: {key}"
                )

            if (
                type(m.get("duration_minutes")) is not int
                or m["duration_minutes"] <= 0
            ):
                raise ValueError(
                    f"Invalid duration: {key}"
                )

            if any(
                x is not None
                and (type(x) is not int or x <= 0)
                for x in marks
            ):
                raise ValueError(
                    f"Invalid question marks: {key}"
                )

            known_sum = sum(
                x for x in marks if x is not None
            )

            if known_sum > m["total_marks"]:
                raise ValueError(
                    f"Known marks exceed paper total: {key}"
                )

            if (
                all(x is not None for x in marks)
                and known_sum != m["total_marks"]
            ):
                raise ValueError(
                    f"Complete marks do not match total: {key}"
                )

            if (
                not m.get("source_filename")
                or not m.get("source_pages")
            ):
                raise ValueError(
                    f"Missing provenance: {key}"
                )

            if (
                not m.get("observed_topics")
                or not m.get("observed_question_formats")
            ):
                raise ValueError(
                    f"Missing observations: {key}"
                )

        return True

    def report(self):
        data = self.load()
        results = []

        for m in data["modules"]:
            known = sum(
                v is not None
                for v in m["main_question_marks"]
            )

            results.append({
                "module_key": m["module_key"],
                "source_year": m["source_year"],
                "main_question_count": m[
                    "main_question_count"
                ],
                "known_question_mark_allocations": known,
                "unknown_question_mark_allocations": (
                    m["main_question_count"] - known
                ),
                "total_marks": m["total_marks"],
                "observed_topic_count": len(
                    m["observed_topics"]
                ),
                "ready_for_automatic_generation": False,
            })

        return {
            "module_count": len(results),
            "source_paper_count": len(results),
            "academic_verification_status": "pending",
            "modules": results,
        }
