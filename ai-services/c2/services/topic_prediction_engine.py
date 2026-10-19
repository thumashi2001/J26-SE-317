"""M20: Modular baseline models for exam topic prediction.

Implements:
- Baseline A: Historical Frequency
- Baseline B: Recency-Weighted Frequency
- Baseline C: Simple Regularized Statistical Model
"""

import math
from services.historical_feature_pipeline import HistoricalFeaturePipeline
from services.prediction_readiness_service import (
    PredictionReadinessAssessor,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_AWAITING_VERIFICATION,
    STATUS_HISTORICAL_ANALYSIS_READY,
    STATUS_EXPERIMENTAL_PREDICTION_READY,
    STATUS_VALIDATED_PREDICTION_READY,
)
from services.topic_taxonomy import TopicTaxonomy


class TopicPredictionEngine:
    """
    Computes topic prediction scores for upcoming examination sessions
    using defensible baseline approaches with strict readiness gating.
    """

    METHOD_HISTORICAL_FREQUENCY = "historical_frequency"
    METHOD_RECENCY_WEIGHTED = "recency_weighted"
    METHOD_REGULARIZED_STATISTICAL = "regularized_statistical"

    SUPPORTED_METHODS = [
        METHOD_HISTORICAL_FREQUENCY,
        METHOD_RECENCY_WEIGHTED,
        METHOD_REGULARIZED_STATISTICAL,
    ]

    def __init__(self, feature_pipeline=None, readiness_assessor=None, taxonomy=None):
        self.feature_pipeline = (
            feature_pipeline if feature_pipeline is not None
            else HistoricalFeaturePipeline()
        )
        self.readiness_assessor = (
            readiness_assessor if readiness_assessor is not None
            else PredictionReadinessAssessor()
        )
        self.taxonomy = taxonomy if taxonomy is not None else TopicTaxonomy()

    def generate_predictions(self, module_key, method=METHOD_RECENCY_WEIGHTED):
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unsupported prediction method '{method}'. Supported: {self.SUPPORTED_METHODS}")

        # 1. Evaluate Prediction Readiness
        readiness = self.readiness_assessor.assess_module(module_key)
        status = readiness["readiness_status"]

        # When evidence is insufficient or awaiting verification, training cannot proceed
        if status in {STATUS_INSUFFICIENT_EVIDENCE, STATUS_AWAITING_VERIFICATION}:
            return {
                "status": "model_not_trained",
                "module_key": module_key,
                "readiness_status": status,
                "model_method": method,
                "prediction_available": False,
                "future_probabilities_available": False,
                "predictions": [],
                "missing_requirements": readiness["missing_requirements"],
                "reasons": readiness["reasons_unavailable"],
                "academic_integrity_notice": (
                    "Model training is inhibited to preserve scientific integrity. "
                    "Predictions require lecturer-verified topic labels and independent examination sessions."
                ),
            }

        # 2. Extract Causal Features
        feature_data = self.feature_pipeline.build_features_for_module(module_key)
        if feature_data.get("status") != "success":
            return {
                "status": "model_not_trained",
                "module_key": module_key,
                "readiness_status": status,
                "model_method": method,
                "prediction_available": False,
                "future_probabilities_available": False,
                "predictions": [],
                "missing_requirements": ["Causal historical features"],
                "reasons": [feature_data.get("reason", "Unable to extract historical features")],
                "academic_integrity_notice": "Feature pipeline could not establish causal historical sessions.",
            }

        target_features = feature_data.get("target_session_features", [])
        historical_records = feature_data.get("feature_records", [])
        sessions_count = feature_data.get("sessions_count", 0)

        # 3. Model Inference based on selected baseline
        ranked_predictions = []
        module_tax = self.taxonomy.get_module_taxonomy(module_key)
        tax_topics = {t["topic_id"]: t["topic_name"] for t in module_tax.get("topics", [])} if module_tax else {}

        if method == self.METHOD_HISTORICAL_FREQUENCY:
            ranked_predictions = self._infer_historical_frequency(target_features, tax_topics)

        elif method == self.METHOD_RECENCY_WEIGHTED:
            ranked_predictions = self._infer_recency_weighted(target_features, tax_topics)

        elif method == self.METHOD_REGULARIZED_STATISTICAL:
            # Low-complexity regularized linear scoring model
            # Requires minimum 4 independent historical sessions for training
            if sessions_count < 4 or len(historical_records) < 10:
                # Fallback to recency-weighted with transparent reporting
                fallback_res = self.generate_predictions(module_key, method=self.METHOD_RECENCY_WEIGHTED)
                fallback_res["model_method"] = self.METHOD_REGULARIZED_STATISTICAL
                fallback_res["notice"] = (
                    f"Statistical model requires >= 4 historical sessions (current: {sessions_count}). "
                    "Output reverted to Recency-Weighted baseline to prevent severe overfitting."
                )
                return fallback_res

            score_type = "experimental_priority_score"
            ranked_predictions = self._fit_predict_regularized(historical_records, target_features, tax_topics)

        # Sort predictions by score descending
        ranked_predictions.sort(key=lambda p: (p["score"], p["historical_occurrences"]), reverse=True)
        for idx, item in enumerate(ranked_predictions, start=1):
            item["rank"] = idx

        # Determine whether predictions are experimental or validated
        is_validated = status == STATUS_VALIDATED_PREDICTION_READY

        return {
            "status": "prediction_ready" if status in {STATUS_EXPERIMENTAL_PREDICTION_READY, STATUS_VALIDATED_PREDICTION_READY} else "historical_analysis_only",
            "module_key": module_key,
            "readiness_status": status,
            "model_method": method,
            "prediction_available": True,
            "future_probabilities_available": is_validated,
            "score_type": "calibrated_probability" if is_validated else score_type,
            "probabilities_sum_to_one": False,
            "sessions_analyzed": sessions_count,
            "predictions": ranked_predictions,
            "disclaimer": (
                "Scores represent topic-priority estimates derived from chronological past-paper patterns. "
                "Because examinations contain multiple concurrent topics, scores are non-mutually-exclusive "
                "and do not sum to 100%."
            ),
        }

    def _fit_predict_regularized(self, historical_records, target_features, tax_topics):
        """Fit a simple L2-regularized linear scoring model across historical session records."""
        # Simple ridge regression on [historical_frequency, recency_weighted_frequency, sessions_since_last]
        # Target: target_appeared (0 or 1)
        # Using analytical closed-form ridge regression: w = (X^T X + alpha*I)^(-1) X^T y
        X = []
        y = []
        for r in historical_records:
            if r["prior_sessions_count"] == 0:
                continue
            # Features: [bias=1.0, hist_freq, recency_freq, gap_norm]
            gap = r["sessions_since_last_appearance"]
            gap_feature = 1.0 / (1.0 + gap) if gap >= 0 else 0.0
            X.append([1.0, r["historical_frequency"], r["recency_weighted_frequency"], gap_feature])
            y.append(float(r["target_appeared"]))

        if len(X) < 5:
            # Not enough data for matrix inversion, return basic recency
            return [
                {
                    "topic_id": feat["topic_id"],
                    "topic_name": tax_topics.get(feat["topic_id"], feat["topic_id"]),
                    "score": round(feat["recency_weighted_frequency"], 4),
                    "score_type": "experimental_priority_score",
                    "historical_occurrences": feat["historical_occurrences_count"],
                    "prior_sessions_observed": feat["prior_sessions_count"],
                    "sessions_since_last_appearance": feat["sessions_since_last_appearance"],
                    "confidence_band": "low",
                }
                for feat in target_features
            ]

        # Regularized weights computation
        n_features = 4
        alpha = 1.0  # L2 regularization strength

        # X^T X
        XtX = [[0.0 for _ in range(n_features)] for _ in range(n_features)]
        Xty = [0.0 for _ in range(n_features)]

        for row, target in zip(X, y):
            for i in range(n_features):
                Xty[i] += row[i] * target
                for j in range(n_features):
                    XtX[i][j] += row[i] * row[j]

        # Add ridge penalty (alpha * I) except to bias
        for i in range(1, n_features):
            XtX[i][i] += alpha

        # Simple 4x4 matrix solve using Gaussian elimination
        weights = self._solve_linear_system(XtX, Xty)

        # Predict for target session
        predictions = []
        for feat in target_features:
            tid = feat["topic_id"]
            gap = feat["sessions_since_last_appearance"]
            gap_feature = 1.0 / (1.0 + gap) if gap >= 0 else 0.0
            x_target = [1.0, feat["historical_frequency"], feat["recency_weighted_frequency"], gap_feature]

            # Linear score clamped to [0.0, 1.0]
            raw_score = sum(w * x for w, x in zip(weights, x_target))
            clamped_score = max(0.0, min(1.0, raw_score))

            predictions.append({
                "topic_id": tid,
                "topic_name": tax_topics.get(tid, tid),
                "score": round(clamped_score, 4),
                "score_type": "experimental_priority_score",
                "historical_occurrences": feat["historical_occurrences_count"],
                "prior_sessions_observed": feat["prior_sessions_count"],
                "sessions_since_last_appearance": feat["sessions_since_last_appearance"],
                "confidence_band": "moderate",
            })

        return predictions

    @staticmethod
    def _solve_linear_system(A, b):
        """Solve Ax = b for small matrices using Gaussian elimination with partial pivoting."""
        n = len(b)
        M = [A[i][:] + [b[i]] for i in range(n)]

        for i in range(n):
            # Pivot
            max_row = max(range(i, n), key=lambda r: abs(M[r][i]))
            M[i], M[max_row] = M[max_row], M[i]

            pivot = M[i][i]
            if abs(pivot) < 1e-9:
                return [0.25] * n  # Fallback uniform weights if singular

            for j in range(i, n + 1):
                M[i][j] /= pivot

            for r in range(n):
                if r != i:
                    factor = M[r][i]
                    for c in range(i, n + 1):
                        M[r][c] -= factor * M[i][c]

        return [M[i][n] for i in range(n)]

    def _infer_historical_frequency(self, target_features, tax_topics):
        """Compute Baseline A predictions from target features."""
        ranked = []
        for feat in target_features:
            tid = feat["topic_id"]
            score = feat["historical_frequency"]
            ranked.append({
                "topic_id": tid,
                "topic_name": tax_topics.get(tid, tid),
                "score": round(score, 4),
                "score_type": "experimental_priority_score",
                "historical_occurrences": feat.get("historical_occurrences_count", 0),
                "prior_sessions_observed": feat.get("prior_sessions_count", 0),
                "sessions_since_last_appearance": feat.get("sessions_since_last_appearance", -1),
                "confidence_band": "low" if feat.get("prior_sessions_count", 0) < 3 else "moderate",
            })
        ranked.sort(key=lambda p: (p["score"], p["historical_occurrences"]), reverse=True)
        for idx, item in enumerate(ranked, start=1):
            item["rank"] = idx
        return ranked

    def _infer_recency_weighted(self, target_features, tax_topics):
        """Compute Baseline B predictions from target features."""
        ranked = []
        for feat in target_features:
            tid = feat["topic_id"]
            score = feat["recency_weighted_frequency"]
            ranked.append({
                "topic_id": tid,
                "topic_name": tax_topics.get(tid, tid),
                "score": round(score, 4),
                "score_type": "experimental_priority_score",
                "historical_occurrences": feat.get("historical_occurrences_count", 0),
                "recency_weighted_score": feat.get("recency_weighted_frequency", 0.0),
                "prior_sessions_observed": feat.get("prior_sessions_count", 0),
                "sessions_since_last_appearance": feat.get("sessions_since_last_appearance", -1),
                "confidence_band": "low" if feat.get("prior_sessions_count", 0) < 3 else "moderate",
            })
        ranked.sort(key=lambda p: (p["score"], p["historical_occurrences"]), reverse=True)
        for idx, item in enumerate(ranked, start=1):
            item["rank"] = idx
        return ranked

    def predict_all_baselines(self, module_key, target_period=None):
        """Run and return all three prediction baselines."""
        return {
            "baseline_a": self.generate_predictions(module_key, method=self.METHOD_HISTORICAL_FREQUENCY),
            "baseline_b": self.generate_predictions(module_key, method=self.METHOD_RECENCY_WEIGHTED),
            "baseline_c": self.generate_predictions(module_key, method=self.METHOD_REGULARIZED_STATISTICAL),
        }
