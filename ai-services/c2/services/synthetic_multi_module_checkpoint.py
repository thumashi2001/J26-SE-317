
"""M11.3.3C.3 - Eight-module synthetic generation checkpoint.

Development-only integration test runner.
Does not export or approve examination papers.
"""

from services.synthetic_content_expander import SyntheticContentExpander
from services.synthetic_diverse_paper_generator import (
    SyntheticDiversePaperGenerator,
)


class SyntheticMultiModuleCheckpoint:
    def __init__(self, generator=None, expander=None):
        self.generator = (
            generator if generator is not None
            else SyntheticDiversePaperGenerator()
        )
        self.expander = (
            expander if expander is not None
            else SyntheticContentExpander()
        )

    @staticmethod
    def fixture_structure(module_key, module_name):
        return {
            "module_key": module_key,
            "module_name": module_name,
            "total_marks": 100,
            "questions": [
                {
                    "number": number,
                    "total_marks": 25,
                    "subquestion_marks": [5, 10, 10],
                }
                for number in range(1, 5)
            ],
        }

    def run(self, seed=42, mode="development_fixture"):
        if mode != "development_fixture":
            raise ValueError(
                "Multi-module checkpoint is development-only"
            )

        if type(seed) is not int:
            raise ValueError("seed must be an integer")

        bank = self.expander.expanded_bank()
        reports = []
        papers = []

        for index, module in enumerate(bank["modules"]):
            module_key = module["module_key"]
            module_name = module.get(
                "module_name",
                module_key.replace("_", " ").title(),
            )

            structure = self.fixture_structure(
                module_key,
                module_name,
            )

            try:
                result = self.generator.generate(
                    structure,
                    seed=seed + index,
                    mode=mode,
                )

                paper = result["paper"]
                diversity = result["diversity"]
                validation = result["validation"]

                passed = (
                    validation["valid"]
                    and diversity["valid"]
                    and paper["total_marks"] == 100
                    and paper["main_question_count"] == 4
                    and result["generated_question_count"] == 12
                    and diversity["unique_scenario_count"] == 12
                    and paper["release_status"] == "not_approved"
                )

                reports.append({
                    "module_key": module_key,
                    "paper_id": paper["paper_id"],
                    "passed": passed,
                    "total_marks": paper["total_marks"],
                    "main_questions": paper["main_question_count"],
                    "subquestions": result[
                        "generated_question_count"
                    ],
                    "unique_scenarios": diversity[
                        "unique_scenario_count"
                    ],
                    "structural_valid": validation["valid"],
                    "diversity_valid": diversity["valid"],
                    "release_status": paper["release_status"],
                })

                papers.append(paper)

            except (ValueError, KeyError, TypeError) as exc:
                reports.append({
                    "module_key": module_key,
                    "passed": False,
                    "error": str(exc),
                })

        return {
            "mode": mode,
            "module_count": len(bank["modules"]),
            "generated_paper_count": len(papers),
            "passed_count": sum(
                report["passed"] for report in reports
            ),
            "failed_count": sum(
                not report["passed"] for report in reports
            ),
            "all_passed": (
                len(reports) == len(bank["modules"])
                and all(report["passed"] for report in reports)
            ),
            "reports": reports,
            "papers": papers,
            "academic_review_status": "pending",
            "production_ready": False,
        }
