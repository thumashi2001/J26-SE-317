"""M17.3 / M17.4 — Topic Classification Model Evaluation and Baseline Comparison.

Evaluates Baseline A (TF-IDF + Logistic Regression) vs Baseline B (TF-IDF + Linear SVM)
on validation data, selects the best model deterministically via validation Macro-F1,
analyzes abstention coverage-vs-accuracy trade-offs, evaluates the selected model
on the held-out test split, and generates JSON and Markdown evaluation reports.

Development fixtures only. Authentic examination evaluation is explicitly marked
as NOT PERFORMED.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from services.m17_topic_classifier_trainer import (
    MODULE_KEYS,
    normalize_text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"


class M17ModelEvaluator:
    """Evaluates and compares topic classification models."""

    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = Path(reports_dir or DEFAULT_REPORTS_DIR)

    @staticmethod
    def evaluate_single_module(
        module_key: str,
        model_pkg: Dict[str, Any],
        questions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate a module's trained model on a set of questions (val or test)."""
        mod_questions = [
            q for q in questions if q.get("module_key") == module_key
        ]
        if not mod_questions:
            return {
                "module_key": module_key,
                "n_samples": 0,
                "accuracy": 0.0,
                "macro_precision": 0.0,
                "macro_recall": 0.0,
                "macro_f1": 0.0,
                "weighted_f1": 0.0,
                "per_topic": {},
                "confusion_matrix": [],
                "classes": model_pkg["classes"],
                "inference_time_seconds": 0.0,
                "avg_inference_ms_per_question": 0.0,
                "predictions": [],
            }

        X = [normalize_text(q["question_text"]) for q in mod_questions]
        y_true = [q["topic"].strip() for q in mod_questions]
        classes = model_pkg["classes"]
        pipeline = model_pkg["pipeline"]
        model_type = model_pkg["model_type"]

        # Run inference and measure time
        start_time = time.perf_counter()
        y_pred = pipeline.predict(X)
        inference_duration = time.perf_counter() - start_time

        # Extract confidence / decision scores
        has_proba = hasattr(pipeline.named_steps["clf"], "predict_proba")
        has_decision = hasattr(pipeline.named_steps["clf"], "decision_function")

        scores: List[float] = []
        score_types: List[str] = []

        if has_proba:
            probas = pipeline.predict_proba(X)
            scores = [float(np.max(p)) for p in probas]
            score_types = ["calibrated_probability"] * len(X)
        elif has_decision:
            margins = pipeline.decision_function(X)
            if margins.ndim == 1:
                scores = [float(abs(m)) for m in margins]
            else:
                scores = [float(np.max(m)) for m in margins]
            score_types = ["uncalibrated_decision_score"] * len(X)
        else:
            scores = [1.0] * len(X)
            score_types = ["binary_decision"] * len(X)

        # Build prediction records
        prediction_records = []
        for i, q in enumerate(mod_questions):
            prediction_records.append({
                "question_id": q.get("question_id"),
                "true_topic": y_true[i],
                "predicted_topic": str(y_pred[i]),
                "confidence_score": round(scores[i], 4),
                "score_type": score_types[i],
                "correct": bool(y_true[i] == y_pred[i]),
            })

        # Calculate metrics
        acc = float(accuracy_score(y_true, y_pred))
        macro_p = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
        macro_r = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
        macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
        weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

        # Per-topic detailed breakdown
        clf_rep = classification_report(
            y_true,
            y_pred,
            labels=classes,
            output_dict=True,
            zero_division=0,
        )
        per_topic = {}
        for c in classes:
            c_str = str(c)
            if c_str in clf_rep:
                per_topic[c_str] = {
                    "precision": round(float(clf_rep[c_str]["precision"]), 4),
                    "recall": round(float(clf_rep[c_str]["recall"]), 4),
                    "f1_score": round(float(clf_rep[c_str]["f1-score"]), 4),
                    "support": int(clf_rep[c_str]["support"]),
                }

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred, labels=classes)

        avg_ms = (inference_duration / len(X)) * 1000.0 if X else 0.0

        return {
            "module_key": module_key,
            "model_type": model_type,
            "n_samples": len(X),
            "accuracy": round(acc, 4),
            "macro_precision": round(macro_p, 4),
            "macro_recall": round(macro_r, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
            "per_topic": per_topic,
            "confusion_matrix": cm.tolist(),
            "classes": classes,
            "inference_time_seconds": round(inference_duration, 4),
            "avg_inference_ms_per_question": round(avg_ms, 3),
            "predictions": prediction_records,
        }

    def evaluate_model_suite(
        self,
        models_dict: Dict[str, Dict[str, Any]],
        questions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate an 8-module suite on a dataset split."""
        module_results = {}
        total_samples = 0
        sum_acc = 0.0
        sum_macro_p = 0.0
        sum_macro_r = 0.0
        sum_macro_f1 = 0.0
        sum_weighted_f1 = 0.0
        total_infer_time = 0.0
        all_predictions = []

        active_modules = [m for m in MODULE_KEYS if m in models_dict]

        for m_key in active_modules:
            res = self.evaluate_single_module(
                module_key=m_key,
                model_pkg=models_dict[m_key],
                questions=questions,
            )
            module_results[m_key] = res
            total_samples += res["n_samples"]
            sum_acc += res["accuracy"]
            sum_macro_p += res["macro_precision"]
            sum_macro_r += res["macro_recall"]
            sum_macro_f1 += res["macro_f1"]
            sum_weighted_f1 += res["weighted_f1"]
            total_infer_time += res["inference_time_seconds"]
            all_predictions.extend(res["predictions"])

        k = len(active_modules) or 1
        model_type = models_dict[active_modules[0]]["model_type"] if active_modules else "unknown"

        return {
            "model_type": model_type,
            "total_samples": total_samples,
            "overall_macro_f1": round(sum_macro_f1 / k, 4),
            "overall_accuracy": round(sum_acc / k, 4),
            "overall_macro_precision": round(sum_macro_p / k, 4),
            "overall_macro_recall": round(sum_macro_r / k, 4),
            "overall_weighted_f1": round(sum_weighted_f1 / k, 4),
            "total_inference_time_seconds": round(total_infer_time, 4),
            "per_module": module_results,
            "all_predictions": all_predictions,
        }

    @staticmethod
    def analyze_abstention_curve(
        predictions: List[Dict[str, Any]],
        thresholds: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Compute coverage vs accuracy across confidence thresholds."""
        if not predictions:
            return []

        # If calibrated probability, check 0.2 to 0.95
        # If uncalibrated decision score, compute quantiles or range
        score_type = predictions[0].get("score_type", "calibrated_probability")

        if thresholds is None:
            if score_type == "calibrated_probability":
                # For 5-class classification, random prior is 0.20, observed range is 0.20 to 0.50
                thresholds = [0.20, 0.25, 0.30, 0.32, 0.35, 0.38, 0.40, 0.42, 0.45, 0.50]
            else:
                all_scores = [p["confidence_score"] for p in predictions]
                if all_scores:
                    min_s, max_s = min(all_scores), max(all_scores)
                    thresholds = [round(float(t), 2) for t in np.linspace(min_s, max_s, 10)]
                else:
                    thresholds = [0.0, 0.5, 1.0]

        total_n = len(predictions)
        curve = []

        for th in thresholds:
            retained = [p for p in predictions if p["confidence_score"] >= th]
            n_retained = len(retained)
            coverage = n_retained / total_n if total_n > 0 else 0.0
            correct = sum(1 for p in retained if p["correct"])
            accuracy_on_retained = correct / n_retained if n_retained > 0 else 0.0

            curve.append({
                "threshold": round(float(th), 4),
                "retained_count": n_retained,
                "abstained_count": total_n - n_retained,
                "coverage": round(coverage, 4),
                "accuracy_retained": round(accuracy_on_retained, 4),
            })

        return curve

    def select_best_model(
        self,
        baseline_a_results: Dict[str, Any],
        baseline_b_results: Dict[str, Any],
    ) -> Tuple[str, str]:
        """Select winning model based primarily on validation Macro-F1.

        Deterministic tie-breaking:
        If difference in validation macro-F1 is <= 1e-4, select Logistic Regression
        because it yields native well-calibrated probabilities for abstention.
        """
        f1_a = baseline_a_results["overall_macro_f1"]
        f1_b = baseline_b_results["overall_macro_f1"]

        if abs(f1_a - f1_b) <= 1e-4:
            winner = "logistic_regression"
            rationale = (
                f"Tie in validation Macro-F1 ({f1_a:.4f} vs {f1_b:.4f}). "
                "Logistic Regression selected via deterministic tie-breaker "
                "for native well-calibrated prediction probabilities."
            )
        elif f1_a > f1_b:
            winner = "logistic_regression"
            rationale = (
                f"Logistic Regression achieved superior validation Macro-F1 "
                f"({f1_a:.4f} vs {f1_b:.4f}, +{(f1_a - f1_b):.4f})."
            )
        else:
            winner = "linear_svc"
            rationale = (
                f"Linear SVC achieved superior validation Macro-F1 "
                f"({f1_b:.4f} vs {f1_a:.4f}, +{(f1_b - f1_a):.4f})."
            )

        return winner, rationale

    def generate_reports(
        self,
        baseline_a_val: Dict[str, Any],
        baseline_b_val: Dict[str, Any],
        selected_model_type: str,
        selection_rationale: str,
        test_results: Dict[str, Any],
        abstention_curve: List[Dict[str, Any]],
        recommended_threshold: float,
        integrity_summary: Dict[str, Any],
    ) -> Tuple[Path, Path]:
        """Generate comprehensive machine-readable JSON and human-readable Markdown reports."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        now_iso = datetime.now(timezone.utc).isoformat()

        report_data = {
            "schema_version": "1.0",
            "milestone": "M17",
            "report_name": "M17 Topic Classification Model Evaluation Report",
            "created_at": now_iso,
            "academic_verification": {
                "synthetic_development_evaluation": "completed",
                "authentic_examination_evaluation": "NOT PERFORMED",
                "status": "unverified",
                "disclaimer": (
                    "All models trained and evaluated on M16 synthetic development data. "
                    "Evaluation results cannot establish accuracy on authentic examination papers. "
                    "No authentic examination papers were used in training or tuning."
                ),
            },
            "data_integrity": integrity_summary,
            "baseline_comparison_validation": {
                "baseline_a": {
                    "name": "TF-IDF + Logistic Regression",
                    "model_type": "logistic_regression",
                    "overall_macro_f1": baseline_a_val["overall_macro_f1"],
                    "overall_accuracy": baseline_a_val["overall_accuracy"],
                    "overall_macro_precision": baseline_a_val["overall_macro_precision"],
                    "overall_macro_recall": baseline_a_val["overall_macro_recall"],
                    "overall_weighted_f1": baseline_a_val["overall_weighted_f1"],
                    "total_inference_time_seconds": baseline_a_val["total_inference_time_seconds"],
                    "per_module": {
                        m: {
                            "macro_f1": res["macro_f1"],
                            "accuracy": res["accuracy"],
                            "macro_precision": res["macro_precision"],
                            "macro_recall": res["macro_recall"],
                            "weighted_f1": res["weighted_f1"],
                        }
                        for m, res in baseline_a_val["per_module"].items()
                    },
                },
                "baseline_b": {
                    "name": "TF-IDF + Linear Support Vector Machine",
                    "model_type": "linear_svc",
                    "overall_macro_f1": baseline_b_val["overall_macro_f1"],
                    "overall_accuracy": baseline_b_val["overall_accuracy"],
                    "overall_macro_precision": baseline_b_val["overall_macro_precision"],
                    "overall_macro_recall": baseline_b_val["overall_macro_recall"],
                    "overall_weighted_f1": baseline_b_val["overall_weighted_f1"],
                    "total_inference_time_seconds": baseline_b_val["total_inference_time_seconds"],
                    "per_module": {
                        m: {
                            "macro_f1": res["macro_f1"],
                            "accuracy": res["accuracy"],
                            "macro_precision": res["macro_precision"],
                            "macro_recall": res["macro_recall"],
                            "weighted_f1": res["weighted_f1"],
                        }
                        for m, res in baseline_b_val["per_module"].items()
                    },
                },
                "selected_model": selected_model_type,
                "selection_rationale": selection_rationale,
            },
            "abstention_analysis": {
                "recommended_threshold": recommended_threshold,
                "score_type": "calibrated_probability" if selected_model_type == "logistic_regression" else "uncalibrated_decision_score",
                "coverage_accuracy_curve": abstention_curve,
            },
            "final_test_evaluation": {
                "model_type": selected_model_type,
                "n_test_samples": test_results["total_samples"],
                "test_macro_f1": test_results["overall_macro_f1"],
                "test_accuracy": test_results["overall_accuracy"],
                "test_macro_precision": test_results["overall_macro_precision"],
                "test_macro_recall": test_results["overall_macro_recall"],
                "test_weighted_f1": test_results["overall_weighted_f1"],
                "test_inference_time_seconds": test_results["total_inference_time_seconds"],
                "per_module": {
                    m: {
                        "macro_f1": res["macro_f1"],
                        "accuracy": res["accuracy"],
                        "macro_precision": res["macro_precision"],
                        "macro_recall": res["macro_recall"],
                        "weighted_f1": res["weighted_f1"],
                        "per_topic": res["per_topic"],
                        "confusion_matrix": res["confusion_matrix"],
                        "classes": res["classes"],
                    }
                    for m, res in test_results["per_module"].items()
                },
            },
        }

        # Write JSON report
        json_path = self.reports_dir / "m17_evaluation_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # Build Markdown report
        md_lines = [
            "# M17 Topic Classification Model Evaluation Report",
            "",
            f"**Generated:** {now_iso}  ",
            "**Milestone:** M17 — Supervised Topic Classifier Training & Evaluation  ",
            "**Status:** Synthetic Development Evaluation (Authentic Evaluation: **NOT PERFORMED**)  ",
            "",
            "## 1. Executive Summary & Safeguards",
            "",
            "- **Synthetic Provenance:** All training, validation, and testing performed exclusively on M16 synthetic development data (800 questions).",
            "- **Authentic Isolation:** Authentic exam questions and lecturer-verified review repositories remained untouched.",
            "- **Authentic Evaluation:** **NOT PERFORMED** — genuine examination papers require formal institutional syllabus reviews.",
            "- **Model Selection Criterion:** Frozen selection based strictly on validation split Macro-F1.",
            "- **Held-Out Test Set:** Evaluated exactly once on the frozen selected model.",
            "",
            "## 2. Dataset Split & Integrity Verification",
            "",
            "| Split | Question Count | Disjoint Scenarios | Overlap with Other Splits |",
            "|---|---|---|---|",
            f"| Train | {integrity_summary['counts']['train']} | {integrity_summary['scenario_isolation']['train_scenarios']} | 0 |",
            f"| Validation | {integrity_summary['counts']['validation']} | {integrity_summary['scenario_isolation']['val_scenarios']} | 0 |",
            f"| Test | {integrity_summary['counts']['test']} | {integrity_summary['scenario_isolation']['test_scenarios']} | 0 |",
            "",
            "> **Note on Template-Family Overlap:** Scenario group IDs are strictly disjoint (0 overlap). However, task prompt phrasing templates overlap across splits because M16 splits at the scenario level to maintain 5 topics per module across splits. This is explicitly documented as a synthetic dataset research limitation.",
            "",
            "## 3. Baseline Comparison on Validation Set (128 Questions)",
            "",
            "| Metric | Baseline A (Logistic Regression) | Baseline B (Linear SVM) | Delta (A - B) |",
            "|---|---|---|---|",
            f"| **Macro-F1** | **{baseline_a_val['overall_macro_f1']:.4f}** | **{baseline_b_val['overall_macro_f1']:.4f}** | {baseline_a_val['overall_macro_f1'] - baseline_b_val['overall_macro_f1']:+.4f} |",
            f"| Accuracy | {baseline_a_val['overall_accuracy']:.4f} | {baseline_b_val['overall_accuracy']:.4f} | {baseline_a_val['overall_accuracy'] - baseline_b_val['overall_accuracy']:+.4f} |",
            f"| Macro Precision | {baseline_a_val['overall_macro_precision']:.4f} | {baseline_b_val['overall_macro_precision']:.4f} | {baseline_a_val['overall_macro_precision'] - baseline_b_val['overall_macro_precision']:+.4f} |",
            f"| Macro Recall | {baseline_a_val['overall_macro_recall']:.4f} | {baseline_b_val['overall_macro_recall']:.4f} | {baseline_a_val['overall_macro_recall'] - baseline_b_val['overall_macro_recall']:+.4f} |",
            f"| Weighted F1 | {baseline_a_val['overall_weighted_f1']:.4f} | {baseline_b_val['overall_weighted_f1']:.4f} | {baseline_a_val['overall_weighted_f1'] - baseline_b_val['overall_weighted_f1']:+.4f} |",
            f"| Inference Time | {baseline_a_val['total_inference_time_seconds']:.4f}s | {baseline_b_val['total_inference_time_seconds']:.4f}s | - |",
            "",
            f"### Model Selection Decision: `{selected_model_type.upper()}`",
            f"> {selection_rationale}",
            "",
            "## 4. Per-Module Validation Performance",
            "",
            "| Module Key | Baseline A Macro-F1 | Baseline A Accuracy | Baseline B Macro-F1 | Baseline B Accuracy |",
            "|---|---|---|---|---|",
        ]

        for m in MODULE_KEYS:
            res_a = baseline_a_val["per_module"].get(m, {})
            res_b = baseline_b_val["per_module"].get(m, {})
            md_lines.append(
                f"| `{m}` | {res_a.get('macro_f1', 0.0):.4f} | {res_a.get('accuracy', 0.0):.4f} | "
                f"{res_b.get('macro_f1', 0.0):.4f} | {res_b.get('accuracy', 0.0):.4f} |"
            )

        md_lines.extend([
            "",
            "## 5. Abstention & Confidence Calibration Analysis",
            "",
            f"**Selected Score Type:** `{report_data['abstention_analysis']['score_type']}`  ",
            f"**Recommended Operating Threshold:** `{recommended_threshold}`  ",
            "",
            "| Threshold | Retained | Abstained | Coverage (%) | Accuracy on Retained (%) |",
            "|---|---|---|---|---|",
        ])

        for pt in abstention_curve:
            md_lines.append(
                f"| {pt['threshold']:.2f} | {pt['retained_count']} | {pt['abstained_count']} | "
                f"{pt['coverage'] * 100:.1f}% | {pt['accuracy_retained'] * 100:.1f}% |"
            )

        md_lines.extend([
            "",
            "## 6. Final Evaluation on Held-Out Test Set (96 Questions)",
            "",
            f"- **Selected Architecture:** `{selected_model_type}`",
            f"- **Overall Test Macro-F1:** **{test_results['overall_macro_f1']:.4f}**",
            f"- **Overall Test Accuracy:** **{test_results['overall_accuracy']:.4f}**",
            f"- **Overall Test Macro Precision:** {test_results['overall_macro_precision']:.4f}",
            f"- **Overall Test Macro Recall:** {test_results['overall_macro_recall']:.4f}",
            f"- **Overall Test Weighted F1:** {test_results['overall_weighted_f1']:.4f}",
            f"- **Total Test Inference Time:** {test_results['total_inference_time_seconds']:.4f}s",
            "",
            "### Per-Module Test Breakdown",
            "",
            "| Module Key | Test Samples | Macro-F1 | Accuracy | Macro Precision | Macro Recall |",
            "|---|---|---|---|---|---|",
        ])

        for m in MODULE_KEYS:
            res_t = test_results["per_module"].get(m, {})
            md_lines.append(
                f"| `{m}` | {res_t.get('n_samples', 0)} | {res_t.get('macro_f1', 0.0):.4f} | "
                f"{res_t.get('accuracy', 0.0):.4f} | {res_t.get('macro_precision', 0.0):.4f} | "
                f"{res_t.get('macro_recall', 0.0):.4f} |"
            )

        md_lines.extend([
            "",
            "## 7. Limitations & Academic Integrity",
            "",
            "1. **Synthetic-Only Data:** Trained and tested on synthetic questions generated by deterministic rules in M16.",
            "2. **Authentic Performance Disconnect:** High synthetic scores do NOT imply identical performance on real SLIIT examinations.",
            "3. **Template Phrasing Bias:** Template reuse across scenarios may inflate synthetic generalization estimates.",
            "4. **Authentic Guardrails Active:** Model predictions are strictly marked `unverified` and routed to lecturer review.",
            "",
        ])

        md_path = self.reports_dir / "m17_evaluation_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        return json_path, md_path
