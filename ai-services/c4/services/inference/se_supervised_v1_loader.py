"""Load SE supervised simulation models (se-supervised-sim-v1).

Isolated from se-supervised-sim-v0 / ASSISTments / path RL. Simulation-only.
Does not auto-wire into se-path-sim-v1 dynamics.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np
import pandas as pd

# Ensure custom joblib classes resolve against live v1 package.
import training_se_supervised_v1.features_response  # noqa: F401
import training_se_supervised_v1.models_exam  # noqa: F401
import training_se_supervised_v1.models_response  # noqa: F401
from catalogues.c1_practice_full_2026_10 import N_TOPICS, catalogue_hash
from training_se_supervised_v1.contract import (
    CLASSIFICATION_PROB_THRESHOLD,
    PASS_THRESHOLD,
)
from training_se_supervised_v1.features_response import FeatureScaler

PROTOCOL = "se-supervised-sim-v1"
DOMAIN = "se_simulation"
BUNDLE_RUN = "train_full_se-supervised-sim-v1_20261014T002241.664Z"
EXPECTED_CATALOGUE_HASH = (
    "95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622"
)
EXPECTED_RESPONSE_DIM = 54
EXPECTED_EXAM_DIM = 98

EXPECTED_RESPONSE_NAME = "hist_gradient_boosting_classifier"
EXPECTED_EXAM_NAME = "ridge_regression"
EXPECTED_PASS_NAME = "logistic_regression"


class SeSupervisedV1LoadError(RuntimeError):
    """SE supervised v1 artifacts unavailable — v1 endpoints must 503; no v0 fallback."""


class SeSupervisedV1ValidationError(ValueError):
    """Malformed SE supervised v1 predict request."""


def c4_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_se_supervised_v1_bundle_dir() -> Path:
    env = os.environ.get("C4_SE_SUPERVISED_V1_BUNDLE_DIR")
    if env:
        return Path(env)
    return c4_root() / "runtime-artifacts" / "se_supervised_sim_v1" / BUNDLE_RUN


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _finite_float(name: str, value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise SeSupervisedV1ValidationError(f"{name} must be a finite number") from exc
    if not np.isfinite(x):
        raise SeSupervisedV1ValidationError(f"{name} must be finite (got {value!r})")
    return x


def features_to_frame(
    features: Mapping[str, Any] | list[float] | dict[str, Any],
    feature_names: list[str],
    *,
    ranges: dict[str, tuple[float | None, float | None]] | None = None,
) -> pd.DataFrame:
    if isinstance(features, list):
        if len(features) != len(feature_names):
            raise SeSupervisedV1ValidationError(
                f"features list length must be {len(feature_names)} "
                f"(got {len(features)}); prefer a dict keyed by feature name"
            )
        row = {
            feature_names[i]: _finite_float(feature_names[i], features[i])
            for i in range(len(features))
        }
    elif isinstance(features, Mapping):
        missing = [n for n in feature_names if n not in features]
        if missing:
            raise SeSupervisedV1ValidationError(
                f"Missing required features ({len(missing)}): {missing[:8]}"
                + ("..." if len(missing) > 8 else "")
            )
        extra = [k for k in features.keys() if k not in feature_names]
        if extra:
            raise SeSupervisedV1ValidationError(
                f"Unexpected feature keys ({len(extra)}): {extra[:8]}"
                + ("..." if len(extra) > 8 else "")
            )
        row = {n: _finite_float(n, features[n]) for n in feature_names}
    else:
        raise SeSupervisedV1ValidationError("features must be a dict or ordered list")

    if ranges:
        for name, (lo, hi) in ranges.items():
            if name not in row:
                continue
            v = row[name]
            if lo is not None and v < lo:
                raise SeSupervisedV1ValidationError(f"{name}={v} below minimum {lo}")
            if hi is not None and v > hi:
                raise SeSupervisedV1ValidationError(f"{name}={v} above maximum {hi}")

    return pd.DataFrame([row], columns=feature_names)


@dataclass(frozen=True)
class SeSupervisedV1Ready:
    ready: bool
    protocol: str = PROTOCOL
    domain: str = DOMAIN
    synthetic: bool = True
    simulation_only: bool = True
    real_exam_validation: bool = False
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d = {
            "ready": self.ready,
            "protocol": self.protocol,
            "domain": self.domain,
            "synthetic": self.synthetic,
            "simulation_only": self.simulation_only,
            "real_exam_validation": self.real_exam_validation,
        }
        if self.detail:
            d["detail"] = self.detail
        return d


class SeSupervisedV1Policy:
    """Loads the three selected supervised v1 models with saved preprocessing."""

    def __init__(self, bundle_dir: Path | None = None) -> None:
        self.bundle_dir = (
            Path(bundle_dir) if bundle_dir else default_se_supervised_v1_bundle_dir()
        )
        self._error: str | None = None
        self._loaded = False
        self.protocol = PROTOCOL
        self.export_dir: Path | None = None
        self.feature_names_response: list[str] = []
        self.feature_names_exam: list[str] = []
        self.pass_threshold = PASS_THRESHOLD
        self.classification_prob_threshold = CLASSIFICATION_PROB_THRESHOLD
        self.catalogue_hash_loaded: str | None = None
        self.response_model_name: str | None = None
        self.exam_model_name: str | None = None
        self.pass_model_name: str | None = None
        self.response_hash: str | None = None
        self.exam_hash: str | None = None
        self.pass_hash: str | None = None
        self.runtime_versions: dict[str, Any] = {}
        self.selection: dict[str, Any] = {}
        self.domain_markers: dict[str, Any] = {}
        self._response_bundle: dict[str, Any] | None = None
        self._exam_bundle: dict[str, Any] | None = None
        self._pass_bundle: dict[str, Any] | None = None
        try:
            self._load()
            self._loaded = True
        except Exception as exc:  # noqa: BLE001
            self._error = str(exc)
            self._loaded = False

    @property
    def ready(self) -> bool:
        return self._loaded and self._error is None

    def readiness(self) -> dict[str, Any]:
        if not self.ready:
            return SeSupervisedV1Ready(
                ready=False,
                detail=self._error or "SE supervised v1 models not loaded",
            ).as_dict()
        return {
            **SeSupervisedV1Ready(ready=True).as_dict(),
            "bundle_dir": str(self.bundle_dir),
            "catalogue_hash": self.catalogue_hash_loaded,
            "n_topics": N_TOPICS,
            "models": {
                "response": {
                    "name": self.response_model_name,
                    "path": "models/response_selected.joblib",
                    "sha256": self.response_hash,
                    "n_features": len(self.feature_names_response),
                },
                "exam_score": {
                    "name": self.exam_model_name,
                    "path": "models/exam_score_selected.joblib",
                    "sha256": self.exam_hash,
                    "n_features": len(self.feature_names_exam),
                },
                "pass": {
                    "name": self.pass_model_name,
                    "path": "models/pass_selected.joblib",
                    "sha256": self.pass_hash,
                    "pass_threshold": self.pass_threshold,
                    "pass_threshold_note": (
                        "Synthetic mock-exam fraction-correct label cutoff (0.55) "
                        "declared before training; not an institutional pass rule."
                    ),
                    "classification_prob_threshold": self.classification_prob_threshold,
                    "classification_prob_threshold_note": (
                        "Hard-class accuracy threshold (0.5) only; separate from "
                        "the 0.55 exam-score label cutoff. Not an institutional rule."
                    ),
                },
            },
            "feature_schema_response": self.feature_names_response,
            "feature_schema_exam": self.feature_names_exam,
            "runtime_versions_training": self.runtime_versions,
            "domain_markers": self.domain_markers,
            "note": (
                "Simulation inference demo only (se-supervised-sim-v1). "
                "Not validated on real SE students or actual exams. "
                "Not wired into se-path-sim-v1 RL dynamics. "
                "Isolated from se-supervised-sim-v0."
            ),
        }

    def _load(self) -> None:
        export = self.bundle_dir / "export_bundle"
        if not export.is_dir():
            raise SeSupervisedV1LoadError(
                f"Missing export_bundle under {self.bundle_dir}; "
                "refusing se-supervised-sim-v0 fallback"
            )
        self.export_dir = export

        markers_path = export / "DOMAIN_MARKERS.json"
        if markers_path.is_file():
            self.domain_markers = _read_json(markers_path)
            if self.domain_markers.get("protocol") not in (None, PROTOCOL):
                raise SeSupervisedV1LoadError(
                    f"DOMAIN_MARKERS protocol {self.domain_markers.get('protocol')!r}"
                )
            if self.domain_markers.get("real_exam_validation") is not False:
                raise SeSupervisedV1LoadError(
                    "DOMAIN_MARKERS.real_exam_validation must be false"
                )
            if self.domain_markers.get("simulation_only") is not True:
                raise SeSupervisedV1LoadError("DOMAIN_MARKERS.simulation_only must be true")

        schema_r = _read_json(export / "feature_schema_response.json")
        schema_e = _read_json(export / "feature_schema_exam.json")
        self.feature_names_response = list(schema_r["features"])
        self.feature_names_exam = list(schema_e["features"])
        if len(self.feature_names_response) != EXPECTED_RESPONSE_DIM:
            raise SeSupervisedV1LoadError(
                f"response feature dim {len(self.feature_names_response)} "
                f"!= {EXPECTED_RESPONSE_DIM}"
            )
        if len(self.feature_names_exam) != EXPECTED_EXAM_DIM:
            raise SeSupervisedV1LoadError(
                f"exam feature dim {len(self.feature_names_exam)} != {EXPECTED_EXAM_DIM}"
            )
        self.pass_threshold = float(schema_e.get("pass_threshold", PASS_THRESHOLD))
        if abs(self.pass_threshold - 0.55) > 1e-12:
            raise SeSupervisedV1LoadError(
                f"pass_threshold {self.pass_threshold} != 0.55 (saved contract)"
            )

        cat = _read_json(export / "topic_catalogue.json")
        self.catalogue_hash_loaded = str(cat.get("sha256") or "")
        if self.catalogue_hash_loaded != EXPECTED_CATALOGUE_HASH:
            raise SeSupervisedV1LoadError(
                f"catalogue hash {self.catalogue_hash_loaded} != {EXPECTED_CATALOGUE_HASH}"
            )
        if catalogue_hash() != EXPECTED_CATALOGUE_HASH:
            raise SeSupervisedV1LoadError("live catalogue hash disagrees with expected freeze")
        if int(cat.get("n_topics") or -1) != 46:
            raise SeSupervisedV1LoadError("catalogue n_topics != 46")

        self.selection = _read_json(export / "SELECTION_FROZEN.json")
        if (export / "runtime_versions.json").is_file():
            self.runtime_versions = _read_json(export / "runtime_versions.json")

        resp_path = export / "models" / "response_selected.joblib"
        exam_path = export / "models" / "exam_score_selected.joblib"
        pass_path = export / "models" / "pass_selected.joblib"
        for p in (resp_path, exam_path, pass_path):
            if not p.is_file():
                raise SeSupervisedV1LoadError(f"Missing model file: {p}")

        self.response_hash = _sha256(resp_path)
        self.exam_hash = _sha256(exam_path)
        self.pass_hash = _sha256(pass_path)

        self._response_bundle = joblib.load(resp_path)
        self._exam_bundle = joblib.load(exam_path)
        self._pass_bundle = joblib.load(pass_path)

        self.response_model_name = str(self._response_bundle["name"])
        self.exam_model_name = str(self._exam_bundle["name"])
        self.pass_model_name = str(self._pass_bundle["name"])

        if self.response_model_name != EXPECTED_RESPONSE_NAME:
            raise SeSupervisedV1LoadError(
                f"Unexpected response model {self.response_model_name!r}"
            )
        if self.exam_model_name != EXPECTED_EXAM_NAME:
            raise SeSupervisedV1LoadError(
                f"Unexpected exam_score model {self.exam_model_name!r}"
            )
        if self.pass_model_name != EXPECTED_PASS_NAME:
            raise SeSupervisedV1LoadError(
                f"Unexpected pass model {self.pass_model_name!r}"
            )

        if list(self._response_bundle["feature_names"]) != self.feature_names_response:
            raise SeSupervisedV1LoadError("response joblib feature_names mismatch schema")
        if list(self._exam_bundle["feature_names"]) != self.feature_names_exam:
            raise SeSupervisedV1LoadError("exam_score joblib feature_names mismatch schema")
        if list(self._pass_bundle["feature_names"]) != self.feature_names_exam:
            raise SeSupervisedV1LoadError("pass joblib feature_names mismatch schema")

        if self.selection.get("response", {}).get("name") != self.response_model_name:
            raise SeSupervisedV1LoadError("SELECTION_FROZEN response name mismatch")
        if self.selection.get("exam_score", {}).get("name") != self.exam_model_name:
            raise SeSupervisedV1LoadError("SELECTION_FROZEN exam_score name mismatch")
        if self.selection.get("pass", {}).get("name") != self.pass_model_name:
            raise SeSupervisedV1LoadError("SELECTION_FROZEN pass name mismatch")

    def _require_ready(self) -> None:
        if not self.ready:
            raise SeSupervisedV1LoadError(
                self._error or "SE supervised v1 models not loaded"
            )

    def validate_protocol(self, protocol: str | None) -> None:
        if protocol is None:
            return
        if protocol != PROTOCOL:
            raise SeSupervisedV1ValidationError(
                f"protocol must be '{PROTOCOL}' (got {protocol!r})"
            )

    def _common_meta(self, *, target: str, model_name: str, model_hash: str) -> dict[str, Any]:
        return {
            "selected_model": model_name,
            "model_hash": model_hash,
            "protocol": self.protocol,
            "catalogue_hash": self.catalogue_hash_loaded,
            "domain": DOMAIN,
            "synthetic": True,
            "simulation_only": True,
            "real_exam_validation": False,
            "target": target,
        }

    def predict_response(self, features: Mapping[str, Any] | list[float]) -> dict[str, Any]:
        self._require_ready()
        assert self._response_bundle is not None
        ranges = {
            "topic_prior_accuracy": (0.0, 1.0),
            "global_prior_accuracy": (0.0, 1.0),
            "topic_prior_attempts": (0.0, None),
            "topic_prior_correct": (0.0, None),
            "topic_prior_streak": (0.0, None),
            "global_prior_attempts": (0.0, None),
            "learner_step": (0.0, None),
        }
        for name in self.feature_names_response:
            if name.startswith("topic_oh_"):
                ranges[name] = (0.0, 1.0)

        df = features_to_frame(features, self.feature_names_response, ranges=ranges)
        oh_cols = [c for c in self.feature_names_response if c.startswith("topic_oh_")]
        oh_sum = float(df[oh_cols].sum(axis=1).iloc[0])
        if abs(oh_sum - 1.0) > 1e-9:
            raise SeSupervisedV1ValidationError(
                f"topic one-hot columns must sum to 1.0 (got {oh_sum})"
            )
        if df["topic_prior_correct"].iloc[0] - df["topic_prior_attempts"].iloc[0] > 1e-9:
            raise SeSupervisedV1ValidationError(
                "topic_prior_correct cannot exceed topic_prior_attempts"
            )

        scaler = FeatureScaler.from_dict(self._response_bundle["scaler"])
        x = scaler.transform_matrix(df)
        p = float(self._response_bundle["model"].predict_proba_positive(x)[0])
        return {
            **self._common_meta(
                target="y_correct",
                model_name=self.response_model_name or "",
                model_hash=self.response_hash or "",
            ),
            "p_correct": p,
            "classification_prob_threshold": self.classification_prob_threshold,
            "meaning": (
                "Predicted probability of next-attempt correctness under the "
                "synthetic SE supervised v1 simulator. Not real-student validated. "
                "classification_prob_threshold=0.5 is for hard-class accuracy only, "
                "not an institutional rule."
            ),
        }

    def predict_exam_score(
        self,
        features: Mapping[str, Any] | list[float],
        *,
        include_clipped_display: bool = True,
    ) -> dict[str, Any]:
        self._require_ready()
        assert self._exam_bundle is not None
        df = self._exam_frame(features)
        scaler = FeatureScaler.from_dict(self._exam_bundle["scaler"])
        x = scaler.transform_matrix(df)
        raw = float(self._exam_bundle["model"].predict(x)[0])
        out: dict[str, Any] = {
            **self._common_meta(
                target="y_exam_score",
                model_name=self.exam_model_name or "",
                model_hash=self.exam_hash or "",
            ),
            "exam_score_raw": raw,
            "note": (
                "Ridge may produce values outside [0,1]. exam_score_raw preserves "
                "the model output; exam_score_clipped_display is for display only."
            ),
        }
        if include_clipped_display:
            clipped = float(np.clip(raw, 0.0, 1.0))
            out["exam_score_clipped_display"] = clipped
            out["clipping_applied"] = bool(raw < 0.0 or raw > 1.0)
        return out

    def predict_pass(self, features: Mapping[str, Any] | list[float]) -> dict[str, Any]:
        self._require_ready()
        assert self._pass_bundle is not None
        df = self._exam_frame(features)
        scaler = FeatureScaler.from_dict(self._pass_bundle["scaler"])
        x = scaler.transform_matrix(df)
        p = float(self._pass_bundle["model"].predict_proba_positive(x)[0])
        return {
            **self._common_meta(
                target="y_pass",
                model_name=self.pass_model_name or "",
                model_hash=self.pass_hash or "",
            ),
            "p_pass": p,
            "pass_threshold": self.pass_threshold,
            "classification_prob_threshold": self.classification_prob_threshold,
            "meaning": (
                f"Predicted probability that synthetic mock-exam fraction-correct "
                f">= {self.pass_threshold}. The 0.55 cutoff is a labelled synthetic "
                "exam-score threshold only — not an institutional pass rule. "
                "classification_prob_threshold=0.5 is separate (hard-class accuracy). "
                "Not real-exam validated."
            ),
        }

    def _exam_frame(self, features: Mapping[str, Any] | list[float]) -> pd.DataFrame:
        ranges: dict[str, tuple[float | None, float | None]] = {
            "global_accuracy": (0.0, 1.0),
            "mean_topic_accuracy": (0.0, 1.0),
            "global_attempts": (0.0, None),
            "n_topics_practiced": (0.0, float(N_TOPICS)),
            "practice_span_hours": (0.0, None),
            "last_topic_index": (0.0, float(N_TOPICS - 1)),
        }
        for name in self.feature_names_exam:
            if name.startswith("topic_accuracy_"):
                ranges[name] = (0.0, 1.0)
            if name.startswith("topic_attempts_"):
                ranges[name] = (0.0, None)
        return features_to_frame(features, self.feature_names_exam, ranges=ranges)
