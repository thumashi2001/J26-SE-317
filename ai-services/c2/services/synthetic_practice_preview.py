
"""M12.4.1 - Internal synthetic practice paper preview.

Development-only. Uses the existing expanded synthetic content bank.
No file writes, approvals, or publication to the student question bank.
"""

from services.synthetic_content_expander import SyntheticContentExpander
from services.synthetic_diverse_paper_generator import (
    SyntheticDiversePaperGenerator,
)
from services.synthetic_multi_module_checkpoint import (
    SyntheticMultiModuleCheckpoint,
)


class SyntheticPracticePreview:
    def __init__(self, generator=None, expander=None):
        self.generator = (
            generator
            if generator is not None
            else SyntheticDiversePaperGenerator()
        )
        self.expander = (
            expander
            if expander is not None
            else SyntheticContentExpander()
        )

    def available_modules(self):
        bank = self.expander.expanded_bank()

        return [
            {
                "module_key": module["module_key"],
                "module_name": module.get(
                    "module_name",
                    module["module_key"]
                    .replace("_", " ")
                    .title(),
                ),
            }
            for module in bank["modules"]
        ]

    def generate(
        self,
        module_key,
        seed=42,
        mode="development_fixture",
    ):
        if mode != "development_fixture":
            raise ValueError(
                "Synthetic practice preview is development-only"
            )

        if type(seed) is not int:
            raise ValueError("seed must be an integer")

        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("module_key is required")

        modules = self.available_modules()

        selected_module = next(
            (
                module
                for module in modules
                if module["module_key"] == module_key
            ),
            None,
        )

        if selected_module is None:
            raise ValueError(
                f"Unsupported module: {module_key}"
            )

        structure = (
            SyntheticMultiModuleCheckpoint.fixture_structure(
                module_key,
                selected_module["module_name"],
            )
        )

        result = self.generator.generate(
            structure,
            seed=seed,
            mode=mode,
        )

        paper = result["paper"]
        validation = result["validation"]
        diversity = result["diversity"]

        if not validation["valid"]:
            raise ValueError(
                "Synthetic paper failed structural validation"
            )

        if not diversity["valid"]:
            raise ValueError(
                "Synthetic paper failed diversity validation"
            )

        if paper["release_status"] != "not_approved":
            raise ValueError(
                "Unexpected synthetic paper release status"
            )

        if paper["total_marks"] != 100:
            raise ValueError(
                "Unexpected development fixture marks"
            )

        if result["generated_question_count"] != 12:
            raise ValueError(
                "Unexpected development fixture question count"
            )

        if diversity["unique_scenario_count"] != 12:
            raise ValueError(
                "Synthetic scenarios are not unique"
            )

        return {
            "preview_type": "synthetic_development_preview",
            "module_key": module_key,
            "module_name": selected_module["module_name"],
            "paper": paper,
            "structural_valid": True,
            "diversity_valid": True,
            "unique_scenario_count": 12,
            "question_count": 12,
            "total_marks": paper["total_marks"],
            "academic_review_status": "pending",
            "release_status": "not_approved",
            "production_ready": False,
            "student_release_allowed": False,
            "authentic_past_paper": False,
            "official_exam_structure_verified": False,
            "limitations": [
                "This paper contains synthetic, unverified questions.",
                "The examination structure is an experimental development fixture.",
                "Academic review and approval are required before student release.",
                "This preview is not an official or predicted examination paper.",
            ],
        }
