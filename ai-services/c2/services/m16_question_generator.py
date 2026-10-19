"""M16.2 — Reproducible synthetic question development dataset generator.

Development fixtures only. Never modifies authentic question repositories,
lecturer verification records, or production generation policies.
"""

import hashlib
import json
import random
import re
from copy import deepcopy
from pathlib import Path

from services.synthetic_question_generator import QUESTION_BLOOM_LEVELS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_M16_BANK_PATH = (
    PROJECT_ROOT / "config" / "m16_expanded_content_bank.json"
)


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class M16ContentExpander:
    """Provides the validated expanded content bank for M16 synthetic questions."""

    def __init__(self, bank_path=None):
        self.bank_path = Path(bank_path or DEFAULT_M16_BANK_PATH)

    def load_bank(self):
        with self.bank_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def expanded_bank(self):
        return self.load_bank()


class M16QuestionGenerator:
    """Generate distinct scenario/task-based synthetic question fixtures."""

    def __init__(self, expander=None):
        self.expander = expander or M16ContentExpander()

    def generate(self, seed=42, max_per_module=100):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")

        if (
            isinstance(max_per_module, bool)
            or not isinstance(max_per_module, int)
            or max_per_module <= 0
        ):
            raise ValueError("max_per_module must be a positive integer")

        bank = self.expander.expanded_bank()
        rng = random.Random(seed)

        result = {
            "schema_version": "1.0",
            "dataset_type": "synthetic_development_questions",
            "generation_mode": "development_fixture",
            "seed": seed,
            "source_type": "synthetic",
            "verification_status": "unverified",
            "modules": [],
        }

        seen_texts = set()
        seen_ids = set()

        for module_index, module in enumerate(bank["modules"]):
            module_key = module["module_key"]
            candidates = []

            for topic_index, topic in enumerate(module["topics"], 1):
                topic_name = topic["name"]
                question_type = topic["question_type"]
                bloom_level = QUESTION_BLOOM_LEVELS[question_type]

                for scenario_index, scenario in enumerate(
                    topic["scenarios"], 1
                ):
                    for task_index, task in enumerate(
                        topic["tasks"], 1
                    ):
                        question_text = (
                            f"Scenario: {scenario.strip()}\n"
                            f"Task: {task.strip()}"
                        )

                        normalized = " ".join(
                            question_text.casefold().split()
                        )

                        if normalized in seen_texts:
                            continue

                        identity = {
                            "module_key": module_key,
                            "topic": topic_name,
                            "scenario": scenario,
                            "task": task,
                        }

                        question_id = (
                            "SYN-M16-"
                            + _slug(module_key).upper()
                            + "-"
                            + _fingerprint(identity)[:12].upper()
                        )

                        if question_id in seen_ids:
                            raise ValueError(
                                f"Duplicate question ID: {question_id}"
                            )

                        candidates.append({
                            "question_id": question_id,
                            "module_key": module_key,
                            "topic": topic_name,
                            "topic_id": (
                                f"provisional_{_slug(topic_name)}"
                            ),
                            "question_text": question_text,
                            "question_type": question_type,
                            "bloom_level": bloom_level,
                            "source_type": "synthetic",
                            "generation_method": (
                                "content_bank_scenario_task"
                            ),
                            "generation_seed": seed,
                            "generation_mode": "development_fixture",
                            "verification_status": "unverified",
                            "human_review_status": "pending",
                            "label_source": "synthetic_generation",
                            "taxonomy_verification_status": "unverified",
                            "exam_structure_verification_status": (
                                "unverified"
                            ),
                            "scenario_group_id": (
                                f"{module_key}:"
                                f"{topic_index}:"
                                f"{scenario_index}"
                            ),
                            "task_group_id": (
                                f"{module_key}:"
                                f"{topic_index}:"
                                f"{task_index}"
                            ),
                            "template_family_id": (
                                f"{_slug(topic_name)}:{question_type}:t{task_index}"
                            ),
                            "content_source": "synthetic_content_bank",
                            "provisional_topic": True,
                            "source_content_bank_id": bank.get(
                                "bank_id",
                                "c2_m16_expanded_synthetic_content_bank_v1"
                            ),
                            "marks": None,
                            "difficulty": "unassessed",
                            "academic_quality_status": "not_evaluated",
                        })

            module_rng = random.Random(seed + module_index * 1000)
            module_rng.shuffle(candidates)
            selected = candidates[:max_per_module]

            for question in selected:
                normalized = " ".join(
                    question["question_text"].casefold().split()
                )
                seen_texts.add(normalized)
                seen_ids.add(question["question_id"])

            result["modules"].append({
                "module_key": module_key,
                "question_count": len(selected),
                "available_candidate_count": len(candidates),
                "requested_maximum": max_per_module,
                "target_reached": len(selected) >= max_per_module,
                "questions": selected,
            })

        result["total_questions"] = sum(
            module["question_count"]
            for module in result["modules"]
        )

        return deepcopy(result)
