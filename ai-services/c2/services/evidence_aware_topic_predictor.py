"""M20 - Evidence-Aware Exam Topic Prediction Subsystem.

Combines verified historical examination evidence, multi-state readiness gates,
chronological feature extraction, modular prediction baselines, and walk-forward
evaluation safeguards. Strictly prevents fabrication of future-exam probabilities
when authentic lecturer-verified ground truth is absent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.chronological_prediction_evaluator import ChronologicalPredictionEvaluator
from services.exam_pattern_analyzer import ExamPatternAnalyzer
from services.prediction_readiness_service import PredictionReadinessAssessor
from services.topic_prediction_engine import TopicPredictionEngine


class EvidenceAwareTopicPredictor:
    """Orchestrates topic prediction readiness, historical analysis, baselines, and evaluation."""

    def __init__(
        self,
        analyzer: Optional[ExamPatternAnalyzer] = None,
        readiness_assessor: Optional[PredictionReadinessAssessor] = None,
        prediction_engine: Optional[TopicPredictionEngine] = None,
        evaluator: Optional[ChronologicalPredictionEvaluator] = None,
    ):
        self.analyzer = analyzer if analyzer is not None else ExamPatternAnalyzer()
        self.readiness_assessor = readiness_assessor or PredictionReadinessAssessor()
        self.prediction_engine = prediction_engine or TopicPredictionEngine(
            readiness_assessor=self.readiness_assessor
        )
        self.evaluator = evaluator or ChronologicalPredictionEvaluator(
            readiness_assessor=self.readiness_assessor,
            prediction_engine=self.prediction_engine,
        )

    def predict(
        self,
        module_key: str,
        target_period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive evidence-aware topic analysis and prediction report."""
        analysis = self.analyzer.analyze(module_key)

        topics = analysis["topics"]
        verified_count = topics["verified_classified_questions"]
        total_questions = analysis["total_questions"]
        distinct_papers = analysis["distinct_papers"]
        distinct_years = analysis["distinct_years"]

        coverage = (
            round(verified_count / total_questions, 4)
            if total_questions > 0
            else 0.0
        )

        # Historical readiness gate
        ready = analysis["prediction_ready"]
        limitations = list(analysis["limitations"])

        if total_questions > 0 and coverage < 0.8:
            limitations.append(
                "Fewer than 80% of authentic questions have verified topic labels; "
                "observed topic frequencies may be unrepresentative."
            )

        ranking_available = (
            ready
            and coverage >= 0.8
            and verified_count > 0
        )

        topic_statistics = []
        for item in topics["statistics"]:
            count = item["question_count"]
            topic_statistics.append({
                "topic_id": item["topic_id"],
                "question_count": count,
                "extracted_marks": item["extracted_marks"],
                "papers_count": item.get("papers_count", 0),
                "paper_coverage": item.get("paper_coverage", 0.0),
                "yearly_occurrences": item.get("yearly_occurrences", {}),
                "share_of_verified_questions": round(
                    count / verified_count, 4
                ) if verified_count else None,
            })

        # Multi-state evidence readiness assessment
        readiness = self.readiness_assessor.assess(module_key, pattern_analysis=analysis)

        if not ranking_available:
            status = "insufficient_evidence"
            study_priorities = []
        else:
            status = "historical_ranking_available"
            study_priorities = [
                {
                    "rank": index,
                    **topic,
                }
                for index, topic in enumerate(
                    topic_statistics,
                    start=1,
                )
            ]

        provisional_count = topics.get("provisional_classified_questions", 0)
        provisional_coverage = (
            round(provisional_count / total_questions, 4)
            if total_questions > 0
            else 0.0
        )

        # Prediction Baselines (Historical Freq, Recency-Weighted, Regularized)
        prediction_models = self.prediction_engine.predict_all_baselines(
            module_key=module_key,
            target_period=target_period,
        )

        # Chronological Walk-Forward Evaluation
        chronological_eval = self.evaluator.evaluate(module_key)

        # Extend limitations from readiness report
        if readiness.get("reasons"):
            limitations.extend(readiness["reasons"])

        # Deduplicate limitations while preserving order
        unique_limitations = list(dict.fromkeys(limitations))

        return {
            "module_key": module_key,
            "analysis_type": "evidence_aware_topic_priorities",
            "status": status,
            "prediction_ready": ranking_available,
            "future_exam_probabilities_available": False,
            "target_examination_period": target_period,
            "prediction_readiness": readiness,
            "historical_evidence": {
                "authentic_questions": total_questions,
                "distinct_papers": distinct_papers,
                "distinct_years": distinct_years,
                "unavailable_years": analysis.get("unavailable_years", []),
                "verified_topic_questions": verified_count,
                "provisional_topic_questions": provisional_count,
                "unverified_topic_questions": topics.get("without_verified_topic", 0),
                "verified_topic_coverage": coverage,
                "provisional_topic_coverage": provisional_coverage,
                "papers_inventory": analysis.get("papers_inventory", []),
                "questions_with_extracted_marks": analysis.get("marks", {}).get(
                    "questions_with_extracted_marks", 0
                ),
                "sum_of_extracted_question_marks": analysis.get("marks", {}).get(
                    "sum_of_extracted_question_marks", 0
                ),
                "ambiguous_marks_questions": analysis.get("marks", {}).get(
                    "ambiguous_marks_questions", 0
                ),
                "excluded_synthetic_questions": analysis.get("excluded", {}).get(
                    "synthetic_questions", 0
                ),
            },
            "topic_statistics": topic_statistics,
            "provisional_topic_summary": topics.get("provisional_statistics", []),
            "study_priorities": study_priorities,
            "prediction_models": prediction_models,
            "chronological_evaluation": chronological_eval,
            "limitations": unique_limitations,
            "disclaimer": (
                "Topic counts describe available authentic historical questions. "
                "Rankings, when available, are study-priority indicators only and do not "
                "predict the next examination or guarantee topic appearance. Future examination "
                "probabilities are strictly disabled until full lecturer verification is complete."
            ),
        }
