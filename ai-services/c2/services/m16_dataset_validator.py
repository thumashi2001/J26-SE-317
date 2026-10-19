"""M16.3 — Validation of synthetic development question datasets."""

import re
from collections import Counter

from services.m16_question_generator import M16ContentExpander
from services.synthetic_question_generator import QUESTION_BLOOM_LEVELS

# Explicit module key aliases supported across configurations
MODULE_ALIASES = {
    "case_studies_in_software_engineering": "case_studies_software_engineering",
    "software_engineering_process_and_quality_management": "software_engineering_process_quality_management",
}

# Reverse aliases for permissive lookup
CANONICAL_TO_ALIASES = {
    "case_studies_software_engineering": {"case_studies_software_engineering", "case_studies_in_software_engineering"},
    "software_engineering_process_quality_management": {"software_engineering_process_quality_management", "software_engineering_process_and_quality_management"},
}


def normalize_text(value):
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _word_3grams(text):
    words = text.casefold().split()
    if len(words) < 3:
        return set(words)
    return {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}


def _jaccard_similarity(set1, set2):
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


class M16DatasetValidator:
    """Validate M16 fixtures without modifying any source records."""

    def __init__(self, expander=None):
        self.expander = (
            expander if expander is not None
            else M16ContentExpander()
        )

    def validate(self, dataset):
        errors = []
        warnings = []
        seen_ids = set()
        seen_texts = set()
        topic_counts = Counter()
        module_counts = Counter()
        question_count = 0
        near_duplicates = []

        def error(location, message):
            errors.append({
                "location": location,
                "message": message,
            })

        def warning(location, message):
            warnings.append({
                "location": location,
                "message": message,
            })

        if not isinstance(dataset, dict):
            return {
                "valid": False,
                "structural_validity": False,
                "educational_quality_verified": False,
                "question_count": 0,
                "error_count": 1,
                "warning_count": 0,
                "errors": [{
                    "location": "dataset",
                    "message": "Dataset must be an object",
                }],
                "warnings": [],
                "academic_verification": "pending",
                "production_ready": False,
            }

        if dataset.get("generation_mode") != "development_fixture":
            error("dataset", "Development fixture mode required")

        if dataset.get("source_type") != "synthetic":
            error("dataset", "Dataset must be synthetic")

        if dataset.get("verification_status") != "unverified":
            error("dataset", "Dataset must remain unverified")

        bank = self.expander.expanded_bank()

        allowed_modules = {
            module["module_key"]: {
                topic["name"]: topic
                for topic in module["topics"]
            }
            for module in bank["modules"]
        }

        modules = dataset.get("modules")

        if not isinstance(modules, list):
            error("modules", "Modules must be a list")
            modules = []

        seen_modules = set()

        for module_index, module in enumerate(modules):
            location = f"modules[{module_index}]"

            if not isinstance(module, dict):
                error(location, "Module must be an object")
                continue

            raw_module_key = module.get("module_key")
            canonical_key = MODULE_ALIASES.get(raw_module_key, raw_module_key)

            if canonical_key not in allowed_modules and raw_module_key not in allowed_modules:
                error(location, f"Unknown module: {raw_module_key}")
                continue

            lookup_key = canonical_key if canonical_key in allowed_modules else raw_module_key

            if lookup_key in seen_modules:
                error(location, "Duplicate module entry")

            seen_modules.add(lookup_key)

            questions = module.get("questions")

            if not isinstance(questions, list):
                error(location, "Questions must be a list")
                continue

            if module.get("question_count") != len(questions):
                error(location, "Module question count mismatch")

            module_questions_for_similarity = []

            for index, question in enumerate(questions):
                qloc = f"{location}.questions[{index}]"
                question_count += 1

                if not isinstance(question, dict):
                    error(qloc, "Question must be an object")
                    continue

                question_id = question.get("question_id")
                text = question.get("question_text")
                topic = question.get("topic")
                question_type = question.get("question_type")

                if (
                    not isinstance(question_id, str)
                    or not question_id.startswith("SYN-M16-")
                ):
                    error(qloc, "Invalid synthetic question ID")
                elif question_id in seen_ids:
                    error(qloc, "Duplicate question ID")
                else:
                    seen_ids.add(question_id)

                if (
                    not isinstance(text, str)
                    or len(normalize_text(text)) < 40
                ):
                    error(qloc, "Question text is missing or too short")
                else:
                    normalized = normalize_text(text)

                    if normalized in seen_texts:
                        error(qloc, "Duplicate question text")

                    seen_texts.add(normalized)

                    # Collect for near-duplicate analysis within module
                    q_3grams = _word_3grams(normalized)
                    for prev_id, prev_grams, prev_text in module_questions_for_similarity:
                        sim = _jaccard_similarity(q_3grams, prev_grams)
                        if sim >= 0.88 and question_id != prev_id:
                            near_duplicates.append({
                                "question_id_1": prev_id,
                                "question_id_2": question_id,
                                "similarity": round(sim, 4),
                            })
                            warning(
                                qloc,
                                f"Near-duplicate question detected (similarity {sim:.2f}) "
                                f"with {prev_id}"
                            )

                    module_questions_for_similarity.append((question_id, q_3grams, normalized))

                # Check module key consistency allowing for known aliases
                q_mod = question.get("module_key")
                q_mod_canonical = MODULE_ALIASES.get(q_mod, q_mod)
                if q_mod != raw_module_key and q_mod_canonical != lookup_key:
                    error(qloc, "Question module mismatch")

                allowed_topics = allowed_modules[lookup_key]

                if topic not in allowed_topics:
                    error(qloc, f"Unknown provisional topic: {topic}")
                else:
                    expected_type = allowed_topics[topic][
                        "question_type"
                    ]

                    if question_type != expected_type:
                        error(qloc, "Question type mismatch")

                if question_type not in QUESTION_BLOOM_LEVELS:
                    error(qloc, "Unsupported question type")
                elif question.get("bloom_level") != (
                    QUESTION_BLOOM_LEVELS[question_type]
                ):
                    error(qloc, "Bloom level mismatch")

                required_values = {
                    "source_type": "synthetic",
                    "generation_mode": "development_fixture",
                    "verification_status": "unverified",
                    "human_review_status": "pending",
                    "label_source": "synthetic_generation",
                    "taxonomy_verification_status": "unverified",
                    "exam_structure_verification_status": "unverified",
                }

                for field, expected in required_values.items():
                    if question.get(field) != expected:
                        error(
                            qloc,
                            f"{field} must be {expected}",
                        )

                if not isinstance(
                    question.get("scenario_group_id"), str
                ) or not question["scenario_group_id"].strip():
                    error(qloc, "Missing scenario group ID")

                if not isinstance(
                    question.get("task_group_id"), str
                ) or not question["task_group_id"].strip():
                    error(qloc, "Missing task group ID")

                if question.get("marks") is None:
                    warning(qloc, "Marks not yet assigned")
                elif (
                    isinstance(question["marks"], bool)
                    or not isinstance(question["marks"], int)
                    or question["marks"] <= 0
                ):
                    error(qloc, "Invalid marks")

                if question.get("difficulty") == "unassessed":
                    warning(qloc, "Difficulty not yet assessed")
                elif question.get("difficulty") not in {
                    "easy", "medium", "hard"
                }:
                    error(qloc, "Invalid difficulty")

                if isinstance(topic, str):
                    topic_counts[f"{lookup_key}:{topic}"] += 1

                module_counts[lookup_key] += 1

        if dataset.get("total_questions") != question_count:
            error("dataset", "Total question count mismatch")

        missing_modules = set(allowed_modules) - seen_modules

        for missing_key in sorted(missing_modules):
            warning(
                "dataset",
                f"Missing module: {missing_key}",
            )

        warning(
            "dataset",
            "All provisional topic labels require academic review",
        )
        warning(
            "dataset",
            "Automated structural validation does not establish academic correctness or syllabus fidelity",
        )

        return {
            "valid": not errors,
            "structural_validity": not errors,
            "educational_quality_verified": False,
            "question_count": question_count,
            "module_count": len(seen_modules),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "near_duplicate_count": len(near_duplicates),
            "module_distribution": dict(sorted(module_counts.items())),
            "topic_distribution": dict(sorted(topic_counts.items())),
            "errors": errors,
            "warnings": warnings,
            "academic_verification": "pending",
            "production_ready": False,
        }
