
"""M11.2.6.1 - Real synthetic generator to paper builder integration.

Development fixtures only. Does not write files or approve content.
"""

import hashlib
import json
from copy import deepcopy

from services.synthetic_question_generator import (
    SyntheticQuestionGenerator,
)
from services.synthetic_paper_builder import (
    SyntheticPaperBuilder,
)
from services.synthetic_dataset_exporter import (
    SyntheticDatasetExporter,
)


class SyntheticGenerationAdapter:
    def __init__(
        self,
        question_generator=None,
        paper_builder=None,
    ):
        self.question_generator = (
            question_generator
            if question_generator is not None
            else SyntheticQuestionGenerator()
        )
        self.paper_builder = (
            paper_builder
            if paper_builder is not None
            else SyntheticPaperBuilder()
        )

    @staticmethod
    def _required_marks(structure):
        SyntheticPaperBuilder._validate_structure(
            structure
        )

        required = {}

        for main in structure["questions"]:
            for marks in main["subquestion_marks"]:
                required[marks] = (
                    required.get(marks, 0) + 1
                )

        return required

    def build_paper(
        self,
        structure,
        pool_configs,
        seed=42,
        mode="development_fixture",
    ):
        """
        pool_configs maps marks to a generator configuration.

        Each marks pool must have sufficient distinct
        topic/question-type combinations.

        Question text must also be unique across pools.
        """
        if mode != "development_fixture":
            raise ValueError(
                "Real generator integration is development-only"
            )

        if isinstance(seed, bool) or not isinstance(
            seed, int
        ):
            raise ValueError(
                "seed must be an integer"
            )

        required = self._required_marks(structure)

        if not isinstance(pool_configs, dict):
            raise ValueError(
                "pool_configs must be a mapping"
            )

        if set(pool_configs) != set(required):
            raise ValueError(
                "Pool configurations must match "
                "required marks exactly"
            )

        all_questions = []
        source_batches = []
        seen_ids = set()
        seen_texts = set()

        for marks in sorted(required):
            config = deepcopy(pool_configs[marks])

            if config.get("module_key") != (
                structure["module_key"]
            ):
                raise ValueError(
                    "Generator module does not match "
                    "paper structure"
                )

            if config.get("module_name") != (
                structure["module_name"]
            ):
                raise ValueError(
                    "Generator module name mismatch"
                )

            # Force the correct marks for this pool.
            config["marks_options"] = [marks]

            count = required[marks]

            question_batch = (
                self.question_generator.generate(
                    config,
                    count=count,
                    seed=seed + marks,
                    mode=mode,
                )
            )

            if (
                question_batch.get("question_count")
                != count
            ):
                raise ValueError(
                    "Generator returned incorrect count"
                )

            source_batches.append(
                question_batch["batch_id"]
            )

            for question in question_batch["questions"]:
                question_id = question["question_id"]
                question_text = question["question_text"]

                if question["marks"] != marks:
                    raise ValueError(
                        "Generator returned incorrect marks"
                    )

                if question_id in seen_ids:
                    raise ValueError(
                        "Duplicate question ID across pools"
                    )

                if question_text in seen_texts:
                    raise ValueError(
                        "Duplicate question text across pools"
                    )

                seen_ids.add(question_id)
                seen_texts.add(question_text)
                all_questions.append(question)

        fingerprint = json.dumps(
            {
                "structure": structure,
                "source_batches": source_batches,
                "seed": seed,
                "mode": mode,
            },
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )

        combined_batch_id = hashlib.sha256(
            fingerprint.encode("utf-8")
        ).hexdigest()[:16]

        combined_batch = {
            "schema_version": "1.0",
            "dataset_type": "synthetic_question_drafts",
            "module_key": structure["module_key"],
            "generation_mode": mode,
            "batch_id": combined_batch_id,
            "question_count": len(all_questions),
            "human_review_required": True,
            "release_status": "not_approved",
            "questions": all_questions,
        }

        paper = self.paper_builder.build(
            combined_batch,
            structure,
            seed=seed,
            mode=mode,
        )

        validation = SyntheticDatasetExporter().validate(
            paper
        )

        if not validation["valid"]:
            raise ValueError(
                "Integrated paper failed validation: "
                + "; ".join(validation["errors"])
            )

        return {
            "paper": paper,
            "validation": validation,
            "source_batch_ids": source_batches,
            "generated_question_count": len(
                all_questions
            ),
        }
