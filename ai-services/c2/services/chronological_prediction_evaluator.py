"""M20 - Chronological Evaluation and Leakage Prevention Framework.

Evaluates exam topic prediction baselines using chronological walk-forward
session splits. Strictly prevents target-examination leakage and enforces
evidence gates so unverified datasets report 'not_evaluable' rather than
fabricating empirical accuracy.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from services.historical_feature_pipeline import HistoricalFeaturePipeline
from services.prediction_readiness_service import PredictionReadinessAssessor
from services.topic_prediction_engine import TopicPredictionEngine


class ChronologicalPredictionEvaluator:
    """Evaluates prediction models using strictly chronological historical splits."""

    def __init__(
        self,
        feature_pipeline: Optional[HistoricalFeaturePipeline] = None,
        readiness_assessor: Optional[PredictionReadinessAssessor] = None,
        prediction_engine: Optional[TopicPredictionEngine] = None,
    ):
        self.feature_pipeline = feature_pipeline or HistoricalFeaturePipeline()
        self.readiness_assessor = readiness_assessor or PredictionReadinessAssessor()
        self.prediction_engine = prediction_engine or TopicPredictionEngine(
            feature_pipeline=self.feature_pipeline,
            readiness_assessor=self.readiness_assessor,
        )

    def evaluate(self, module_key: str) -> Dict[str, Any]:
        """Perform chronological evaluation for a module if sufficient verified evidence exists.

        If verified ground truth or independent sessions are insufficient,
        returns a structured 'not_evaluable' status explaining the limitation.
        """
        readiness = self.readiness_assessor.assess(module_key)

        # Gate: Module must be in an evaluable state and have verified sessions
        if readiness["status"] not in ("experimental_prediction_ready", "validated_prediction_ready"):
            return {
                "module_key": module_key,
                "status": "not_evaluable",
                "is_evaluable": False,
                "reason": (
                    f"Chronological evaluation requires verified ground-truth examination labels "
                    f"and at least 3 distinct historical sessions. Current readiness state is '{readiness['status']}'."
                ),
                "readiness": readiness,
                "sample_size_limitations": [
                    "Walk-forward chronological evaluation requires at least 2 training sessions and 1 held-out test session.",
                    "The current authentic dataset contains 0 lecturer-verified topic labels.",
                    "No empirical metrics can be reported without verified ground truth.",
                ],
                "evaluation_protocol": "walk_forward_chronological_split",
                "provenance": {
                    "dataset_type": "authentic_historical_examinations",
                    "synthetic_fixture": False,
                },
                "metrics": None,
            }

        # Build verified session sequence
        feature_result = self.feature_pipeline.build_features(module_key)
        sessions = feature_result.get("sessions", [])

        if len(sessions) < 3:
            return {
                "module_key": module_key,
                "status": "not_evaluable",
                "is_evaluable": False,
                "reason": (
                    f"Insufficient distinct examination sessions for walk-forward evaluation. "
                    f"Found {len(sessions)} sessions; minimum 3 required."
                ),
                "readiness": readiness,
                "sample_size_limitations": [
                    "Walk-forward chronological evaluation requires at least 2 training sessions and 1 held-out test session.",
                ],
                "evaluation_protocol": "walk_forward_chronological_split",
                "provenance": {
                    "dataset_type": "authentic_historical_examinations",
                    "synthetic_fixture": False,
                },
                "metrics": None,
            }

        # Run walk-forward chronological evaluation on authentic sessions
        return self._run_walk_forward(
            module_key=module_key,
            taxonomy=feature_result.get("taxonomy", []),
            sessions=sessions,
            readiness=readiness,
            is_synthetic_fixture=False,
        )

    def _run_walk_forward(
        self,
        module_key: str,
        taxonomy: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]],
        readiness: Dict[str, Any],
        is_synthetic_fixture: bool = False,
    ) -> Dict[str, Any]:
        """Execute walk-forward splits across sorted sessions:

        For split t (from index 2 to len(sessions)-1):
          Train sessions: sessions[0 ... t-1]
          Test session:   sessions[t]
        """
        all_topic_ids = [t["topic_id"] for t in taxonomy]
        k_values = [3, 5]

        # Results per baseline: baseline_a, baseline_b, baseline_c
        baseline_splits: Dict[str, List[Dict[str, Any]]] = {
            "historical_frequency": [],
            "recency_weighted_frequency": [],
            "regularized_statistical_model": [],
        }

        # Number of splits
        n_splits = len(sessions) - 2

        for t in range(2, len(sessions)):
            train_sessions = sessions[:t]
            test_session = sessions[t]
            test_session_id = test_session["session_id"]
            actual_topics = set(test_session["topics_present"].keys())

            # Evaluate each baseline on this split
            for baseline_id in baseline_splits.keys():
                predictions = self._predict_split(
                    baseline_id=baseline_id,
                    taxonomy=taxonomy,
                    train_sessions=train_sessions,
                )

                # Compute ranking & probability metrics on test_session
                split_metrics = self._compute_split_metrics(
                    predictions=predictions,
                    actual_topics=actual_topics,
                    all_topic_ids=all_topic_ids,
                    k_values=k_values,
                )
                split_metrics["test_session_id"] = test_session_id
                split_metrics["train_sessions_count"] = len(train_sessions)
                split_metrics["actual_topics_count"] = len(actual_topics)

                baseline_splits[baseline_id].append(split_metrics)

        # Aggregate across splits
        aggregated_models: Dict[str, Any] = {}
        for baseline_id, splits in baseline_splits.items():
            aggregated_models[baseline_id] = self._aggregate_splits(splits, k_values)

        return {
            "module_key": module_key,
            "status": "evaluated",
            "is_evaluable": True,
            "evaluation_protocol": "walk_forward_chronological_split",
            "number_of_splits": n_splits,
            "provenance": {
                "dataset_type": "synthetic_test_fixture" if is_synthetic_fixture else "authentic_historical_examinations",
                "synthetic_fixture": is_synthetic_fixture,
                "warning": (
                    "FOR SOFTWARE TEST PURPOSES ONLY. DO NOT USE AS EMPIRICAL RESEARCH FINDINGS."
                    if is_synthetic_fixture
                    else None
                ),
            },
            "readiness": readiness,
            "models": aggregated_models,
            "sample_size_limitations": [
                f"Evaluation evaluated on {n_splits} chronological walk-forward split(s).",
                "Small-sample size induces variance in metric estimates.",
                "Performance reflects historical examination splits only and may not predict syllabus structural changes.",
            ],
        }

    def _predict_split(
        self,
        baseline_id: str,
        taxonomy: List[Dict[str, Any]],
        train_sessions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate topic predictions from train_sessions only (strictly no test session data)."""
        n_sessions = len(train_sessions)
        preds = []

        if baseline_id == "historical_frequency":
            for topic in taxonomy:
                tid = topic["topic_id"]
                appearances = sum(1 for s in train_sessions if tid in s.get("topics_present", {}))
                score = appearances / n_sessions if n_sessions > 0 else 0.0
                preds.append({"topic_id": tid, "score": score, "probability": score})

        elif baseline_id == "recency_weighted_frequency":
            decay = 0.75
            weights = [decay ** (n_sessions - 1 - idx) for idx in range(n_sessions)]
            w_sum = sum(weights) or 1.0

            for topic in taxonomy:
                tid = topic["topic_id"]
                w_appearances = sum(
                    weights[idx] for idx, s in enumerate(train_sessions) if tid in s.get("topics_present", {})
                )
                score = w_appearances / w_sum
                preds.append({"topic_id": tid, "score": score, "probability": score})

        elif baseline_id == "regularized_statistical_model":
            # Simple ridge regression on train_sessions
            for topic in taxonomy:
                tid = topic["topic_id"]
                y_hist = [1.0 if tid in s.get("topics_present", {}) else 0.0 for s in train_sessions]
                # If only 2 sessions, fall back to weighted frequency
                if len(train_sessions) < 3:
                    score = sum(y_hist) / len(y_hist)
                else:
                    # Simple trend slope + mean
                    x = list(range(len(y_hist)))
                    mean_x = sum(x) / len(x)
                    mean_y = sum(y_hist) / len(y_hist)
                    var_x = sum((xi - mean_x) ** 2 for xi in x) or 1.0
                    cov_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y_hist))
                    slope = cov_xy / (var_x + 1.0)  # Ridge shrunk
                    intercept = mean_y - slope * mean_x
                    raw = intercept + slope * len(y_hist)  # predict next session
                    score = max(0.0, min(1.0, raw))
                preds.append({"topic_id": tid, "score": score, "probability": score})

        # Rank predictions descending by score
        preds.sort(key=lambda p: p["score"], reverse=True)
        for rank, p in enumerate(preds, start=1):
            p["rank"] = rank

        return preds

    def _compute_split_metrics(
        self,
        predictions: List[Dict[str, Any]],
        actual_topics: set[str],
        all_topic_ids: List[str],
        k_values: List[int],
    ) -> Dict[str, Any]:
        """Compute precision@K, recall@K, MRR, and Brier score on a single test session."""
        metrics: Dict[str, Any] = {}

        # Precision@K and Recall@K
        n_actual = len(actual_topics)
        for k in k_values:
            top_k = predictions[:k]
            top_k_ids = {p["topic_id"] for p in top_k}
            hits = len(top_k_ids.intersection(actual_topics))

            precision_k = round(hits / k, 4) if k > 0 else 0.0
            recall_k = round(hits / n_actual, 4) if n_actual > 0 else 0.0

            metrics[f"precision@{k}"] = precision_k
            metrics[f"recall@{k}"] = recall_k

        # Mean Reciprocal Rank (MRR) - rank of first relevant topic
        mrr = 0.0
        for p in predictions:
            if p["topic_id"] in actual_topics:
                mrr = round(1.0 / p["rank"], 4)
                break
        metrics["reciprocal_rank"] = mrr

        # Brier Score = mean((probability - actual)^2) across all topics
        # actual = 1 if topic in actual_topics else 0
        pred_map = {p["topic_id"]: p.get("probability", p["score"]) for p in predictions}
        brier_sum = 0.0
        for tid in all_topic_ids:
            prob = pred_map.get(tid, 0.0)
            actual = 1.0 if tid in actual_topics else 0.0
            brier_sum += (prob - actual) ** 2

        brier_score = round(brier_sum / len(all_topic_ids), 4) if all_topic_ids else 0.0
        metrics["brier_score"] = brier_score

        return metrics

    def _aggregate_splits(
        self,
        splits: List[Dict[str, Any]],
        k_values: List[int],
    ) -> Dict[str, Any]:
        """Aggregate metric lists across chronological splits."""
        if not splits:
            return {"splits": [], "summary": {}}

        n = len(splits)
        summary: Dict[str, Any] = {}

        for k in k_values:
            p_key = f"precision@{k}"
            r_key = f"recall@{k}"
            p_vals = [s[p_key] for s in splits]
            r_vals = [s[r_key] for s in splits]
            summary[f"mean_{p_key}"] = round(sum(p_vals) / n, 4)
            summary[f"mean_{r_key}"] = round(sum(r_vals) / n, 4)

        rr_vals = [s["reciprocal_rank"] for s in splits]
        summary["mean_reciprocal_rank"] = round(sum(rr_vals) / n, 4)

        brier_vals = [s["brier_score"] for s in splits]
        summary["mean_brier_score"] = round(sum(brier_vals) / n, 4)

        return {
            "splits": splits,
            "summary": summary,
        }

    # -------------------------------------------------------------
    # Deterministic Synthetic Fixture for Software Testing
    # -------------------------------------------------------------

    def evaluate_synthetic_test_fixture(
        self,
        module_key: str = "synthetic_eval_fixture",
    ) -> Dict[str, Any]:
        """Run the walk-forward evaluation algorithm on a deterministic synthetic test fixture.

        Used strictly to verify evaluation math, metric formulas, and chronological
        split isolation in test suites. Explicitly marked as a test fixture.
        """
        taxonomy = [
            {"topic_id": "topic_a", "display_name": "Topic A"},
            {"topic_id": "topic_b", "display_name": "Topic B"},
            {"topic_id": "topic_c", "display_name": "Topic C"},
            {"topic_id": "topic_d", "display_name": "Topic D"},
            {"topic_id": "topic_e", "display_name": "Topic E"},
        ]

        # 4 deterministic chronological sessions
        # S0: A, B, C
        # S1: B, C, D
        # S2: A, C, E  (test split 1: train on S0, S1)
        # S3: B, D, E  (test split 2: train on S0, S1, S2)
        sessions = [
            {
                "session_id": "fixture_2020_final",
                "academic_year": 2020,
                "topics_present": {"topic_a": 2, "topic_b": 1, "topic_c": 3},
            },
            {
                "session_id": "fixture_2021_final",
                "academic_year": 2021,
                "topics_present": {"topic_b": 2, "topic_c": 2, "topic_d": 1},
            },
            {
                "session_id": "fixture_2022_final",
                "academic_year": 2022,
                "topics_present": {"topic_a": 1, "topic_c": 2, "topic_e": 2},
            },
            {
                "session_id": "fixture_2023_final",
                "academic_year": 2023,
                "topics_present": {"topic_b": 3, "topic_d": 2, "topic_e": 1},
            },
        ]

        readiness = {
            "status": "experimental_prediction_ready",
            "verified_question_count": 20,
            "distinct_papers": 4,
            "distinct_years": 4,
            "evidence_coverage": 1.0,
        }

        return self._run_walk_forward(
            module_key=module_key,
            taxonomy=taxonomy,
            sessions=sessions,
            readiness=readiness,
            is_synthetic_fixture=True,
        )
