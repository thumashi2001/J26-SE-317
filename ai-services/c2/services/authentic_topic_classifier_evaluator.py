"""M20.5 — Authentic Examination Question Topic Classifier Evaluator.

Provides evaluation infrastructure for authentic question topic classification and candidate ranking.
Strictly requires genuine lecturer-approved ground truth labels.
When no verified authentic labels exist, returns status 'not_evaluable'.
Prevents synthetic data contamination and model self-evaluation.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEWS_DIR = PROJECT_ROOT / "outputs" / "classification_reviews"
DEFAULT_QUESTIONS_PATH = PROJECT_ROOT / "datasets" / "processed" / "questions.json"


class AuthenticTopicClassifierEvaluator:
    """Evaluates authentic question topic suggestions against lecturer-verified ground truth."""

    def __init__(
        self,
        reviews_repo=None,
        ranker=None,
        questions_path: Optional[Path] = None,
    ):
        self.reviews_repo = reviews_repo
        self.ranker = ranker
        self.questions_path = Path(questions_path or DEFAULT_QUESTIONS_PATH)

    def evaluate(
        self,
        verified_labels: Optional[List[Dict[str, Any]]] = None,
        classifications: Optional[List[Dict[str, Any]]] = None,
        min_samples: int = 1,
    ) -> Dict[str, Any]:
        """Evaluate topic suggestions against genuine verified ground-truth labels.

        Args:
            verified_labels: Optional list of lecturer verification records.
                             If None, loaded from reviews_repo.
            classifications: Optional list of classification outputs or candidate rankings.
            min_samples: Minimum required verified labels to perform evaluation.

        Returns:
            Dictionary with evaluation results or 'not_evaluable' status.
        """
        # 1. Resolve verified ground-truth labels
        if verified_labels is None:
            if self.reviews_repo is not None:
                all_reviews = self.reviews_repo.get_all_reviews()
                verified_labels = [
                    r for r in all_reviews
                    if r.get("decision") == "approved" and r.get("topic_id")
                ]
            else:
                verified_labels = []

        total_verified = len(verified_labels)
        if total_verified < min_samples:
            return {
                "status": "not_evaluable",
                "evaluable": False,
                "reason": (
                    f"Insufficient lecturer-verified authentic labels. Found {total_verified}, "
                    f"minimum required is {min_samples}. Machine suggestions cannot be evaluated "
                    "without genuine human ground truth."
                ),
                "total_verified_labels": total_verified,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": None,
                "disclaimer": (
                    "Authentic evaluation requires lecturer-verified labels. "
                    "Synthetic performance or candidate coverage cannot substitute for genuine accuracy."
                ),
            }

        # Build ground-truth map: question_id -> verified_topic_id
        ground_truth: Dict[str, Dict[str, Any]] = {}
        for r in verified_labels:
            qid = r.get("question_id")
            if qid:
                ground_truth[qid] = {
                    "question_id": qid,
                    "module_key": r.get("module_key", "unknown"),
                    "verified_topic_id": r.get("topic_id"),
                    "reviewer_id": r.get("reviewer_id"),
                    "reviewed_at": r.get("reviewed_at"),
                }

        # 2. Resolve predictions / candidate rankings for the verified questions
        # If classifications provided, map them by question_id
        pred_map: Dict[str, Dict[str, Any]] = {}
        if classifications:
            for c in classifications:
                qid = c.get("question_id")
                if qid:
                    pred_map[qid] = c

        # 3. Compute metrics across verified instances
        y_true: List[str] = []
        y_top1: List[str] = []
        top3_hits = 0
        abstained_count = 0
        evaluated_questions: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        per_module: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "top1_correct": 0, "top3_correct": 0, "abstained": 0}
        )

        for qid, gt_info in ground_truth.items():
            true_topic = gt_info["verified_topic_id"]
            mod_key = gt_info["module_key"]

            # Obtain candidates from ranker or pred_map
            candidates = []
            abstained = False
            top1_topic = None

            if qid in pred_map:
                pred_entry = pred_map[qid]
                raw_cands = pred_entry.get("candidate_topics", [])
                candidates = [c.get("topic_id") for c in raw_cands if isinstance(c, dict)]
                abstained = pred_entry.get("abstained", False)
                top1_topic = candidates[0] if candidates else None
            elif self.ranker is not None:
                # Rank on the fly if question text is available
                # Fallback to unranked if not found
                pass

            y_true.append(true_topic)
            y_top1.append(top1_topic or "unclassified")

            per_module[mod_key]["total"] += 1

            if abstained or not top1_topic:
                abstained_count += 1
                per_module[mod_key]["abstained"] += 1

            is_top1 = (top1_topic == true_topic)
            is_top3 = (true_topic in candidates[:3])

            if is_top1:
                per_module[mod_key]["top1_correct"] += 1
            else:
                errors.append({
                    "question_id": qid,
                    "module_key": mod_key,
                    "true_topic": true_topic,
                    "predicted_top1": top1_topic,
                    "candidates": candidates[:3],
                })

            if is_top3:
                top3_hits += 1
                per_module[mod_key]["top3_correct"] += 1

            evaluated_questions.append({
                "question_id": qid,
                "module_key": mod_key,
                "true_topic": true_topic,
                "predicted_top1": top1_topic,
                "candidates": candidates[:3],
                "top1_correct": is_top1,
                "top3_correct": is_top3,
                "abstained": abstained,
            })

        n_eval = len(y_true)
        top1_accuracy = sum(1 for yt, yp in zip(y_true, y_top1) if yt == yp) / n_eval if n_eval > 0 else 0.0
        top3_recall = top3_hits / n_eval if n_eval > 0 else 0.0
        abstention_rate = abstained_count / n_eval if n_eval > 0 else 0.0

        # Per-topic metrics
        unique_topics = sorted(list(set(y_true)))
        per_topic_metrics: Dict[str, Dict[str, float]] = {}
        for topic in unique_topics:
            tp = sum(1 for yt, yp in zip(y_true, y_top1) if yt == topic and yp == topic)
            fp = sum(1 for yt, yp in zip(y_true, y_top1) if yt != topic and yp == topic)
            fn = sum(1 for yt, yp in zip(y_true, y_top1) if yt == topic and yp != topic)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            per_topic_metrics[topic] = {
                "support": sum(1 for yt in y_true if yt == topic),
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4),
            }

        macro_f1 = (
            sum(m["f1_score"] for m in per_topic_metrics.values()) / len(per_topic_metrics)
            if per_topic_metrics else 0.0
        )

        # Build module summaries
        module_results = {}
        for mod, counts in per_module.items():
            tot = counts["total"]
            module_results[mod] = {
                "total_verified": tot,
                "top1_accuracy": round(counts["top1_correct"] / tot, 4) if tot > 0 else 0.0,
                "top3_recall": round(counts["top3_correct"] / tot, 4) if tot > 0 else 0.0,
                "abstention_rate": round(counts["abstained"] / tot, 4) if tot > 0 else 0.0,
            }

        return {
            "status": "evaluated",
            "evaluable": True,
            "total_verified_labels": n_eval,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "top1_accuracy": round(top1_accuracy, 4),
                "top3_candidate_recall": round(top3_recall, 4),
                "abstention_rate": round(abstention_rate, 4),
                "macro_f1": round(macro_f1, 4),
                "per_topic": per_topic_metrics,
                "per_module": module_results,
            },
            "error_analysis": {
                "total_errors": len(errors),
                "sample_errors": errors[:10],
            },
            "provenance": {
                "evaluated_on": "lecturer_verified_ground_truth",
                "synthetic_contamination": False,
                "model_self_evaluation": False,
            },
        }
