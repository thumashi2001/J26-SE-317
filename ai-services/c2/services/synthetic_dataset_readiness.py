
"""M11.2.1 - Read-only synthetic dataset readiness reporting."""

from collections import Counter

from services.module_registry import ModuleRegistry
from services.synthetic_rules import SyntheticRules
from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)


class SyntheticDatasetReadiness:
    """Report generation prerequisites without modifying source data."""

    def __init__(
        self,
        registry=None,
        rules=None,
        review_repository=None,
    ):
        self.registry = (
            registry if registry is not None
            else ModuleRegistry()
        )
        self.rules = (
            rules if rules is not None
            else SyntheticRules(registry=self.registry)
        )
        self.review_repository = (
            review_repository
            if review_repository is not None
            else SyllabusTopicReviewRepository()
        )

    def report(self):
        modules = self.registry.get_all()
        reviews = self.review_repository.list_reviews()

        if not isinstance(reviews, list):
            raise ValueError("Review repository must return a list")

        reviews_by_module = {}

        for review in reviews:
            if not isinstance(review, dict):
                continue

            key = review.get("module_key")
            if isinstance(key, str):
                reviews_by_module.setdefault(key, []).append(review)

        defaults = self.rules.rules.get("generation_defaults", {})
        policy = self.rules.rules.get("generation_policy", {})
        quality = self.rules.rules.get("quality_rules", {})

        target = defaults.get("target_papers_per_module")

        valid_target = (
            isinstance(target, int)
            and not isinstance(target, bool)
            and target > 0
        )

        module_reports = []

        for module in modules:
            key = module["module_key"]
            decisions = reviews_by_module.get(key, [])

            counts = Counter(
                review.get("review_decision")
                for review in decisions
            )

            approved = counts.get("approved", 0)
            rejected = counts.get("rejected", 0)

            topics = module.get("topics") or []
            structure = module.get("exam_structure")

            missing = []

            if not module.get("module_code"):
                missing.append("module_code")

            # Do not interpret lecturer-approved candidates as
            # automatically populated module taxonomy topics.
            if not topics:
                missing.append("verified_module_topics")

            # A nonempty structure is not proof of verification.
            # Require an explicit verified status.
            if not isinstance(structure, dict) or not structure:
                missing.append("exam_structure")
            elif structure.get("verification_status") != "verified":
                missing.append("verified_exam_structure")

            if not valid_target:
                missing.append("target_papers_per_module")

            if not defaults.get("difficulty_distribution"):
                missing.append("difficulty_distribution")

            if not defaults.get("blooms_taxonomy_distribution"):
                missing.append("blooms_taxonomy_distribution")

            if not defaults.get("question_type_distribution"):
                missing.append("question_type_distribution")

            if (
                policy.get("require_human_review_before_release")
                is True
                or quality.get("require_human_review_before_release")
                is True
            ):
                review_required = True
            else:
                review_required = False

            module_reports.append({
                "module_key": key,
                "module_name": module["module_name"],
                "module_code": module.get("module_code"),
                "approved_syllabus_candidates": approved,
                "rejected_syllabus_candidates": rejected,
                "configured_topics": len(topics),
                "has_exam_structure": bool(structure),
                "ready_for_generation": len(missing) == 0,
                "missing_requirements": missing,
                "human_review_required_before_release":
                    review_required,
            })

        ready_count = sum(
            item["ready_for_generation"]
            for item in module_reports
        )

        return {
            "schema_version": "1.0",
            "report_type": "synthetic_dataset_readiness",
            "total_modules": len(module_reports),
            "ready_modules": ready_count,
            "blocked_modules": len(module_reports) - ready_count,
            "saved_review_decisions": len(reviews),
            "approved_review_decisions": sum(
                item["approved_syllabus_candidates"]
                for item in module_reports
            ),
            "rejected_review_decisions": sum(
                item["rejected_syllabus_candidates"]
                for item in module_reports
            ),
            "target_papers_per_module":
                target if valid_target else None,
            "modules": module_reports,
            "note": (
                "This report checks configuration readiness only. "
                "It does not generate questions or certify "
                "academic content quality."
            ),
        }
