"""M16.5 — Training-ready export service for synthetic development datasets.

Exports group-aware train/validation/test splits preventing scenario leakage.
Enforces synthetic-only provenance and validates partition integrity.
Development fixtures only. Never modifies authentic examination datasets.
"""

import hashlib
import json
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_DIR = (
    PROJECT_ROOT / "datasets" / "synthetic" / "m16" / "training_export"
)

# Forbidden directories that must never be overwritten
FORBIDDEN_DIRECTORIES = [
    PROJECT_ROOT / "datasets" / "authentic",
    PROJECT_ROOT / "datasets" / "processed",
]


def _extract_3grams(text):
    words = text.casefold().split()
    if len(words) < 3:
        return set(words)
    return {" ".join(words[i:i + 3]) for i in range(len(words) - 2)}


def _jaccard(set1, set2):
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


class M16TrainingExporter:
    """Group-aware dataset splitting and training export for M16 synthetic data."""

    def __init__(self, export_dir=None):
        self.export_dir = Path(export_dir or DEFAULT_EXPORT_DIR)

    @staticmethod
    def _validate_ratios(train_ratio, val_ratio, test_ratio):
        for name, ratio in [
            ("train_ratio", train_ratio),
            ("val_ratio", val_ratio),
            ("test_ratio", test_ratio),
        ]:
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
                raise ValueError(f"{name} must be a number")
            if ratio < 0:
                raise ValueError(f"{name} cannot be negative")

        if train_ratio <= 0:
            raise ValueError("train_ratio must be positive")
        if test_ratio <= 0:
            raise ValueError("test_ratio must be positive")

        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 1e-5:
            raise ValueError(f"Split ratios must sum to 1.0 (got {total})")

    @staticmethod
    def _validate_dataset(dataset):
        if not isinstance(dataset, dict):
            raise ValueError("Dataset must be an object")

        if dataset.get("source_type") != "synthetic":
            raise ValueError("Training exporter only processes synthetic datasets")

        if dataset.get("generation_mode") != "development_fixture":
            raise ValueError("Only development fixture datasets may be exported")

        if dataset.get("verification_status") != "unverified":
            raise ValueError("Dataset must remain unverified")

        modules = dataset.get("modules")
        if not isinstance(modules, list) or not modules:
            raise ValueError("Dataset must contain a non-empty modules list")

        for module in modules:
            questions = module.get("questions", [])
            for q in questions:
                if q.get("source_type") != "synthetic":
                    raise ValueError(
                        f"Non-synthetic question detected: {q.get('question_id')}"
                    )
                if q.get("verification_status") != "unverified":
                    raise ValueError(
                        f"Verified question detected: {q.get('question_id')}"
                    )

    def split(
        self,
        dataset,
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
    ):
        """Split dataset into group-aware train, validation, and test partitions."""
        self._validate_ratios(train_ratio, val_ratio, test_ratio)
        self._validate_dataset(dataset)

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")

        train_questions = []
        val_questions = []
        test_questions = []

        all_train_scenarios = set()
        all_val_scenarios = set()
        all_test_scenarios = set()

        rng = random.Random(seed)

        for module_index, module in enumerate(dataset["modules"]):
            module_key = module["module_key"]
            questions = module.get("questions", [])

            if not questions:
                continue

            # Group questions by scenario_group_id to prevent data leakage
            scenario_groups = {}
            for q in questions:
                sg_id = q.get("scenario_group_id")
                if not sg_id:
                    sg_id = f"{module_key}:default_group"
                if sg_id not in scenario_groups:
                    scenario_groups[sg_id] = []
                scenario_groups[sg_id].append(deepcopy(q))

            group_keys = sorted(scenario_groups.keys())

            # Require sufficient independent groups to support splitting
            required_groups = 3 if val_ratio > 0 else 2
            if len(group_keys) < required_groups:
                raise ValueError(
                    f"Insufficient independent scenario groups ({len(group_keys)}) "
                    f"for module '{module_key}'. Need at least {required_groups}."
                )

            # Deterministic group shuffle
            module_rng = random.Random(seed + module_index * 1000)
            shuffled_keys = list(group_keys)
            module_rng.shuffle(shuffled_keys)

            # Compute group allocation counts
            total_groups = len(shuffled_keys)
            n_train = max(1, round(total_groups * train_ratio))
            n_val = max(1, round(total_groups * val_ratio)) if val_ratio > 0 else 0
            n_test = total_groups - n_train - n_val

            # Adjust allocations to guarantee at least one group in test
            if n_test < 1:
                n_test = 1
                if n_train > 1:
                    n_train -= 1
                elif n_val > 1:
                    n_val -= 1

            train_keys = set(shuffled_keys[:n_train])
            val_keys = set(shuffled_keys[n_train:n_train + n_val])
            test_keys = set(shuffled_keys[n_train + n_val:])

            # Verify group disjointness within module
            assert train_keys.isdisjoint(val_keys)
            assert train_keys.isdisjoint(test_keys)
            assert val_keys.isdisjoint(test_keys)

            for key in train_keys:
                train_questions.extend(scenario_groups[key])
                all_train_scenarios.add(key)

            for key in val_keys:
                val_questions.extend(scenario_groups[key])
                all_val_scenarios.add(key)

            for key in test_keys:
                test_questions.extend(scenario_groups[key])
                all_test_scenarios.add(key)

        # Global scenario leakage verification
        leakage_detected = not (
            all_train_scenarios.isdisjoint(all_val_scenarios)
            and all_train_scenarios.isdisjoint(all_test_scenarios)
            and all_val_scenarios.isdisjoint(all_test_scenarios)
        )

        if leakage_detected:
            raise ValueError("Scenario leakage detected across dataset splits")

        total_q = len(train_questions) + len(val_questions) + len(test_questions)

        # Lexical and template similarity analysis
        leakage_report = self._analyze_lexical_similarity(
            train_questions, val_questions, test_questions
        )

        # Class distribution and imbalance analysis
        class_dist = self._analyze_distributions(
            train_questions, val_questions, test_questions
        )

        metadata = {
            "schema_version": "1.0",
            "milestone": "M16.5",
            "dataset_type": "synthetic_development_split",
            "split_seed": seed,
            "source_type": "synthetic",
            "verification_status": "unverified",
            "academic_verification": "pending",
            "production_ready": False,
            "provisional_topics": True,
            "target_ratios": {
                "train": train_ratio,
                "validation": val_ratio,
                "test": test_ratio,
            },
            "actual_counts": {
                "train": len(train_questions),
                "validation": len(val_questions),
                "test": len(test_questions),
                "total": total_q,
            },
            "actual_proportions": {
                "train": round(len(train_questions) / total_q, 4) if total_q > 0 else 0,
                "validation": round(len(val_questions) / total_q, 4) if total_q > 0 else 0,
                "test": round(len(test_questions) / total_q, 4) if total_q > 0 else 0,
            },
            "group_splitting_strategy": "scenario_group_id_disjoint",
            "scenario_leakage_detected": False,
            "distinct_scenarios": {
                "train": len(all_train_scenarios),
                "validation": len(all_val_scenarios),
                "test": len(all_test_scenarios),
                "total": (
                    len(all_train_scenarios)
                    + len(all_val_scenarios)
                    + len(all_test_scenarios)
                ),
            },
            "leakage_risk_report": leakage_report,
            "class_distributions": class_dist,
            "academic_disclaimer": (
                "Synthetic evaluation results cannot establish accuracy on "
                "authentic examination papers. For development and model pre-training only."
            ),
        }

        return {
            "train": train_questions,
            "validation": val_questions,
            "test": test_questions,
            "metadata": metadata,
        }

    @staticmethod
    def _analyze_lexical_similarity(train_q, val_q, test_q):
        """Detect potential lexical and template leakage between train and eval sets."""
        train_3grams = [_extract_3grams(q["question_text"]) for q in train_q]
        val_3grams = [_extract_3grams(q["question_text"]) for q in val_q]
        test_3grams = [_extract_3grams(q["question_text"]) for q in test_q]

        # Sample comparisons to maintain test speed
        sample_train = train_3grams[:min(len(train_3grams), 50)]
        sample_test = test_3grams[:min(len(test_3grams), 50)]
        sample_val = val_3grams[:min(len(val_3grams), 50)]

        max_train_test_jaccard = 0.0
        sum_train_test_jaccard = 0.0
        comparisons = 0

        for t_grams in sample_train:
            for eval_grams in sample_test:
                sim = _jaccard(t_grams, eval_grams)
                if sim > max_train_test_jaccard:
                    max_train_test_jaccard = sim
                sum_train_test_jaccard += sim
                comparisons += 1

        avg_train_test_jaccard = (
            sum_train_test_jaccard / comparisons if comparisons > 0 else 0.0
        )

        return {
            "max_train_test_3gram_jaccard": round(max_train_test_jaccard, 4),
            "avg_train_test_3gram_jaccard": round(avg_train_test_jaccard, 4),
            "high_leakage_risk": max_train_test_jaccard > 0.85,
            "assessment": (
                "Low risk: disjoint scenarios prevent memorization leakage"
                if max_train_test_jaccard <= 0.85
                else "Elevated risk: template structure overlap detected"
            ),
        }

    @staticmethod
    def _analyze_distributions(train_q, val_q, test_q):
        """Report class distributions and imbalance ratios across partitions."""
        def extract_dist(questions):
            modules = Counter(q["module_key"] for q in questions)
            topics = Counter(f"{q['module_key']}:{q['topic']}" for q in questions)
            q_types = Counter(q["question_type"] for q in questions)
            blooms = Counter(q["bloom_level"] for q in questions)
            return {
                "module_distribution": dict(sorted(modules.items())),
                "topic_distribution": dict(sorted(topics.items())),
                "question_type_distribution": dict(sorted(q_types.items())),
                "bloom_level_distribution": dict(sorted(blooms.items())),
            }

        train_dist = extract_dist(train_q)
        val_dist = extract_dist(val_q)
        test_dist = extract_dist(test_q)

        # Imbalance ratio for modules in train (max_count / min_count)
        module_counts = list(train_dist["module_distribution"].values())
        imbalance_ratio = (
            max(module_counts) / min(module_counts)
            if module_counts and min(module_counts) > 0
            else 1.0
        )

        return {
            "train": train_dist,
            "validation": val_dist,
            "test": test_dist,
            "train_module_imbalance_ratio": round(imbalance_ratio, 3),
        }

    def export(
        self,
        dataset,
        output_dir=None,
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        seed=42,
    ):
        """Export train.json, validation.json, test.json, and split_metadata.json."""
        target_dir = Path(output_dir or self.export_dir).resolve()

        # Enforce output path safeguards
        for forbidden in FORBIDDEN_DIRECTORIES:
            resolved = forbidden.resolve()
            if target_dir == resolved or resolved in target_dir.parents:
                raise ValueError(
                    f"M16 training export cannot write to forbidden directory: {forbidden}"
                )

        splits = self.split(
            dataset,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
        )

        target_dir.mkdir(parents=True, exist_ok=True)

        created_files = {}

        for split_name in ("train", "validation", "test"):
            file_path = target_dir / f"{split_name}.json"
            split_data = {
                "schema_version": "1.0",
                "split_name": split_name,
                "dataset_type": f"synthetic_{split_name}_split",
                "source_type": "synthetic",
                "verification_status": "unverified",
                "academic_verification": "pending",
                "provisional_topics": True,
                "seed": seed,
                "disclaimer": (
                    "Synthetic development fixtures only. Evaluation results "
                    "cannot establish accuracy on authentic examination papers."
                ),
                "question_count": len(splits[split_name]),
                "questions": splits[split_name],
            }
            file_path.write_text(
                json.dumps(split_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            created_files[split_name] = file_path

        metadata_path = target_dir / "split_metadata.json"
        metadata_path.write_text(
            json.dumps(splits["metadata"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        created_files["metadata"] = metadata_path

        return {
            "output_dir": target_dir,
            "created_files": created_files,
            "metadata": splits["metadata"],
        }
