"""M17.1 / M17.2 — Supervised Topic Classification Model Training Pipeline.

Trains and packages scikit-learn topic classification models on M16 synthetic
development data using a two-stage approach (module context supplied, model predicts
provisional topic within the module).

Development and research use only. Strictly isolated from authentic examination data.
Provisional labels are unverified and must not be marked as lecturer-approved.
"""

import hashlib
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = (
    PROJECT_ROOT / "datasets" / "synthetic" / "m16" / "training_export"
)
DEFAULT_MODELS_DIR = PROJECT_ROOT / "outputs" / "models" / "m17"

MODULE_KEYS = [
    "application_frameworks",
    "case_studies_software_engineering",
    "database_systems",
    "distributed_systems",
    "software_architecture",
    "software_engineering_process_quality_management",
    "software_project_management",
    "user_experience_engineering",
]


def normalize_text(text: str) -> str:
    """Normalize question text for TF-IDF vectorization."""
    if not isinstance(text, str):
        raise ValueError("Question text must be a string")
    text = text.strip()
    if not text:
        raise ValueError("Question text cannot be empty")
    # Collapse multiple whitespace characters and lower-case
    return " ".join(text.lower().split())


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for reproducibility tracking."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class M17DatasetIntegrityError(Exception):
    """Raised when synthetic dataset integrity or split isolation is violated."""
    pass


class M17TopicClassifierTrainer:
    """Trainer for M17 supervised topic classification models."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        models_dir: Optional[Path] = None,
    ):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self.models_dir = Path(models_dir or DEFAULT_MODELS_DIR)

    def load_split(
        self,
        split_name: str,
    ) -> Dict[str, Any]:
        """Load and validate a split file (train.json, validation.json, test.json)."""
        file_path = self.data_dir / f"{split_name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Split file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise M17DatasetIntegrityError(
                f"Failed to parse {split_name}.json: {e}"
            ) from e

        # Integrity checks
        if not isinstance(data, dict):
            raise M17DatasetIntegrityError(f"Split data in {split_name} must be a dict")

        if data.get("source_type") != "synthetic":
            raise M17DatasetIntegrityError(
                f"Invalid source_type in {split_name}: {data.get('source_type')}. "
                "Only synthetic development data may be loaded."
            )

        if data.get("verification_status") != "unverified":
            raise M17DatasetIntegrityError(
                f"Split {split_name} has verification_status='{data.get('verification_status')}'. "
                "Expected 'unverified' for synthetic development fixtures."
            )

        if not data.get("provisional_topics", False):
            raise M17DatasetIntegrityError(
                f"Split {split_name} must declare provisional_topics=True."
            )

        questions = data.get("questions")
        if not isinstance(questions, list) or not questions:
            raise M17DatasetIntegrityError(
                f"Split {split_name} must contain a non-empty 'questions' list"
            )

        for q in questions:
            if q.get("source_type") != "synthetic":
                raise M17DatasetIntegrityError(
                    f"Non-synthetic question detected in {split_name}: {q.get('question_id')}"
                )
            if q.get("verification_status") != "unverified":
                raise M17DatasetIntegrityError(
                    f"Verified question detected in synthetic {split_name}: {q.get('question_id')}"
                )
            if not q.get("module_key") or not q.get("topic") or not q.get("question_text"):
                raise M17DatasetIntegrityError(
                    f"Question {q.get('question_id')} missing required fields"
                )

        return data

    def validate_split_integrity(
        self,
        train_data: Dict[str, Any],
        val_data: Dict[str, Any],
        test_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate partition disjointness, scenario isolation, and template risks."""
        train_qs = train_data["questions"]
        val_qs = val_data["questions"]
        test_qs = test_data["questions"]

        # 1. Question ID uniqueness and disjointness
        train_ids = [q["question_id"] for q in train_qs]
        val_ids = [q["question_id"] for q in val_qs]
        test_ids = [q["question_id"] for q in test_qs]

        if len(train_ids) != len(set(train_ids)):
            raise M17DatasetIntegrityError("Duplicate question IDs within train split")
        if len(val_ids) != len(set(val_ids)):
            raise M17DatasetIntegrityError("Duplicate question IDs within validation split")
        if len(test_ids) != len(set(test_ids)):
            raise M17DatasetIntegrityError("Duplicate question IDs within test split")

        train_id_set = set(train_ids)
        val_id_set = set(val_ids)
        test_id_set = set(test_ids)

        if not train_id_set.isdisjoint(val_id_set):
            raise M17DatasetIntegrityError("Question ID overlap between train and validation")
        if not train_id_set.isdisjoint(test_id_set):
            raise M17DatasetIntegrityError("Question ID overlap between train and test")
        if not val_id_set.isdisjoint(test_id_set):
            raise M17DatasetIntegrityError("Question ID overlap between validation and test")

        # 2. Scenario group disjointness
        train_scenarios = {q.get("scenario_group_id") for q in train_qs if q.get("scenario_group_id")}
        val_scenarios = {q.get("scenario_group_id") for q in val_qs if q.get("scenario_group_id")}
        test_scenarios = {q.get("scenario_group_id") for q in test_qs if q.get("scenario_group_id")}

        if not train_scenarios.isdisjoint(val_scenarios):
            raise M17DatasetIntegrityError("Scenario group overlap between train and validation")
        if not train_scenarios.isdisjoint(test_scenarios):
            raise M17DatasetIntegrityError("Scenario group overlap between train and test")
        if not val_scenarios.isdisjoint(test_scenarios):
            raise M17DatasetIntegrityError("Scenario group overlap between validation and test")

        # 3. Template family tracking (explicitly flag unresolved template overlap)
        train_templates = {q.get("template_family_id") for q in train_qs if q.get("template_family_id")}
        val_templates = {q.get("template_family_id") for q in val_qs if q.get("template_family_id")}
        test_templates = {q.get("template_family_id") for q in test_qs if q.get("template_family_id")}

        template_train_val_overlap = len(train_templates & val_templates)
        template_train_test_overlap = len(train_templates & test_templates)
        template_val_test_overlap = len(val_templates & test_templates)

        # 4. Check all expected module keys and minimum sample counts
        for module_key in MODULE_KEYS:
            mod_train_qs = [q for q in train_qs if q["module_key"] == module_key]
            if not mod_train_qs:
                raise M17DatasetIntegrityError(f"Missing training questions for module '{module_key}'")
            topics = {q["topic"] for q in mod_train_qs}
            if len(topics) < 5:
                raise M17DatasetIntegrityError(
                    f"Module '{module_key}' has only {len(topics)} provisional topics in train (expected 5)"
                )
            for topic in topics:
                count = sum(1 for q in mod_train_qs if q["topic"] == topic)
                if count < 5:
                    raise M17DatasetIntegrityError(
                        f"Topic '{topic}' in module '{module_key}' has only {count} training samples (min 5)"
                    )

        return {
            "counts": {
                "train": len(train_ids),
                "validation": len(val_ids),
                "test": len(test_ids),
                "total": len(train_ids) + len(val_ids) + len(test_ids),
            },
            "scenario_isolation": {
                "train_scenarios": len(train_scenarios),
                "val_scenarios": len(val_scenarios),
                "test_scenarios": len(test_scenarios),
                "disjoint": True,
            },
            "template_family_risk": {
                "train_val_overlap_count": template_train_val_overlap,
                "train_test_overlap_count": template_train_test_overlap,
                "val_test_overlap_count": template_val_test_overlap,
                "risk_flagged": True,
                "explanation": (
                    "Template families share task phrasing across distinct scenarios because M16 splits "
                    "at the scenario group level to retain all 5 topics across splits. Model evaluation on "
                    "synthetic data may exhibit higher performance than on novel unseen phrasing."
                ),
            },
            "status": "passed",
        }

    @staticmethod
    def build_pipeline(
        model_type: str = "logistic_regression",
        seed: int = 42,
        C: float = 1.0,
        ngram_range: Tuple[int, int] = (1, 2),
        max_iter: int = 1000,
    ) -> Pipeline:
        """Construct a reproducible scikit-learn classification pipeline."""
        if model_type not in ("logistic_regression", "linear_svc"):
            raise ValueError(
                f"Unsupported model_type: '{model_type}'. "
                "Supported: 'logistic_regression', 'linear_svc'"
            )

        tfidf = TfidfVectorizer(
            ngram_range=ngram_range,
            sublinear_tf=True,
            min_df=1,
            lowercase=True,
        )

        if model_type == "logistic_regression":
            clf = LogisticRegression(
                C=C,
                max_iter=max_iter,
                class_weight="balanced",
                random_state=seed,
                solver="lbfgs",
            )
        else:
            clf = LinearSVC(
                C=C,
                max_iter=max_iter,
                class_weight="balanced",
                random_state=seed,
            )

        return Pipeline([
            ("tfidf", tfidf),
            ("clf", clf),
        ])

    def train_module(
        self,
        module_key: str,
        questions: List[Dict[str, Any]],
        model_type: str = "logistic_regression",
        seed: int = 42,
        C: float = 1.0,
        ngram_range: Tuple[int, int] = (1, 2),
        max_iter: int = 1000,
    ) -> Dict[str, Any]:
        """Train a single module topic classifier."""
        module_questions = [
            q for q in questions if q.get("module_key") == module_key
        ]
        if not module_questions:
            raise ValueError(f"No training questions found for module '{module_key}'")

        X = [normalize_text(q["question_text"]) for q in module_questions]
        y = [q["topic"].strip() for q in module_questions]

        classes = sorted(list(set(y)))
        if len(classes) < 2:
            raise ValueError(
                f"Module '{module_key}' must have at least 2 topic classes to train (got {len(classes)})"
            )

        pipeline = self.build_pipeline(
            model_type=model_type,
            seed=seed,
            C=C,
            ngram_range=ngram_range,
            max_iter=max_iter,
        )

        start_time = time.perf_counter()
        pipeline.fit(X, y)
        train_duration = time.perf_counter() - start_time

        return {
            "module_key": module_key,
            "model_type": model_type,
            "pipeline": pipeline,
            "classes": classes,
            "n_samples": len(X),
            "n_classes": len(classes),
            "training_time_seconds": round(train_duration, 4),
            "seed": seed,
            "hyperparameters": {
                "C": C,
                "ngram_range": list(ngram_range),
                "max_iter": max_iter,
                "class_weight": "balanced",
                "model_type": model_type,
            },
        }

    def train_all_modules(
        self,
        questions: List[Dict[str, Any]],
        model_type: str = "logistic_regression",
        seed: int = 42,
        C: float = 1.0,
        ngram_range: Tuple[int, int] = (1, 2),
        max_iter: int = 1000,
    ) -> Dict[str, Dict[str, Any]]:
        """Train classifiers for all 8 Year 3 modules."""
        trained_models = {}
        for module_key in MODULE_KEYS:
            trained_models[module_key] = self.train_module(
                module_key=module_key,
                questions=questions,
                model_type=model_type,
                seed=seed,
                C=C,
                ngram_range=ngram_range,
                max_iter=max_iter,
            )
        return trained_models

    def save_artifacts(
        self,
        models_dict: Dict[str, Dict[str, Any]],
        model_type: str,
        integrity_summary: Dict[str, Any],
        output_dir: Optional[Path] = None,
        is_selected_production_candidate: bool = False,
    ) -> Path:
        """Persist trained model artifacts and comprehensive metadata."""
        target_dir = Path(output_dir or self.models_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Compute dataset hashes for provenance
        train_file = self.data_dir / "train.json"
        train_hash = compute_file_sha256(train_file) if train_file.exists() else "unknown"

        meta_file = self.data_dir / "split_metadata.json"
        split_meta_hash = compute_file_sha256(meta_file) if meta_file.exists() else "unknown"

        saved_files = []
        module_metadata = {}

        for module_key, pkg in models_dict.items():
            # Standard artifact name: {module_key}_{model_type}.joblib
            # If selected as default classifier, also write {module_key}_classifier.joblib
            filename = f"{module_key}_{model_type}.joblib"
            filepath = target_dir / filename

            artifact_payload = {
                "module_key": module_key,
                "model_type": pkg["model_type"],
                "classes": pkg["classes"],
                "pipeline": pkg["pipeline"],
                "hyperparameters": pkg["hyperparameters"],
                "seed": pkg["seed"],
                "training_time_seconds": pkg["training_time_seconds"],
                "n_samples": pkg["n_samples"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "synthetic_provenance": "m16_synthetic_development_split",
                "academic_verification": "unverified",
            }
            joblib.dump(artifact_payload, filepath)
            saved_files.append(str(filepath))

            if is_selected_production_candidate:
                default_filepath = target_dir / f"{module_key}_classifier.joblib"
                joblib.dump(artifact_payload, default_filepath)
                saved_files.append(str(default_filepath))

            module_metadata[module_key] = {
                "artifact_file": filename,
                "classes": pkg["classes"],
                "n_samples": pkg["n_samples"],
                "training_time_seconds": pkg["training_time_seconds"],
            }

        # Overall training metadata
        overall_metadata = {
            "schema_version": "1.0",
            "milestone": "M17",
            "model_type": model_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "python_version": sys.version,
                "platform": platform.platform(),
                "sklearn_version": sklearn.__version__,
                "joblib_version": joblib.__version__,
            },
            "provenance": {
                "dataset_type": "synthetic_development_data",
                "train_dataset_sha256": train_hash,
                "split_metadata_sha256": split_meta_hash,
                "verification_status": "unverified",
                "academic_use_permitted": False,
                "disclaimer": (
                    "Trained strictly on synthetic development questions from M16. "
                    "Cannot be used as authentic exam intelligence without lecturer verification."
                ),
            },
            "integrity_summary": integrity_summary,
            "modules": module_metadata,
        }

        meta_path = target_dir / f"{model_type}_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(overall_metadata, f, indent=2)

        if is_selected_production_candidate:
            default_meta_path = target_dir / "selected_model_metadata.json"
            with open(default_meta_path, "w", encoding="utf-8") as f:
                json.dump(overall_metadata, f, indent=2)

        return target_dir
