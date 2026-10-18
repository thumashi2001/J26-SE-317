
"""Plan multi-module synthetic examination dataset diversity.

This service calculates minimum unique question and scenario
requirements. It does not generate papers or change academic
verification statuses.
"""

import json
from pathlib import Path


DEFAULT_PLAN_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "synthetic_dataset_plan.json"
)


class SyntheticDiversityPlanner:
    def __init__(self, plan_path=None):
        self.plan_path = Path(
            plan_path or DEFAULT_PLAN_PATH
        )

    def load_plan(self):
        with self.plan_path.open(
            "r", encoding="utf-8"
        ) as file:
            plan = json.load(file)

        self.validate_plan(plan)
        return plan

    @staticmethod
    def validate_plan(plan):
        if not isinstance(plan, dict):
            raise ValueError("Dataset plan must be an object")

        if plan.get("schema_version") != "1.0":
            raise ValueError("Unsupported plan schema version")

        if plan.get("generation_mode") != "development_fixture":
            raise ValueError(
                "Planning must use development_fixture mode"
            )

        if plan.get("production_generation_enabled") is not False:
            raise ValueError(
                "Production generation must remain disabled"
            )

        if plan.get("academic_review_required") is not True:
            raise ValueError(
                "Academic review must remain required"
            )

        modules = plan.get("modules")

        if not isinstance(modules, list) or not modules:
            raise ValueError("Modules must be a nonempty list")

        policy = plan.get("diversity_policy")

        if not isinstance(policy, dict):
            raise ValueError("Missing diversity policy")

        for key in (
            "allow_repeated_question_ids",
            "allow_repeated_question_text",
            "allow_repeated_scenario_ids",
        ):
            if policy.get(key) is not False:
                raise ValueError(
                    f"Repeated content must be prohibited: {key}"
                )

        for key in (
            "minimum_distinct_scenarios_per_module",
            "minimum_distinct_question_variants_per_module",
        ):
            value = policy.get(key)

            if type(value) is not int or value < 1:
                raise ValueError(
                    f"{key} must be a positive integer"
                )

        seen = set()
        total = 0

        for module in modules:
            if not isinstance(module, dict):
                raise ValueError(
                    "Each module must be an object"
                )

            key = module.get("module_key")
            name = module.get("module_name")
            count = module.get("target_papers")

            if not isinstance(key, str) or not key.strip():
                raise ValueError("Invalid module key")

            if not isinstance(name, str) or not name.strip():
                raise ValueError("Invalid module name")

            if key in seen:
                raise ValueError(
                    f"Duplicate module key: {key}"
                )

            if type(count) is not int or count < 1:
                raise ValueError(
                    f"Invalid paper target for {key}"
                )

            if module.get("configuration_status") != (
                "requires_academic_verification"
            ):
                raise ValueError(
                    f"Unverified configuration expected: {key}"
                )

            seen.add(key)
            total += count

        expected = plan.get("target_total_papers")

        if type(expected) is not int or expected != total:
            raise ValueError(
                "Target total does not match module totals"
            )

        return True

    def build_report(self, subquestions_per_paper=None):
        plan = self.load_plan()
        policy = plan["diversity_policy"]

        counts = subquestions_per_paper or {}

        modules = []
        total_question_slots = 0

        for module in plan["modules"]:
            key = module["module_key"]
            target = module["target_papers"]
            slots = counts.get(key)

            if slots is not None:
                if type(slots) is not int or slots < 1:
                    raise ValueError(
                        f"Invalid subquestion count for {key}"
                    )

                required_questions = target * slots
                total_question_slots += required_questions
            else:
                required_questions = None

            modules.append({
                "module_key": key,
                "module_name": module["module_name"],
                "semester": module.get("semester"),
                "target_papers": target,
                "subquestions_per_paper": slots,
                "required_unique_questions": required_questions,
                "minimum_distinct_scenarios": policy[
                    "minimum_distinct_scenarios_per_module"
                ],
                "minimum_distinct_question_variants": policy[
                    "minimum_distinct_question_variants_per_module"
                ],
                "configuration_status": module[
                    "configuration_status"
                ],
                "ready_for_generation": False,
            })

        all_structures_known = all(
            item["subquestions_per_paper"] is not None
            for item in modules
        )

        return {
            "plan_id": plan["plan_id"],
            "target_total_papers": plan[
                "target_total_papers"
            ],
            "module_count": len(modules),
            "known_total_question_slots": total_question_slots,
            "all_structures_known": all_structures_known,
            "academic_review_required": True,
            "production_generation_enabled": False,
            "modules": modules,
        }
