
"""M11.2.3 - Synthetic examination paper draft builder."""

import hashlib
import json
import random
from copy import deepcopy

from services.synthetic_dataset_readiness import (
    SyntheticDatasetReadiness,
)


class SyntheticPaperBuilder:
    """
    Assemble existing synthetic question drafts into a paper.

    The builder never changes question marks or text.
    It never writes files or approves academic content.
    """

    def __init__(self, readiness=None):
        self.readiness = readiness

    @staticmethod
    def _positive_int(value, name):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(
                f"{name} must be a positive integer"
            )

    @classmethod
    def _validate_structure(cls, structure):
        if not isinstance(structure, dict):
            raise ValueError(
                "Paper structure must be an object"
            )

        for field in ("module_key", "module_name"):
            if (
                not isinstance(structure.get(field), str)
                or not structure[field].strip()
            ):
                raise ValueError(
                    f"Missing or invalid {field}"
                )

        cls._positive_int(
            structure.get("total_marks"),
            "total_marks",
        )

        sections = structure.get("questions")

        if not isinstance(sections, list) or not sections:
            raise ValueError(
                "questions must be a nonempty list"
            )

        numbers = set()
        total = 0

        for section in sections:
            if not isinstance(section, dict):
                raise ValueError(
                    "Invalid main question"
                )

            number = section.get("number")

            cls._positive_int(
                number,
                "question number",
            )

            if number in numbers:
                raise ValueError(
                    "Duplicate main question number"
                )

            numbers.add(number)

            cls._positive_int(
                section.get("total_marks"),
                "main question total_marks",
            )

            subquestion_marks = section.get(
                "subquestion_marks"
            )

            if (
                not isinstance(subquestion_marks, list)
                or not subquestion_marks
            ):
                raise ValueError(
                    "Each main question needs subquestion_marks"
                )

            for marks in subquestion_marks:
                cls._positive_int(
                    marks,
                    "subquestion marks",
                )

            if sum(subquestion_marks) != section["total_marks"]:
                raise ValueError(
                    f"Main question {number} marks do not add up"
                )

            total += section["total_marks"]

        if total != structure["total_marks"]:
            raise ValueError(
                "Paper total marks do not match main questions"
            )

    @staticmethod
    def _validate_batch(batch, module_key, mode):
        if not isinstance(batch, dict):
            raise ValueError(
                "Question batch must be an object"
            )

        if batch.get("dataset_type") != (
            "synthetic_question_drafts"
        ):
            raise ValueError(
                "Expected a synthetic question draft batch"
            )

        if batch.get("module_key") != module_key:
            raise ValueError(
                "Question batch module mismatch"
            )

        if batch.get("generation_mode") != mode:
            raise ValueError(
                "Question batch mode mismatch"
            )

        if batch.get("release_status") != "not_approved":
            raise ValueError(
                "Question batch must remain unapproved"
            )

        questions = batch.get("questions")

        if not isinstance(questions, list):
            raise ValueError(
                "Question batch must contain a question list"
            )

        if (
            batch.get("question_count") != len(questions)
        ):
            raise ValueError(
                "Question batch count mismatch"
            )

        ids = set()
        texts = set()

        for question in questions:
            if not isinstance(question, dict):
                raise ValueError(
                    "Invalid question record"
                )

            question_id = question.get("question_id")
            question_text = question.get("question_text")

            if (
                not isinstance(question_id, str)
                or not question_id.strip()
                or question_id in ids
            ):
                raise ValueError(
                    "Missing or duplicate question ID"
                )

            if (
                not isinstance(question_text, str)
                or not question_text.strip()
                or question_text in texts
            ):
                raise ValueError(
                    "Missing or duplicate question text"
                )

            ids.add(question_id)
            texts.add(question_text)

            if (
                question.get("source_type") != "synthetic"
                or question.get("module_key") != module_key
            ):
                raise ValueError(
                    "Question source or module mismatch"
                )

            if (
                question.get("verification_status")
                != "unverified"
                or question.get("human_review_status")
                != "pending"
            ):
                raise ValueError(
                    "Question must be pending academic review"
                )

            if (
                not isinstance(
                    question.get("generation_provenance"),
                    dict,
                )
                or not question["generation_provenance"]
            ):
                raise ValueError(
                    "Missing question generation provenance"
                )

            marks = question.get("marks")

            if (
                isinstance(marks, bool)
                or not isinstance(marks, int)
                or marks <= 0
            ):
                raise ValueError(
                    "Question marks must be positive integers"
                )

        return questions

    def _check_production_readiness(self, module_key):
        readiness = (
            self.readiness
            if self.readiness is not None
            else SyntheticDatasetReadiness()
        )

        report = readiness.report()

        module = next(
            (
                item
                for item in report["modules"]
                if item["module_key"] == module_key
            ),
            None,
        )

        if (
            module is None
            or not module.get("ready_for_generation", False)
        ):
            raise ValueError(
                "Production paper assembly blocked: "
                "module academic configuration is not ready"
            )

        # Readiness alone is insufficient to prove that an
        # arbitrary caller-supplied structure is approved.
        raise ValueError(
            "Production paper assembly blocked: "
            "verified structure binding is not implemented"
        )

    def build(
        self,
        batch,
        structure,
        seed=42,
        mode="development_fixture",
    ):
        """
        Assemble a paper using existing question marks.

        If a required marks combination cannot be satisfied,
        raise an error instead of changing question marks.
        """
        if mode not in (
            "production",
            "development_fixture",
        ):
            raise ValueError(
                "Unsupported paper assembly mode"
            )

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(
                "seed must be an integer"
            )

        self._validate_structure(structure)

        module_key = structure["module_key"]

        if mode == "production":
            self._check_production_readiness(module_key)

        questions = self._validate_batch(
            batch,
            module_key,
            mode,
        )

        # Collect the exact marks required for all subquestions.
        slots = []

        for main_question in structure["questions"]:
            for index, marks in enumerate(
                main_question["subquestion_marks"],
                start=1,
            ):
                slots.append({
                    "main_number": main_question["number"],
                    "sub_number": index,
                    "marks": marks,
                })

        rng = random.Random(seed)

        pools = {}

        for question in questions:
            pools.setdefault(
                question["marks"],
                [],
            ).append(question)

        for pool in pools.values():
            rng.shuffle(pool)

        # Verify every marks requirement before consuming items.
        required_counts = {}

        for slot in slots:
            marks = slot["marks"]
            required_counts[marks] = (
                required_counts.get(marks, 0) + 1
            )

        for marks, required in required_counts.items():
            available = len(pools.get(marks, []))

            if available < required:
                raise ValueError(
                    "Insufficient synthetic questions "
                    f"worth {marks} marks: "
                    f"required {required}, available {available}"
                )

        assembled = []

        for main_question in structure["questions"]:
            subquestions = []

            for index, marks in enumerate(
                main_question["subquestion_marks"],
                start=1,
            ):
                selected = deepcopy(
                    pools[marks].pop()
                )

                subquestions.append({
                    "label": chr(96 + index)
                    if index <= 26 else str(index),
                    "marks": marks,
                    "question": selected,
                })

            assembled.append({
                "number": main_question["number"],
                "total_marks": main_question["total_marks"],
                "subquestions": subquestions,
            })

        paper_marks = sum(
            item["total_marks"]
            for item in assembled
        )

        if paper_marks != structure["total_marks"]:
            raise ValueError(
                "Assembled paper marks mismatch"
            )

        fingerprint = json.dumps(
            {
                "batch_id": batch.get("batch_id"),
                "structure": structure,
                "seed": seed,
                "mode": mode,
            },
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )

        paper_id = (
            "SYN-PAPER-"
            + hashlib.sha256(
                fingerprint.encode("utf-8")
            ).hexdigest()[:16]
        )

        return {
            "schema_version": "1.0",
            "dataset_type": "synthetic_exam_paper_draft",
            "paper_id": paper_id,
            "module_key": module_key,
            "module_name": structure["module_name"],
            "generation_mode": mode,
            "source_type": "synthetic",
            "verification_status": "unverified",
            "human_review_status": "pending",
            "release_status": "not_approved",
            "total_marks": paper_marks,
            "main_question_count": len(assembled),
            "questions": assembled,
            "assembly_provenance": {
                "builder": "c2_synthetic_paper_builder_v1",
                "source_batch_id": batch.get("batch_id"),
                "seed": seed,
                "mode": mode,
            },
        }
