
"""M11.3.3C.1 - Safe, development-only content bank expansion."""

import json
from copy import deepcopy
from pathlib import Path

from services.synthetic_content_bank import SyntheticContentBank


DEFAULT_EXPANSION_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "synthetic_scenario_expansion.json"
)


class SyntheticContentExpander:
    def __init__(self, content_bank=None, expansion_path=None):
        self.content_bank = (
            content_bank if content_bank is not None
            else SyntheticContentBank()
        )
        self.expansion_path = Path(
            expansion_path
            if expansion_path is not None
            else DEFAULT_EXPANSION_PATH
        )

    def load_expansion(self):
        with self.expansion_path.open(
            "r", encoding="utf-8"
        ) as file:
            return json.load(file)

    def expanded_bank(self):
        original = self.content_bank.load()
        expansion = self.load_expansion()

        if expansion.get("schema_version") != "1.0":
            raise ValueError("Unsupported expansion schema")

        if (
            expansion.get("source_type") != "synthetic"
            or expansion.get("verification_status")
            != "unverified"
            or expansion.get("academic_review_status")
            != "pending"
        ):
            raise ValueError(
                "Expansion must remain synthetic and unverified"
            )

        if not isinstance(
            expansion.get("expansion_id"), str
        ) or not expansion["expansion_id"].strip():
            raise ValueError("Missing expansion ID")

        modules = expansion.get("modules")

        if not isinstance(modules, list):
            raise ValueError("Expansion modules must be a list")

        bank = deepcopy(original)

        bank_modules = {
            module["module_key"]: module
            for module in bank["modules"]
        }

        seen_modules = set()

        for expanded_module in modules:
            if not isinstance(expanded_module, dict):
                raise ValueError("Invalid expansion module")

            module_key = expanded_module.get("module_key")

            if module_key in seen_modules:
                raise ValueError("Duplicate expansion module")

            seen_modules.add(module_key)

            if module_key not in bank_modules:
                raise ValueError(
                    f"Unknown expansion module: {module_key}"
                )

            target_module = bank_modules[module_key]

            topics = {
                topic["name"]: topic
                for topic in target_module["topics"]
            }

            expanded_topics = expanded_module.get("topics")

            if not isinstance(expanded_topics, list):
                raise ValueError("Invalid expansion topics")

            seen_topics = set()

            for expanded_topic in expanded_topics:
                if not isinstance(expanded_topic, dict):
                    raise ValueError("Invalid expansion topic")

                name = expanded_topic.get("name")

                if name in seen_topics:
                    raise ValueError("Duplicate expansion topic")

                seen_topics.add(name)

                if name not in topics:
                    raise ValueError(
                        f"Unknown expansion topic: {name}"
                    )

                scenarios = expanded_topic.get("scenarios")

                if not isinstance(scenarios, list):
                    raise ValueError("Invalid expansion scenarios")

                target_topic = topics[name]
                existing = {
                    text.strip().casefold()
                    for text in target_topic["scenarios"]
                }

                for scenario in scenarios:
                    if (
                        not isinstance(scenario, str)
                        or len(scenario.strip()) < 30
                    ):
                        raise ValueError(
                            "Expansion scenario is too short"
                        )

                    normalized = scenario.strip().casefold()

                    if normalized in existing:
                        raise ValueError(
                            "Duplicate scenario in expansion"
                        )

                    existing.add(normalized)
                    target_topic["scenarios"].append(
                        scenario.strip()
                    )

        # Ensure no duplicates anywhere in the resulting bank,
        # including across different modules and topics.
        all_scenarios = set()

        for module in bank["modules"]:
            for topic in module["topics"]:
                for scenario in topic["scenarios"]:
                    normalized = scenario.strip().casefold()

                    if normalized in all_scenarios:
                        raise ValueError(
                            "Duplicate scenario across content bank"
                        )

                    all_scenarios.add(normalized)

        # Revalidate the merged bank using the existing rules.
        SyntheticContentBank.validate(bank)

        bank["expansion_provenance"] = {
            "expansion_id": expansion["expansion_id"],
            "source_type": "synthetic",
            "verification_status": "unverified",
            "academic_review_status": "pending",
            "purpose": "development_scenario_diversity",
        }

        return bank

    def coverage_report(self):
        bank = self.expanded_bank()
        modules = []

        for module in bank["modules"]:
            scenario_count = sum(
                len(topic["scenarios"])
                for topic in module["topics"]
            )

            task_count = sum(
                len(topic["tasks"])
                for topic in module["topics"]
            )

            pair_count = sum(
                len(topic["scenarios"]) * len(topic["tasks"])
                for topic in module["topics"]
            )

            modules.append({
                "module_key": module["module_key"],
                "scenario_count": scenario_count,
                "authored_task_count": task_count,
                "possible_scenario_task_pairs": pair_count,
                "supports_12_unique_scenarios": (
                    scenario_count >= 12
                ),
            })

        return {
            "module_count": len(modules),
            "total_scenarios": sum(
                module["scenario_count"]
                for module in modules
            ),
            "total_authored_tasks": sum(
                module["authored_task_count"]
                for module in modules
            ),
            "total_possible_pairs": sum(
                module["possible_scenario_task_pairs"]
                for module in modules
            ),
            "modules": modules,
            "academic_review_status": "pending",
            "production_ready": False,
        }
