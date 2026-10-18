
"""M11.3.2B - Evidence-based synthetic content bank.

Read-only validation and coverage reporting.
Does not modify historical papers, lecturer reviews, or datasets.
"""

import json
import re
from pathlib import Path

from services.synthetic_diversity_planner import (
    SyntheticDiversityPlanner,
)
from services.past_paper_evidence_analyzer import (
    PastPaperEvidenceAnalyzer,
)


DEFAULT_BANK_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "synthetic_content_bank.json"
)

ALLOWED_TYPES = {
    "apply", "analyze", "evaluate", "design", "explain"
}


def normalize(value):
    return re.sub(r"\s+", " ", value.casefold()).strip()


class SyntheticContentBank:
    def __init__(self, bank_path=None):
        self.bank_path = Path(bank_path or DEFAULT_BANK_PATH)

    def load(self):
        with self.bank_path.open("r", encoding="utf-8") as file:
            bank = json.load(file)

        self.validate(bank)
        return bank

    @staticmethod
    def validate(bank):
        if not isinstance(bank, dict):
            raise ValueError("Content bank must be an object")

        if bank.get("schema_version") != "1.0":
            raise ValueError("Unsupported content bank schema")

        if bank.get("verification_status") != "unverified":
            raise ValueError("Content must remain unverified")

        if bank.get("academic_review_status") != "pending":
            raise ValueError("Academic review must remain pending")

        if bank.get("generation_mode") != "development_fixture":
            raise ValueError("Only development fixtures are allowed")

        planned = SyntheticDiversityPlanner().load_plan()
        evidence = PastPaperEvidenceAnalyzer().load()

        planned_keys = {
            item["module_key"]
            for item in planned["modules"]
        }

        evidence_by_key = {
            item["module_key"]: item
            for item in evidence["modules"]
        }

        modules = bank.get("modules")

        if not isinstance(modules, list):
            raise ValueError("Modules must be a list")

        keys = [m.get("module_key") for m in modules
                if isinstance(m, dict)]

        if len(keys) != len(modules):
            raise ValueError("Invalid module entry")

        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate module key")

        if set(keys) != planned_keys:
            raise ValueError(
                "Content bank must cover exactly the planned modules"
            )

        all_scenarios = set()
        all_tasks = set()

        for module in modules:
            key = module["module_key"]
            evidence_topics = {
                normalize(name)
                for name in evidence_by_key[key]["observed_topics"]
            }

            topics = module.get("topics")

            if not isinstance(topics, list) or not topics:
                raise ValueError(f"Missing topics for {key}")

            seen_topics = set()

            for topic in topics:
                if not isinstance(topic, dict):
                    raise ValueError(f"Invalid topic for {key}")

                name = topic.get("name")

                if not isinstance(name, str) or not name.strip():
                    raise ValueError(f"Invalid topic name for {key}")

                normalized_name = normalize(name)

                if normalized_name in seen_topics:
                    raise ValueError(f"Duplicate topic: {key}/{name}")

                seen_topics.add(normalized_name)

                if topic.get("question_type") not in ALLOWED_TYPES:
                    raise ValueError(
                        f"Invalid question type: {key}/{name}"
                    )

                response_format = topic.get("response_format")

                if (
                    not isinstance(response_format, str)
                    or not response_format.strip()
                ):
                    raise ValueError("Missing response format")

                year = topic.get("source_year")

                if year != evidence_by_key[key]["source_year"]:
                    raise ValueError(
                        f"Historical source year mismatch: {key}"
                    )

                # The authored topic name can be more specific
                # than the observed historical label. This is
                # not proof of taxonomy or syllabus approval.
                if not evidence_topics:
                    raise ValueError(
                        f"No historical topic evidence: {key}"
                    )

                for field, global_seen in (
                    ("scenarios", all_scenarios),
                    ("tasks", all_tasks),
                ):
                    values = topic.get(field)

                    if not isinstance(values, list) or not values:
                        raise ValueError(
                            f"Missing {field}: {key}/{name}"
                        )

                    for value in values:
                        if (
                            not isinstance(value, str)
                            or len(value.strip()) < 25
                        ):
                            raise ValueError(
                                f"Invalid {field} content"
                            )

                        normalized = normalize(value)

                        if normalized in global_seen:
                            raise ValueError(
                                f"Duplicate {field} content"
                            )

                        global_seen.add(normalized)

        return True

    def coverage_report(self):
        bank = self.load()
        plan = SyntheticDiversityPlanner().load_plan()
        policy = plan["diversity_policy"]

        min_scenarios = policy[
            "minimum_distinct_scenarios_per_module"
        ]
        min_variants = policy[
            "minimum_distinct_question_variants_per_module"
        ]

        results = []

        for module in bank["modules"]:
            topics = module["topics"]

            scenarios = sum(
                len(topic["scenarios"])
                for topic in topics
            )
            tasks = sum(
                len(topic["tasks"])
                for topic in topics
            )
            possible_pairs = sum(
                len(topic["scenarios"]) * len(topic["tasks"])
                for topic in topics
            )

            results.append({
                "module_key": module["module_key"],
                "topic_count": len(topics),
                "scenario_count": scenarios,
                "authored_task_count": tasks,
                "possible_scenario_task_pairs": possible_pairs,
                "scenario_shortfall": max(
                    0, min_scenarios - scenarios
                ),
                "task_shortfall": max(
                    0, min_variants - tasks
                ),
                "academically_verified": False,
                "ready_for_160_paper_generation": False,
            })

        return {
            "bank_id": bank["bank_id"],
            "module_count": len(results),
            "topic_count": sum(
                x["topic_count"] for x in results
            ),
            "scenario_count": sum(
                x["scenario_count"] for x in results
            ),
            "authored_task_count": sum(
                x["authored_task_count"] for x in results
            ),
            "possible_scenario_task_pairs": sum(
                x["possible_scenario_task_pairs"]
                for x in results
            ),
            "total_scenario_shortfall": sum(
                x["scenario_shortfall"] for x in results
            ),
            "total_task_shortfall": sum(
                x["task_shortfall"] for x in results
            ),
            "academic_review_status": "pending",
            "ready_for_generation": False,
            "modules": results,
        }
