
"""M11.3.3A - Integrate authored content with the synthetic paper builder.

Development fixtures only. No files are written, and no academic
approval is inferred from successful validation.
"""

import hashlib
import json
import random
from collections import Counter

from services.synthetic_content_bank import SyntheticContentBank
from services.synthetic_paper_builder import SyntheticPaperBuilder
from services.synthetic_dataset_exporter import SyntheticDatasetExporter


class SyntheticContentAdapter:
    def __init__(self, content_bank=None, paper_builder=None):
        self.content_bank = (
            content_bank if content_bank is not None
            else SyntheticContentBank()
        )
        self.paper_builder = (
            paper_builder if paper_builder is not None
            else SyntheticPaperBuilder()
        )

    @staticmethod
    def _fingerprint(value):
        serialized = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()[:16]

    def build_paper(
        self,
        structure,
        seed=42,
        mode="development_fixture",
    ):
        if mode != "development_fixture":
            raise ValueError(
                "Content bank integration is development-only"
            )

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")

        SyntheticPaperBuilder._validate_structure(structure)

        bank = self.content_bank.load()
        module_key = structure["module_key"]

        module = next(
            (
                item for item in bank["modules"]
                if item["module_key"] == module_key
            ),
            None,
        )

        if module is None:
            raise ValueError(
                f"No content bank for module: {module_key}"
            )

        required_marks = Counter(
            marks
            for main in structure["questions"]
            for marks in main["subquestion_marks"]
        )

        # The bank has no mark-specific questions yet.
        # Assigning marks here is an experimental development
        # fixture operation, not academic mark calibration.
        candidates = []

        for topic_index, topic in enumerate(
            module["topics"], start=1
        ):
            for scenario_index, scenario in enumerate(
                topic["scenarios"], start=1
            ):
                for task_index, task in enumerate(
                    topic["tasks"], start=1
                ):
                    candidates.append({
                        "topic": topic,
                        "topic_index": topic_index,
                        "scenario": scenario,
                        "scenario_index": scenario_index,
                        "task": task,
                        "task_index": task_index,
                    })

        required_count = sum(required_marks.values())

        if len(candidates) < required_count:
            raise ValueError(
                "Insufficient distinct scenario/task pairs: "
                f"required {required_count}, "
                f"available {len(candidates)}"
            )

        rng = random.Random(seed)
        rng.shuffle(candidates)
        selected = candidates[:required_count]

        # Allocate exact marks required by the caller's
        # experimental structure. Do not modify question
        # text or marks later in the paper builder.
        mark_slots = sorted(
            (
                marks
                for marks, count in required_marks.items()
                for _ in range(count)
            ),
            reverse=True,
        )

        questions = []
        seen_texts = set()

        for candidate, marks in zip(selected, mark_slots):
            topic = candidate["topic"]

            question_text = (
                f"Scenario: {candidate['scenario']}\n"
                f"Task: {candidate['task']}"
            )

            if question_text in seen_texts:
                raise ValueError("Duplicate generated question text")

            seen_texts.add(question_text)

            question_id = (
                "SYN-CONTENT-"
                + self._fingerprint({
                    "module_key": module_key,
                    "topic": topic["name"],
                    "scenario": candidate["scenario"],
                    "task": candidate["task"],
                    "marks": marks,
                })
            )

            questions.append({
                "question_id": question_id,
                "module_key": module_key,
                "question_text": question_text,
                "marks": marks,
                "source_type": "synthetic",
                "verification_status": "unverified",
                "human_review_status": "pending",
                "topic_name": topic["name"],
                "question_type": topic["question_type"],
                "response_format": topic["response_format"],
                "generation_provenance": {
                    "generator": "c2_synthetic_content_adapter_v1",
                    "content_bank_id": bank["bank_id"],
                    "historical_reference_year": (
                        topic["source_year"]
                    ),
                    "historical_reference_role": (
                        "question_style_inspiration_only"
                    ),
                    "topic_index": candidate["topic_index"],
                    "scenario_index": candidate["scenario_index"],
                    "task_index": candidate["task_index"],
                    "marks_assignment": (
                        "experimental_fixture_not_calibrated"
                    ),
                    "mode": mode,
                    "seed": seed,
                },
            })

        batch_id = self._fingerprint({
            "module_key": module_key,
            "structure": structure,
            "seed": seed,
            "content_bank_id": bank["bank_id"],
            "questions": questions,
        })

        batch = {
            "schema_version": "1.0",
            "dataset_type": "synthetic_question_drafts",
            "module_key": module_key,
            "generation_mode": mode,
            "batch_id": batch_id,
            "question_count": len(questions),
            "human_review_required": True,
            "release_status": "not_approved",
            "questions": questions,
        }

        paper = self.paper_builder.build(
            batch,
            structure,
            seed=seed,
            mode=mode,
        )

        # The structure is an integration fixture, not an
        # academically verified historical exam blueprint.
        paper["assembly_provenance"][
            "structure_verification_status"
        ] = "development_fixture_unverified"
        paper["assembly_provenance"][
            "content_bank_id"
        ] = bank["bank_id"]

        validation = SyntheticDatasetExporter().validate(paper)

        if not validation["valid"]:
            raise ValueError(
                "Content bank paper validation failed: "
                + "; ".join(validation["errors"])
            )

        return {
            "paper": paper,
            "validation": validation,
            "batch": batch,
            "generated_question_count": len(questions),
            "available_content_pairs": len(candidates),
        }
