
"""M11.3.3C.2 - Diversity-enforced synthetic paper generation.

Development-only. Does not write files or approve academic content.
"""

import hashlib
import json
import random

from services.synthetic_content_expander import SyntheticContentExpander
from services.synthetic_diversity_guard import SyntheticDiversityGuard
from services.synthetic_paper_builder import SyntheticPaperBuilder
from services.synthetic_dataset_exporter import SyntheticDatasetExporter


class ExpandedBankProvider:
    """Expose an expanded in-memory bank through the load() interface."""

    def __init__(self, expanded_bank):
        self.bank = expanded_bank

    def load(self):
        return self.bank


class SyntheticDiversePaperGenerator:
    def __init__(self, expander=None, builder=None):
        self.expander = (
            expander if expander is not None
            else SyntheticContentExpander()
        )
        self.builder = (
            builder if builder is not None
            else SyntheticPaperBuilder()
        )

    @staticmethod
    def _hash(data):
        raw = json.dumps(
            data,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:16]

    def generate(
        self,
        structure,
        seed=42,
        mode="development_fixture",
    ):
        # 1. Enforce development-only generation.
        if mode != "development_fixture":
            raise ValueError(
                "Diverse generation is development-only"
            )

        if type(seed) is not int:
            raise ValueError("seed must be an integer")

        # 2. Validate the examination structure.
        SyntheticPaperBuilder._validate_structure(structure)

        # 3. Load the expanded synthetic content bank.
        bank = self.expander.expanded_bank()
        module_key = structure["module_key"]

        module = next(
            (
                item
                for item in bank["modules"]
                if item["module_key"] == module_key
            ),
            None,
        )

        if module is None:
            raise ValueError(
                f"No expanded content for module: {module_key}"
            )

        # 4. Determine required marks slots.
        slots = [
            marks
            for main in structure["questions"]
            for marks in main["subquestion_marks"]
        ]

        # 5. Build one candidate per distinct scenario.
        scenario_candidates = []

        for topic_index, topic in enumerate(
            module["topics"],
            start=1,
        ):
            for scenario_index, scenario in enumerate(
                topic["scenarios"],
                start=1,
            ):
                scenario_candidates.append({
                    "topic": topic,
                    "topic_index": topic_index,
                    "scenario": scenario,
                    "scenario_index": scenario_index,
                })

        # 6. Reject requests exceeding scenario capacity.
        if len(scenario_candidates) < len(slots):
            raise ValueError(
                "Insufficient unique scenarios: "
                f"required {len(slots)}, "
                f"available {len(scenario_candidates)}"
            )

        # 7. Select unique scenarios deterministically.
        rng = random.Random(seed)
        rng.shuffle(scenario_candidates)

        chosen = scenario_candidates[:len(slots)]

        # Match the mark slots required by the paper builder.
        marks_required = sorted(slots, reverse=True)

        questions = []

        # 8. Generate question records.
        for candidate, marks in zip(chosen, marks_required):
            topic = candidate["topic"]

            if not topic.get("tasks"):
                raise ValueError(
                    f"No tasks for topic: {topic['name']}"
                )

            task_index = rng.randrange(
                len(topic["tasks"])
            ) + 1

            task = topic["tasks"][task_index - 1]

            question_text = (
                f"Scenario: {candidate['scenario']}\n"
                f"Task: {task}"
            )

            identity = {
                "module_key": module_key,
                "topic_index": candidate["topic_index"],
                "scenario_index": candidate["scenario_index"],
                "task_index": task_index,
                "marks": marks,
            }

            question = {
                "question_id": (
                    "SYN-DIVERSE-" + self._hash(identity)
                ),
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
                    "generator": (
                        "c2_synthetic_content_adapter_v1"
                    ),
                    "generation_strategy": (
                        "unique_scenario_selection_v1"
                    ),
                    "content_bank_id": bank["bank_id"],
                    "expansion_id": bank[
                        "expansion_provenance"
                    ]["expansion_id"],
                    "topic_index": candidate["topic_index"],
                    "scenario_index": candidate["scenario_index"],
                    "task_index": task_index,
                    "historical_reference_year": (
                        topic["source_year"]
                    ),
                    "historical_reference_role": (
                        "question_style_inspiration_only"
                    ),
                    "marks_assignment": (
                        "experimental_fixture_not_calibrated"
                    ),
                    "mode": mode,
                    "seed": seed,
                },
            }

            questions.append(question)

        # 9. Create the synthetic question batch.
        batch = {
            "schema_version": "1.0",
            "dataset_type": "synthetic_question_drafts",
            "module_key": module_key,
            "generation_mode": mode,
            "batch_id": self._hash({
                "structure": structure,
                "seed": seed,
                "questions": questions,
                "expansion_id": bank[
                    "expansion_provenance"
                ]["expansion_id"],
            }),
            "question_count": len(questions),
            "human_review_required": True,
            "release_status": "not_approved",
            "questions": questions,
        }

        # 10. Assemble the paper using the existing builder.
        paper = self.builder.build(
            batch,
            structure,
            seed=seed,
            mode=mode,
        )

        # 11. Record assembly provenance.
        paper["assembly_provenance"].update({
            "generation_strategy": (
                "unique_scenario_selection_v1"
            ),
            "content_bank_id": bank["bank_id"],
            "expansion_id": bank[
                "expansion_provenance"
            ]["expansion_id"],
            "structure_verification_status": (
                "development_fixture_unverified"
            ),
        })

        # 12. Validate the assembled paper.
        validation = SyntheticDatasetExporter().validate(
            paper
        )

        if not validation["valid"]:
            raise ValueError(
                "Paper validation failed: "
                + "; ".join(validation["errors"])
            )

        # 13. Audit against the expanded bank.
        provider = ExpandedBankProvider(bank)

        guard = SyntheticDiversityGuard(
            content_bank=provider
        )

        diversity = guard.audit_paper(paper)

        if not diversity["valid"]:
            raise ValueError(
                "Paper diversity failed: "
                + "; ".join(diversity["errors"])
            )

        # 14. Return the paper and validation reports.
        # Nothing is written to disk.
        return {
            "paper": paper,
            "validation": validation,
            "diversity": diversity,
            "generated_question_count": len(questions),
            "available_scenario_count": len(
                scenario_candidates
            ),
        }
