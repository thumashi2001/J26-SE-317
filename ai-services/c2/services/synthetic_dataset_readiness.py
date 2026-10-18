
"""M11.2.1 - Read-only synthetic dataset readiness reporting."""

import json
from collections import Counter
from pathlib import Path

from services.module_registry import ModuleRegistry
from services.synthetic_rules import SyntheticRules
from services.topic_taxonomy import TopicTaxonomy
from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EXAM_STRUCTURES_PATH = (
    ROOT / "config" / "exam_structures.json"
)

# Canonical module keys are defined in modules.json.
# These aliases support existing configuration differences.
EXAM_STRUCTURE_KEY_ALIASES = {
    "case_studies_software_engineering":
        "case_studies_in_software_engineering",
    "software_engineering_process_quality_management":
        "software_engineering_process_and_quality_management",
}

# The topic taxonomy configuration currently uses the same
# two legacy module keys as exam_structures.json.
TAXONOMY_KEY_ALIASES = EXAM_STRUCTURE_KEY_ALIASES.copy()


class SyntheticDatasetReadiness:
    """
    Report synthetic examination dataset generation readiness.

    Data sources:
    - modules.json: registered modules and module codes
    - topic_taxonomies.json: syllabus topics and verification
    - exam_structures.json: examination structures and verification
    - synthetic_rules.json: generation policies and defaults
    - review_decisions.json: saved lecturer review decisions

    This service is read-only. It does not generate questions,
    modify configuration files, or change lecturer decisions.
    """

    def __init__(
        self,
        registry=None,
        rules=None,
        review_repository=None,
        taxonomy=None,
        exam_structures_path=None,
    ):
        self.registry = (
            registry
            if registry is not None
            else ModuleRegistry()
        )

        self.rules = (
            rules
            if rules is not None
            else SyntheticRules(registry=self.registry)
        )

        self.review_repository = (
            review_repository
            if review_repository is not None
            else SyllabusTopicReviewRepository()
        )

        self.taxonomy = (
            taxonomy
            if taxonomy is not None
            else TopicTaxonomy()
        )

        self.exam_structures_path = Path(
            exam_structures_path
            if exam_structures_path is not None
            else DEFAULT_EXAM_STRUCTURES_PATH
        )

    def _load_exam_structures(self):
        """
        Load examination structures without modifying the file.
        """
        with self.exam_structures_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Examination structure configuration must be an object"
            )

        if data.get("schema_version") != "1.0":
            raise ValueError(
                "Invalid examination structure schema version"
            )

        structures = data.get("structures")

        if not isinstance(structures, list):
            raise ValueError(
                "Examination structures must be a list"
            )

        structure_mapping = {}

        for item in structures:
            if not isinstance(item, dict):
                raise ValueError(
                    "Invalid examination structure record"
                )

            module_key = item.get("module_key")

            if (
                not isinstance(module_key, str)
                or not module_key.strip()
            ):
                raise ValueError(
                    "Examination structure has invalid module key"
                )

            if module_key in structure_mapping:
                raise ValueError(
                    f"Duplicate examination structure: {module_key}"
                )

            structure_mapping[module_key] = item

        return structure_mapping

    def _get_taxonomy(self, module_key):
        """
        Resolve a module taxonomy using its canonical key
        or an existing legacy configuration key.
        """
        taxonomy = self.taxonomy.get_module_taxonomy(
            module_key
        )

        if taxonomy is None:
            legacy_key = TAXONOMY_KEY_ALIASES.get(
                module_key
            )

            if legacy_key:
                taxonomy = (
                    self.taxonomy.get_module_taxonomy(
                        legacy_key
                    )
                )

        return taxonomy

    def _get_exam_structure(
        self,
        module_key,
        exam_structures,
    ):
        """
        Resolve a module's examination structure record.
        """
        record = exam_structures.get(module_key)

        if record is None:
            legacy_key = EXAM_STRUCTURE_KEY_ALIASES.get(
                module_key
            )

            if legacy_key:
                record = exam_structures.get(
                    legacy_key
                )

        return record or {}

    def report(self):
        """
        Produce a readiness report for all registered modules.
        """
        modules = self.registry.get_all()

        reviews = self.review_repository.list_reviews()

        if not isinstance(reviews, list):
            raise ValueError(
                "Review repository must return a list"
            )

        exam_structures = self._load_exam_structures()

        reviews_by_module = {}

        for review in reviews:
            if not isinstance(review, dict):
                continue

            module_key = review.get("module_key")

            if isinstance(module_key, str):
                reviews_by_module.setdefault(
                    module_key,
                    [],
                ).append(review)

        defaults = self.rules.rules.get(
            "generation_defaults",
            {},
        )

        policy = self.rules.rules.get(
            "generation_policy",
            {},
        )

        quality = self.rules.rules.get(
            "quality_rules",
            {},
        )

        target = defaults.get(
            "target_papers_per_module"
        )

        valid_target = (
            isinstance(target, int)
            and not isinstance(target, bool)
            and target > 0
        )

        human_review_required = (
            policy.get(
                "require_human_review_before_release"
            ) is True
            or quality.get(
                "require_human_review_before_release"
            ) is True
        )

        module_reports = []

        for module in modules:
            module_key = module["module_key"]

            decisions = reviews_by_module.get(
                module_key,
                [],
            )

            counts = Counter(
                review.get("review_decision")
                for review in decisions
            )

            approved = counts.get(
                "approved",
                0,
            )

            rejected = counts.get(
                "rejected",
                0,
            )

            # --------------------------------------
            # Resolve module topic taxonomy
            # --------------------------------------

            taxonomy_record = self._get_taxonomy(
                module_key
            )

            if taxonomy_record is None:
                topics = []
                taxonomy_status = "unverified"
            else:
                topics = taxonomy_record.get(
                    "topics",
                    [],
                )

                taxonomy_status = (
                    taxonomy_record.get(
                        "verification_status",
                        "unverified",
                    )
                )

            if not isinstance(topics, list):
                raise ValueError(
                    f"Invalid topics for {module_key}"
                )

            # --------------------------------------
            # Resolve examination structure
            # --------------------------------------

            structure_record = (
                self._get_exam_structure(
                    module_key,
                    exam_structures,
                )
            )

            structure = structure_record.get(
                "structure"
            )

            structure_status = (
                structure_record.get(
                    "verification_status",
                    "unverified",
                )
            )

            # --------------------------------------
            # Check missing requirements
            # --------------------------------------

            missing = []

            if not module.get("module_code"):
                missing.append(
                    "module_code"
                )

            if (
                not topics
                or taxonomy_status != "verified"
            ):
                missing.append(
                    "verified_module_topics"
                )

            if (
                not isinstance(structure, dict)
                or not structure
            ):
                missing.append(
                    "exam_structure"
                )

            elif structure_status != "verified":
                missing.append(
                    "verified_exam_structure"
                )

            if not valid_target:
                missing.append(
                    "target_papers_per_module"
                )

            if not defaults.get(
                "difficulty_distribution"
            ):
                missing.append(
                    "difficulty_distribution"
                )

            if not defaults.get(
                "blooms_taxonomy_distribution"
            ):
                missing.append(
                    "blooms_taxonomy_distribution"
                )

            if not defaults.get(
                "question_type_distribution"
            ):
                missing.append(
                    "question_type_distribution"
                )

            # --------------------------------------
            # Build module report
            # --------------------------------------

            module_reports.append({
                "module_key": module_key,
                "module_name": module["module_name"],
                "module_code": module.get(
                    "module_code"
                ),

                "approved_syllabus_candidates":
                    approved,

                "rejected_syllabus_candidates":
                    rejected,

                "configured_topics":
                    len(topics),

                "taxonomy_verification_status":
                    taxonomy_status,

                "has_exam_structure":
                    bool(structure),

                "exam_structure_verification_status":
                    structure_status,

                "ready_for_generation":
                    len(missing) == 0,

                "missing_requirements":
                    missing,

                "human_review_required_before_release":
                    human_review_required,
            })

        ready_count = sum(
            item["ready_for_generation"]
            for item in module_reports
        )

        return {
            "schema_version": "1.0",

            "report_type":
                "synthetic_dataset_readiness",

            "total_modules":
                len(module_reports),

            "ready_modules":
                ready_count,

            "blocked_modules":
                len(module_reports) - ready_count,

            "saved_review_decisions":
                len(reviews),

            "approved_review_decisions":
                sum(
                    item["approved_syllabus_candidates"]
                    for item in module_reports
                ),

            "rejected_review_decisions":
                sum(
                    item["rejected_syllabus_candidates"]
                    for item in module_reports
                ),

            "target_papers_per_module":
                target if valid_target else None,

            "modules":
                module_reports,

            "note": (
                "This report checks configuration readiness "
                "only. Lecturer-approved syllabus candidates "
                "are not automatically treated as verified "
                "module taxonomies. No synthetic questions "
                "are generated by this service."
            ),
        }
