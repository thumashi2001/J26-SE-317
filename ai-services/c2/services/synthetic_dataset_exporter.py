
"""M11.2.4 - Validate and export synthetic examination paper drafts."""

import json
import re
from pathlib import Path


DEFAULT_EXPORT_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "datasets"
    / "synthetic"
    / "drafts"
)


class SyntheticDatasetExporter:
    """
    Validate and export synthetic paper drafts as JSON.

    Exports are development-only and never imply
    academic approval. Existing files are not overwritten.
    """

    def __init__(self, export_directory=None):
        self.export_directory = Path(
            export_directory
            if export_directory is not None
            else DEFAULT_EXPORT_DIRECTORY
        )

    @staticmethod
    def _positive_int(value):
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        )

    def validate(self, paper):
        errors = []

        if not isinstance(paper, dict):
            return {
                "valid": False,
                "errors": ["Paper must be an object"],
            }

        if paper.get("dataset_type") != (
            "synthetic_exam_paper_draft"
        ):
            errors.append("Invalid dataset type")

        if paper.get("generation_mode") != (
            "development_fixture"
        ):
            errors.append(
                "Only development fixture papers can be exported"
            )

        if paper.get("source_type") != "synthetic":
            errors.append("Paper must be synthetic")

        if paper.get("verification_status") != "unverified":
            errors.append("Paper must be unverified")

        if paper.get("human_review_status") != "pending":
            errors.append("Paper must be pending human review")

        if paper.get("release_status") != "not_approved":
            errors.append("Paper must not be approved")

        paper_id = paper.get("paper_id")

        if (
            not isinstance(paper_id, str)
            or re.fullmatch(
                r"SYN-PAPER-[A-Za-z0-9_-]+",
                paper_id,
            ) is None
        ):
            errors.append("Invalid synthetic paper ID")

        module_key = paper.get("module_key")

        if (
            not isinstance(module_key, str)
            or not module_key.strip()
        ):
            errors.append("Missing module key")

        if (
            not isinstance(paper.get("module_name"), str)
            or not paper["module_name"].strip()
        ):
            errors.append("Missing module name")

        if not isinstance(
            paper.get("assembly_provenance"), dict
        ) or not paper["assembly_provenance"]:
            errors.append("Missing assembly provenance")
        else:
            provenance = paper["assembly_provenance"]

            if not provenance.get("source_batch_id"):
                errors.append("Missing source batch ID")

            if provenance.get("mode") != (
                "development_fixture"
            ):
                errors.append("Invalid assembly provenance mode")

        sections = paper.get("questions")

        if not isinstance(sections, list) or not sections:
            errors.append("Missing main questions")
            sections = []

        if paper.get("main_question_count") != len(sections):
            errors.append("Main question count mismatch")

        seen_numbers = set()
        seen_ids = set()
        seen_texts = set()
        calculated_total = 0

        for section in sections:
            if not isinstance(section, dict):
                errors.append("Invalid main question record")
                continue

            number = section.get("number")

            if not self._positive_int(number):
                errors.append("Invalid main question number")
            elif number in seen_numbers:
                errors.append("Duplicate main question number")
            else:
                seen_numbers.add(number)

            subquestions = section.get("subquestions")

            if (
                not isinstance(subquestions, list)
                or not subquestions
            ):
                errors.append("Missing subquestions")
                continue

            section_total = 0
            seen_labels = set()

            for sub in subquestions:
                if not isinstance(sub, dict):
                    errors.append("Invalid subquestion")
                    continue

                label = sub.get("label")

                if (
                    not isinstance(label, str)
                    or not label.strip()
                    or label in seen_labels
                ):
                    errors.append(
                        "Invalid or duplicate subquestion label"
                    )
                else:
                    seen_labels.add(label)

                question = sub.get("question")

                if not isinstance(question, dict):
                    errors.append("Missing question record")
                    continue

                marks = sub.get("marks")

                if not self._positive_int(marks):
                    errors.append("Invalid subquestion marks")
                    continue

                if question.get("marks") != marks:
                    errors.append(
                        "Subquestion and source marks mismatch"
                    )

                section_total += marks

                question_id = question.get("question_id")

                if (
                    not isinstance(question_id, str)
                    or not question_id.strip()
                    or question_id in seen_ids
                ):
                    errors.append(
                        "Missing or duplicate question ID"
                    )
                else:
                    seen_ids.add(question_id)

                question_text = question.get("question_text")

                if (
                    not isinstance(question_text, str)
                    or not question_text.strip()
                    or question_text in seen_texts
                ):
                    errors.append(
                        "Missing or duplicate question text"
                    )
                else:
                    seen_texts.add(question_text)

                if question.get("module_key") != module_key:
                    errors.append("Question module mismatch")

                if question.get("source_type") != "synthetic":
                    errors.append("Question is not synthetic")

                if (
                    question.get("verification_status")
                    != "unverified"
                    or question.get("human_review_status")
                    != "pending"
                ):
                    errors.append(
                        "Question review status is invalid"
                    )

                provenance = question.get(
                    "generation_provenance"
                )

                if (
                    not isinstance(provenance, dict)
                    or not provenance
                ):
                    errors.append(
                        "Missing question provenance"
                    )
                elif provenance.get("mode") not in (
                    "development_fixture",
                    None,
                ):
                    errors.append(
                        "Invalid question provenance mode"
                    )

            if section.get("total_marks") != section_total:
                errors.append("Main question marks mismatch")

            calculated_total += section_total

        if not self._positive_int(paper.get("total_marks")):
            errors.append("Invalid paper total marks")
        elif paper["total_marks"] != calculated_total:
            errors.append("Paper total marks mismatch")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "paper_id": paper_id,
            "calculated_total_marks": calculated_total,
            "unique_question_count": len(seen_ids),
        }

    def export(self, paper):
        """
        Export a validated development paper as JSON.

        Never overwrites an existing file.
        """
        validation = self.validate(paper)

        if not validation["valid"]:
            raise ValueError(
                "Synthetic paper validation failed: "
                + "; ".join(validation["errors"])
            )

        self.export_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            self.export_directory
            / f"{paper['paper_id']}.json"
        )

        # Exclusive creation prevents accidental overwrites.
        # Validation restricts the paper ID to a safe filename.
        with destination.open(
            "x",
            encoding="utf-8",
        ) as file:
            json.dump(
                paper,
                file,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
            file.write("\n")

        return {
            "exported": True,
            "paper_id": paper["paper_id"],
            "file_path": str(destination),
            "release_status": "not_approved",
            "validation": validation,
        }
