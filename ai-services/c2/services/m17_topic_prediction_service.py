"""M17.4 — Conservative Topic Classification Prediction and Abstention Service.

Provides topic classification for Year 3 examination questions using trained
M17 scikit-learn models. Applies conservative abstention thresholding,
distinguishes calibrated probabilities from uncalibrated decision scores,
enforces synthetic isolation, and returns unverified provisional predictions.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np

from services.m17_topic_classifier_trainer import (
    DEFAULT_MODELS_DIR,
    MODULE_KEYS,
    normalize_text,
)

MODULE_ALIASES = {
    "case_studies_in_software_engineering": "case_studies_software_engineering",
}


def _slug(text: str) -> str:
    """Generate a clean slug for provisional topic IDs."""
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


class ModelNotFoundError(FileNotFoundError):
    """Raised when a trained module classifier artifact is not found."""
    pass


class M17TopicPredictionService:
    """Conservative topic prediction service with abstention."""

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        default_threshold: float = 0.38,
        model_type: Optional[str] = None,
    ):
        self.models_dir = Path(models_dir or DEFAULT_MODELS_DIR).resolve()
        self.default_threshold = default_threshold
        self.model_type = model_type
        self._cache: Dict[str, Dict[str, Any]] = {}

    def canonicalize_module_key(self, module_key: str) -> str:
        """Validate and canonicalize module key."""
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Module key must be a non-empty string")

        norm = module_key.strip().lower()
        norm = MODULE_ALIASES.get(norm, norm)

        if norm not in MODULE_KEYS:
            raise ValueError(
                f"Invalid module key: '{module_key}'. "
                f"Supported modules: {', '.join(MODULE_KEYS)}"
            )

        return norm

    def get_model_path(self, module_key: str) -> Path:
        """Resolve trusted local artifact path for a module classifier."""
        canonical_key = self.canonicalize_module_key(module_key)

        candidates = []
        if self.model_type:
            candidates.append(self.models_dir / f"{canonical_key}_{self.model_type}.joblib")

        # Priority 1: Generic default classifier artifact
        candidates.append(self.models_dir / f"{canonical_key}_classifier.joblib")
        # Priority 2: Logistic regression artifact
        candidates.append(self.models_dir / f"{canonical_key}_logistic_regression.joblib")
        # Priority 3: Linear SVC artifact
        candidates.append(self.models_dir / f"{canonical_key}_linear_svc.joblib")

        for path in candidates:
            # Prevent path traversal outside models_dir
            resolved = path.resolve()
            if not str(resolved).startswith(str(self.models_dir)):
                raise ValueError("Unauthorized path traversal detected")
            if resolved.exists():
                return resolved

        raise ModelNotFoundError(
            f"Topic classification model artifact not found for module '{canonical_key}'. "
            f"Expected in {self.models_dir}. Run M17 training pipeline first."
        )

    def load_model(self, module_key: str) -> Dict[str, Any]:
        """Load and cache module classifier artifact from trusted local directory."""
        canonical_key = self.canonicalize_module_key(module_key)
        if canonical_key in self._cache:
            return self._cache[canonical_key]

        model_path = self.get_model_path(canonical_key)
        try:
            payload = joblib.load(model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {model_path}: {e}") from e

        if not isinstance(payload, dict) or "pipeline" not in payload or "classes" not in payload:
            raise ValueError(f"Corrupt or invalid model artifact structure: {model_path}")

        self._cache[canonical_key] = payload
        return payload

    def predict(
        self,
        module_key: str,
        question_text: str,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Predict topic with conservative abstention and explicit confidence type."""
        canonical_key = self.canonicalize_module_key(module_key)
        clean_text = normalize_text(question_text)

        model_pkg = self.load_model(canonical_key)
        pipeline = model_pkg["pipeline"]
        classes = model_pkg["classes"]
        model_type = model_pkg.get("model_type", "unknown")

        has_proba = hasattr(pipeline.named_steps["clf"], "predict_proba")
        has_decision = hasattr(pipeline.named_steps["clf"], "decision_function")

        X = [clean_text]

        if has_proba:
            probas = pipeline.predict_proba(X)[0]
            best_idx = int(np.argmax(probas))
            best_topic = str(classes[best_idx])
            raw_score = float(probas[best_idx])
            score_type = "calibrated_probability"
        elif has_decision:
            margins = pipeline.decision_function(X)[0]
            if margins.ndim == 0 or len(margins) <= 1:
                best_idx = 0
                best_topic = str(classes[0])
                raw_score = float(margins)
            else:
                best_idx = int(np.argmax(margins))
                best_topic = str(classes[best_idx])
                raw_score = float(margins[best_idx])
            score_type = "uncalibrated_decision_score"
        else:
            pred = pipeline.predict(X)[0]
            best_topic = str(pred)
            raw_score = 1.0
            score_type = "binary_decision"

        active_threshold = threshold if threshold is not None else self.default_threshold
        if not (0.0 <= active_threshold <= 10.0):
            raise ValueError("Abstention threshold must be a non-negative number")

        # Conservative abstention decision
        if raw_score >= active_threshold:
            decision = "classified"
            predicted_topic = best_topic
            provisional_topic_id = f"provisional_{_slug(best_topic)}"
            abstained = False
        else:
            decision = "needs_review"
            predicted_topic = "unclassified"
            provisional_topic_id = None
            abstained = True

        return {
            "module_key": canonical_key,
            "question_text": question_text,
            "predicted_topic": predicted_topic,
            "candidate_topic": best_topic if abstained else predicted_topic,
            "provisional_topic_id": provisional_topic_id,
            "confidence_score": round(raw_score, 4),
            "score_type": score_type,
            "decision": decision,
            "abstention_threshold": round(active_threshold, 4),
            "abstained": abstained,
            "model_type": model_type,
            "verification_status": "unverified",
            "academic_verification": "pending_lecturer_review",
            "source_type": "synthetic_model_inference",
            "disclaimer": (
                "Experimental topic prediction trained on synthetic development data. "
                "Must be independently verified by an academic lecturer before any official use."
            ),
        }
