
"""M11.2.2 - Reproducible synthetic question draft generator."""

import hashlib
import json
import math
import random
from copy import deepcopy

from services.synthetic_dataset_readiness import (
    SyntheticDatasetReadiness,
)
from services.synthetic_rules import SyntheticRules


QUESTION_TEMPLATES = {
    "explain": (
        "Explain the key principles of {topic} in the context "
        "of {module_name}. Include a relevant example."
    ),
    "apply": (
        "Apply the principles of {topic} to a realistic "
        "{module_name} scenario. Describe the steps and "
        "justify your approach."
    ),
    "analyze": (
        "Analyze a scenario involving {topic} in "
        "{module_name}. Identify potential challenges "
        "and explain their consequences."
    ),
    "evaluate": (
        "Evaluate two possible approaches to {topic} "
        "within {module_name}. Discuss their strengths, "
        "limitations, and suitability."
    ),
    "design": (
        "Design a solution involving {topic} for a "
        "{module_name} problem. Explain your design "
        "decisions and expected outcomes."
    ),
}


QUESTION_BLOOM_LEVELS = {
    "explain": "understand",
    "apply": "apply",
    "analyze": "analyze",
    "evaluate": "evaluate",
    "design": "create",
}


class SyntheticQuestionGenerator:
    """
    Generate reproducible synthetic examination question drafts.

    Production mode requires verified module readiness.
    Development fixture mode uses explicitly supplied test data.

    Neither mode writes files or approves generated questions.
    """

    def __init__(self, rules=None, readiness=None):
        self.rules = (
            rules if rules is not None else SyntheticRules()
        )
        self.readiness = readiness

    @staticmethod
    def _positive_integer(value, field):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValueError(
                f"{field} must be a positive integer"
            )

    @staticmethod
    def _validate_distribution(distribution, field):
        if (
            not isinstance(distribution, dict)
            or not distribution
        ):
            raise ValueError(
                f"Missing or invalid {field}"
            )

        total = 0

        for label, weight in distribution.items():
            if (
                not isinstance(label, str)
                or not label.strip()
                or isinstance(weight, bool)
                or not isinstance(weight, (int, float))
                or not math.isfinite(weight)
                or weight < 0
            ):
                raise ValueError(
                    f"Invalid entry in {field}"
                )

            total += weight

        if total <= 0:
            raise ValueError(
                f"{field} must have positive total weight"
            )

    @staticmethod
    def _weighted_choice(rng, distribution):
        choices = list(distribution.keys())
        weights = list(distribution.values())

        return rng.choices(
            choices,
            weights=weights,
            k=1,
        )[0]

    @classmethod
    def _validate_config(cls, config):
        if not isinstance(config, dict):
            raise ValueError(
                "Generation configuration must be an object"
            )

        for field in (
            "module_key",
            "module_code",
            "module_name",
        ):
            value = config.get(field)

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"Missing or invalid {field}"
                )

        topics = config.get("topics")

        if (
            not isinstance(topics, list)
            or not topics
            or any(
                not isinstance(topic, str)
                or not topic.strip()
                for topic in topics
            )
        ):
            raise ValueError(
                "At least one valid topic is required"
            )

        if len(topics) != len(set(topics)):
            raise ValueError(
                "Duplicate topics are not allowed"
            )

        marks_options = config.get("marks_options")

        if (
            not isinstance(marks_options, list)
            or not marks_options
        ):
            raise ValueError(
                "marks_options must be a nonempty list"
            )

        for marks in marks_options:
            cls._positive_integer(marks, "marks")

        distribution_fields = (
            "question_type_distribution",
            "difficulty_distribution",
            "blooms_taxonomy_distribution",
        )

        for field in distribution_fields:
            cls._validate_distribution(
                config.get(field),
                field,
            )

        type_distribution = config[
            "question_type_distribution"
        ]

        unsupported = (
            set(type_distribution)
            - set(QUESTION_TEMPLATES)
        )

        if unsupported:
            raise ValueError(
                "Unsupported question types: "
                + ", ".join(sorted(unsupported))
            )

        bloom_distribution = config[
            "blooms_taxonomy_distribution"
        ]

        for question_type, weight in (
            type_distribution.items()
        ):
            if weight <= 0:
                continue

            required_bloom = (
                QUESTION_BLOOM_LEVELS[question_type]
            )

            if bloom_distribution.get(
                required_bloom, 0
            ) <= 0:
                raise ValueError(
                    "Bloom distribution does not support "
                    f"question type: {question_type}"
                )

    def _check_production_readiness(self, config):
        module_key = config["module_key"]

        readiness = (
            self.readiness
            if self.readiness is not None
            else SyntheticDatasetReadiness()
        )

        report = readiness.report()

        module_report = next(
            (
                item
                for item in report["modules"]
                if item["module_key"] == module_key
            ),
            None,
        )

        if (
            module_report is None
            or not module_report.get(
                "ready_for_generation", False
            )
        ):
            raise ValueError(
                "Production generation blocked: "
                "module academic configuration "
                "is not verified and ready"
            )

        registered_module = (
            self.rules.registry.get_by_key(module_key)
        )

        if (
            registered_module is None
            or registered_module.get("module_code")
            != config["module_code"]
        ):
            raise ValueError(
                "Production module code mismatch"
            )

        # Keep production disabled if the topic source
        # used by the validator is not synchronized.
        verified_topics = (
            registered_module.get("topics") or []
        )

        if not verified_topics:
            raise ValueError(
                "Production generation blocked: "
                "verified topics are not available "
                "in the validation registry"
            )

        if any(
            topic not in verified_topics
            for topic in config["topics"]
        ):
            raise ValueError(
                "Production topics do not match "
                "verified module configuration"
            )

    def generate(
        self,
        config,
        count,
        seed=42,
        mode="production",
    ):
        """
        Generate synthetic question drafts in memory.

        No output files or real datasets are modified.
        """

        if mode not in (
            "production",
            "development_fixture",
        ):
            raise ValueError(
                "Unsupported generation mode"
            )

        self._positive_integer(count, "count")

        if (
            isinstance(seed, bool)
            or not isinstance(seed, int)
        ):
            raise ValueError(
                "seed must be an integer"
            )

        self._validate_config(config)

        if mode == "production":
            self._check_production_readiness(config)

        module_key = config["module_key"]

        rng = random.Random(seed)

        # The batch ID depends on the complete request.
        fingerprint = json.dumps(
            {
                "config": config,
                "seed": seed,
                "count": count,
                "mode": mode,
            },
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )

        batch_id = hashlib.sha256(
            fingerprint.encode("utf-8")
        ).hexdigest()[:16]

        # Each topic/question-type pair produces one
        # distinct template question.
        available_combinations = [
            (topic, question_type)
            for topic in config["topics"]
            for question_type, weight in config[
                "question_type_distribution"
            ].items()
            if weight > 0
        ]

        if count > len(available_combinations):
            raise ValueError(
                "Requested question count exceeds available unique "
                "topic/question-type combinations. Add more reviewed "
                "templates or topics before increasing the count."
            )

        rng.shuffle(available_combinations)

        questions = []
        question_texts = set()

        for index in range(1, count + 1):
            topic, question_type = (
                available_combinations[index - 1]
            )

            difficulty = self._weighted_choice(
                rng,
                config["difficulty_distribution"],
            )

            # Bloom's level is derived from the action verb.
            bloom_level = (
                QUESTION_BLOOM_LEVELS[question_type]
            )

            marks = rng.choice(
                config["marks_options"]
            )

            question_text = (
                QUESTION_TEMPLATES[
                    question_type
                ].format(
                    topic=topic,
                    module_name=config["module_name"],
                )
            )

            if question_text in question_texts:
                raise ValueError(
                    "Duplicate generated question text"
                )

            question_texts.add(question_text)

            question = {
                "question_id": (
                    f"SYN-{module_key}-{batch_id}-Q{index:04d}"
                ),
                "module_key": module_key,
                "module_code": config["module_code"],
                "module_name": config["module_name"],
                "question_text": question_text,
                "topic": topic,
                "marks": marks,
                "marks_status": "generated",
                "question_type": question_type,
                "difficulty": difficulty,
                "bloom_level": bloom_level,
                "source_type": "synthetic",
                "verification_status": "unverified",
                "human_review_status": "pending",
                "generation_provenance": {
                    "generator": "c2_template_generator_v1",
                    "mode": mode,
                    "batch_id": batch_id,
                    "seed": seed,
                    "sequence": index,
                },
            }

            if mode == "production":
                validation = (
                    self.rules.validate_generated_question(
                        question
                    )
                )

                if not validation["valid"]:
                    raise ValueError(
                        "Generated question failed validation: "
                        + "; ".join(validation["errors"])
                    )

            questions.append(question)

        question_ids = [
            question["question_id"]
            for question in questions
        ]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Generated question IDs are not unique"
            )

        return {
            "schema_version": "1.0",
            "dataset_type": "synthetic_question_drafts",
            "module_key": module_key,
            "generation_mode": mode,
            "batch_id": batch_id,
            "question_count": len(questions),
            "human_review_required": True,
            "release_status": "not_approved",
            "questions": deepcopy(questions),
        }
