"""M22.2: Isolated Synthetic Topic Prediction Demonstration Service.

Provides a deterministic, explicitly synthetic multi-session exam history
for SLIIT Year 3 SE curriculum topics to demonstrate:
1. Baseline A: Historical Frequency
2. Baseline B: Recency-Weighted Frequency (lambda=0.75)
3. Baseline C: Regularized Statistical Model
4. Chronological walk-forward evaluation (Precision@3, Recall@3, MRR, Brier Score)

Strictly isolated from authentic examination records and lecturer verification repositories.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.chronological_prediction_evaluator import ChronologicalPredictionEvaluator
from services.taxonomy_approval_service import TaxonomyApprovalService


class SyntheticTopicPredictionService:
    """Generates deterministic synthetic exam histories and executes baseline topic predictions."""

    CONSTRUCTION_METHODOLOGY = (
        "Deterministic 5-year chronological sequence (2019-2023) modeling authentic SLIIT final examinations. "
        "Foundational syllabus topics (Index 0) appear consistently in 100% of sessions. "
        "Core topics (Index 1) and alternating topics (Index 2) appear in 60% of sessions. "
        "Emerging topics (Index 3) appear only in the most recent 3 sessions (2021-2023) to model syllabus modernization. "
        "Legacy topics (Index 4) appear only in early sessions (2019-2020) and are phased out. "
        "All data is fully synthetic, deterministic, and isolated from authentic student/paper records."
    )

    DISCLAIMER = (
        "ACADEMIC RESEARCH DEMONSTRATION ONLY: These predictions and metrics are produced "
        "from an isolated, deterministic synthetic exam sequence. They are designed exclusively "
        "for viva evaluation of Baselines A, B, C and chronological walk-forward validation. "
        "They are NOT genuine predictions for any future SLIIT examination."
    )

    ACADEMIC_INTEGRITY_NOTICE = (
        "Authentic examination predictions remain strictly blocked ('awaiting_lecturer_verification') "
        "because 0 of 443 authentic past-paper questions currently have lecturer-verified topic labels. "
        "This experimental view demonstrates algorithm behavior without compromising authentic data integrity."
    )

    def __init__(
        self,
        taxonomy_service: Optional[TaxonomyApprovalService] = None,
        evaluator: Optional[ChronologicalPredictionEvaluator] = None,
    ):
        self.taxonomy_service = taxonomy_service or TaxonomyApprovalService()
        self.evaluator = evaluator or ChronologicalPredictionEvaluator()

    def build_synthetic_exam_history(self, module_key: str) -> Dict[str, Any]:
        """Construct deterministic synthetic multi-session examination sequence for a module."""
        canon_key = self.taxonomy_service.canonicalize_module_key(module_key)
        tax_data = self.taxonomy_service.get_taxonomy(canon_key)
        topics = tax_data.get("topics", [])

        if not topics:
            raise ValueError(f"Module '{module_key}' has no curriculum topics defined in taxonomy.")

        topic_ids = [t["topic_id"] for t in topics]
        m = len(topic_ids)

        # Deterministic appearance schedule across 5 annual exam sittings (2019-2023)
        schedule: Dict[int, List[int]] = {
            2019: [0, 1, 2, 4],
            2020: [0, 2, 4, 5] if m > 5 else [0, 2, 4],
            2021: [0, 1, 3],
            2022: [0, 1, 3, 5] if m > 5 else [0, 1, 3],
            2023: [0, 2, 3, 5] if m > 5 else [0, 2, 3],
        }

        years = sorted(schedule.keys())
        sessions = []

        for yr in years:
            active_indices = [idx for idx in schedule[yr] if idx < m]
            topics_present: Dict[str, int] = {}
            topic_marks: Dict[str, int] = {}

            # Distribute 100 marks across active topics
            base_marks = 100 // max(len(active_indices), 1)
            rem_marks = 100 % max(len(active_indices), 1)

            for i, idx in enumerate(active_indices):
                tid = topic_ids[idx]
                q_count = 2 if idx == 0 else 1
                marks = base_marks + (rem_marks if i == 0 else 0)
                topics_present[tid] = q_count
                topic_marks[tid] = marks

            sessions.append({
                "session_id": f"synthetic_{canon_key}_{yr}_final",
                "academic_year": yr,
                "examination_type": "Regular End-Semester Final Examination",
                "total_marks": 100,
                "total_questions": sum(topics_present.values()),
                "topics_present": topics_present,
                "topic_marks": topic_marks,
            })

        return {
            "module_key": canon_key,
            "module_name": tax_data.get("module_name", canon_key),
            "topics": topics,
            "sessions": sessions,
        }

    def generate_experimental_demonstration(
        self,
        module_key: str,
        target_period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute all three baseline prediction algorithms and walk-forward chronological evaluation."""
        dataset = self.build_synthetic_exam_history(module_key)
        canon_key = dataset["module_key"]
        module_name = dataset["module_name"]
        topics = dataset["topics"]
        sessions = dataset["sessions"]

        tax_formatted = [
            {"topic_id": t["topic_id"], "display_name": t["topic_name"]}
            for t in topics
        ]
        topic_name_map = {t["topic_id"]: t["topic_name"] for t in topics}

        # 1. Chronological Walk-Forward Evaluation
        # Readiness record signaling experimental demonstration status
        readiness = {
            "status": "experimental_prediction_ready",
            "verified_question_count": sum(s["total_questions"] for s in sessions),
            "distinct_papers": len(sessions),
            "distinct_years": len(sessions),
            "evidence_coverage": 1.0,
        }

        eval_res = self.evaluator._run_walk_forward(
            module_key=canon_key,
            taxonomy=tax_formatted,
            sessions=sessions,
            readiness=readiness,
            is_synthetic_fixture=True,
        )

        # 2. Upcoming Session Topic Predictions (using all 5 observed sessions as prior history)
        preds_a = self.evaluator._predict_split("historical_frequency", tax_formatted, sessions)
        preds_b = self.evaluator._predict_split("recency_weighted_frequency", tax_formatted, sessions)
        preds_c = self.evaluator._predict_split("regularized_statistical_model", tax_formatted, sessions)

        def _format_preds(raw_preds: List[Dict[str, Any]], score_type_label: str) -> List[Dict[str, Any]]:
            formatted = []
            for p in raw_preds:
                formatted.append({
                    "rank": p["rank"],
                    "topic_id": p["topic_id"],
                    "topic_name": topic_name_map.get(p["topic_id"], p["topic_id"]),
                    "score": round(float(p["score"]), 4),
                    "probability": round(float(p.get("probability", p["score"])), 4),
                    "score_type": score_type_label,
                })
            return formatted

        ranked_a = _format_preds(preds_a, "historical_frequency_score")
        ranked_b = _format_preds(preds_b, "recency_weighted_priority_score")
        ranked_c = _format_preds(preds_c, "regularized_trend_score")

        # 3. Format Evaluation Splits & Comparative Metrics
        splits_detail = []
        for t in range(2, len(sessions)):
            train_sessions = sessions[:t]
            test_session = sessions[t]
            splits_detail.append({
                "split_index": t - 1,
                "train_sessions_count": len(train_sessions),
                "train_academic_years": [s["academic_year"] for s in train_sessions],
                "test_session_id": test_session["session_id"],
                "test_academic_year": test_session["academic_year"],
                "actual_topics_tested": list(test_session["topics_present"].keys()),
                "actual_topics_count": len(test_session["topics_present"]),
            })

        models_eval = eval_res.get("models", {})

        return {
            "provenance": "synthetic_experimental_demonstration",
            "is_experimental_demonstration": True,
            "disclaimer": self.DISCLAIMER,
            "academic_integrity_notice": self.ACADEMIC_INTEGRITY_NOTICE,
            "module_key": canon_key,
            "module_name": module_name,
            "target_period": target_period or "next_session",
            "synthetic_session_count": len(sessions),
            "synthetic_sessions": [
                {
                    "session_id": s["session_id"],
                    "academic_year": s["academic_year"],
                    "examination_type": s["examination_type"],
                    "total_questions": s["total_questions"],
                    "total_marks": s["total_marks"],
                    "topics_present": list(s["topics_present"].keys()),
                }
                for s in sessions
            ],
            "construction_methodology": self.CONSTRUCTION_METHODOLOGY,
            "methods": {
                "baseline_a": {
                    "method_id": "historical_frequency",
                    "method_name": "Baseline A: Historical Frequency",
                    "description": "Calculates the empirical occurrence ratio of each curriculum topic across all observed prior examination sessions.",
                    "predictions": ranked_a,
                },
                "baseline_b": {
                    "method_id": "recency_weighted_frequency",
                    "method_name": "Baseline B: Recency-Weighted Frequency",
                    "description": "Applies exponential decay (lambda=0.75) to historical appearances, weighting recent exam sessions higher to capture temporal trends.",
                    "predictions": ranked_b,
                },
                "baseline_c": {
                    "method_id": "regularized_statistical_model",
                    "method_name": "Baseline C: Regularized Statistical Model",
                    "description": "Fits an L2-regularized linear trend regression over chronological session appearances to capture emerging topics while penalizing noise.",
                    "predictions": ranked_c,
                },
            },
            "chronological_evaluation": {
                "protocol": "walk_forward_chronological_split",
                "total_sessions": len(sessions),
                "eligible_evaluation_splits": eval_res.get("number_of_splits", len(splits_detail)),
                "splits_evaluated": splits_detail,
                "comparative_metrics": {
                    "historical_frequency": models_eval.get("historical_frequency", {}).get("summary", {}),
                    "recency_weighted_frequency": models_eval.get("recency_weighted_frequency", {}).get("summary", {}),
                    "regularized_statistical_model": models_eval.get("regularized_statistical_model", {}).get("summary", {}),
                },
                "split_level_results": {
                    "historical_frequency": models_eval.get("historical_frequency", {}).get("splits", []),
                    "recency_weighted_frequency": models_eval.get("recency_weighted_frequency", {}).get("splits", []),
                    "regularized_statistical_model": models_eval.get("regularized_statistical_model", {}).get("splits", []),
                },
                "sample_size_limitations": [
                    f"Evaluated across {len(splits_detail)} chronological walk-forward splits on synthetic sequence.",
                    "No future examination session was included in feature extraction or training of its corresponding fold.",
                    "Small sample size induces variance in metric estimates; results demonstrate algorithmic properties rather than empirical certainty.",
                ],
            },
        }
