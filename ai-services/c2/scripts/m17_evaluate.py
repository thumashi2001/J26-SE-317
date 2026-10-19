"""M17 — Topic Classification Model Evaluation CLI Script.

Loads trained model artifacts, evaluates Baseline A vs Baseline B on validation data,
computes abstention coverage curves, evaluates the frozen selected model on the held-out
synthetic test set (96 questions), and outputs JSON and Markdown reports.

Usage:
    python -m scripts.m17_evaluate
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib

from services.m17_topic_classifier_trainer import (
    DEFAULT_DATA_DIR,
    DEFAULT_MODELS_DIR,
    MODULE_KEYS,
    M17TopicClassifierTrainer,
)
from services.m17_model_evaluator import (
    DEFAULT_REPORTS_DIR,
    M17ModelEvaluator,
)
from services.m17_topic_prediction_service import M17TopicPredictionService


def load_model_suite(models_dir: Path, model_type: str):
    suite = {}
    for m in MODULE_KEYS:
        path = models_dir / f"{m}_{model_type}.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Model artifact not found: {path}. Run scripts.m17_train first.")
        suite[m] = joblib.load(path)
    return suite


def main():
    parser = argparse.ArgumentParser(
        description="M17 Topic Classification Model Evaluation",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help="Directory containing trained model artifacts",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help="Directory containing dataset splits",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default=str(DEFAULT_REPORTS_DIR),
        help="Directory to save evaluation reports",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.38,
        help="Abstention threshold (default: 0.38)",
    )
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    data_dir = Path(args.data_dir)
    reports_dir = Path(args.reports_dir)

    print("=" * 65)
    print("M17: Topic Classification Model Evaluation")
    print("=" * 65)
    print(f"Models Directory: {models_dir}")
    print(f"Data Directory: {data_dir}")
    print(f"Reports Directory: {reports_dir}")
    print(f"Operating Threshold: {args.threshold}")
    print("-" * 65)

    trainer = M17TopicClassifierTrainer(data_dir=data_dir, models_dir=models_dir)
    evaluator = M17ModelEvaluator(reports_dir=reports_dir)

    # 1. Load splits
    print("[1/4] Loading dataset splits...")
    train_data = trainer.load_split("train")
    val_data = trainer.load_split("validation")
    test_data = trainer.load_split("test")
    integrity = trainer.validate_split_integrity(train_data, val_data, test_data)

    # 2. Load model suites
    print("\n[2/4] Loading trained model artifacts...")
    models_a = load_model_suite(models_dir, "logistic_regression")
    models_b = load_model_suite(models_dir, "linear_svc")

    # 3. Validation evaluation & model selection
    print("\n[3/4] Re-evaluating on Validation Split (128 questions)...")
    val_a = evaluator.evaluate_model_suite(models_a, val_data["questions"])
    val_b = evaluator.evaluate_model_suite(models_b, val_data["questions"])

    winner, rationale = evaluator.select_best_model(val_a, val_b)
    print(f"  Selected Winner: {winner.upper()}")
    print(f"  Rationale: {rationale}")

    selected_suite = models_a if winner == "logistic_regression" else models_b
    winner_val = val_a if winner == "logistic_regression" else val_b

    # Abstention analysis on validation predictions
    abstention_curve = evaluator.analyze_abstention_curve(winner_val["all_predictions"])

    # 4. Final Evaluation on Held-out Test Split
    print(f"\n[4/4] Evaluating Selected Model ({winner}) on Held-Out Test Split (96 questions)...")
    test_results = evaluator.evaluate_model_suite(selected_suite, test_data["questions"])

    print("\n" + "=" * 65)
    print(f"HELD-OUT TEST SET RESULTS ({winner.upper()})")
    print("=" * 65)
    print(f"Total Test Questions: {test_results['total_samples']}")
    print(f"Overall Macro-F1:     {test_results['overall_macro_f1']:.4f}")
    print(f"Overall Accuracy:     {test_results['overall_accuracy']:.4f}")
    print(f"Macro Precision:      {test_results['overall_macro_precision']:.4f}")
    print(f"Macro Recall:         {test_results['overall_macro_recall']:.4f}")
    print(f"Weighted F1:          {test_results['overall_weighted_f1']:.4f}")
    print(f"Inference Latency:    {test_results['total_inference_time_seconds'] * 1000:.1f}ms")
    print("-" * 65)

    print("\nPer-Module Test Breakdown:")
    for m in MODULE_KEYS:
        r = test_results["per_module"].get(m, {})
        print(f"  {m:<45} Macro-F1: {r.get('macro_f1', 0):.4f}  Acc: {r.get('accuracy', 0):.4f}")

    # Generate JSON and Markdown reports
    json_path, md_path = evaluator.generate_reports(
        baseline_a_val=val_a,
        baseline_b_val=val_b,
        selected_model_type=winner,
        selection_rationale=rationale,
        test_results=test_results,
        abstention_curve=abstention_curve,
        recommended_threshold=args.threshold,
        integrity_summary=integrity,
    )

    print(f"\n[OK] Generated JSON report: {json_path}")
    print(f"[OK] Generated Markdown report: {md_path}")

    # Sample predictions demonstration
    print("\n" + "=" * 65)
    print("SAMPLE INFERENCE WITH CONSERVATIVE ABSTENTION")
    print("=" * 65)
    predictor = M17TopicPredictionService(
        models_dir=models_dir,
        default_threshold=args.threshold,
        model_type=winner,
    )

    sample_queries = [
        (
            "database_systems",
            "Scenario: High transaction banking database experiences lock contention.\n"
            "Task: Evaluate pessimistic concurrency control versus two-phase locking protocols.",
        ),
        (
            "software_architecture",
            "Scenario: E-commerce platform needs event-driven decoupling.\n"
            "Task: Contrast publish-subscribe messaging topology with message queue worker architecture.",
        ),
        (
            "application_frameworks",
            "Scenario: Mobile client receives push events.\n"
            "Task: Analyze WebSocket event handling versus long polling middleware.",
        ),
        (
            "database_systems",
            "What is the weather like in Colombo today?",  # Out-of-domain / ambiguous test
        ),
    ]

    for m_key, q_text in sample_queries:
        res = predictor.predict(m_key, q_text)
        print(f"\nModule:     {res['module_key']}")
        print(f"Question:   {q_text[:70]}...")
        print(f"Predicted:  {res['predicted_topic']}")
        print(f"Decision:   {res['decision']} (Abstained: {res['abstained']})")
        print(f"Score:      {res['confidence_score']} ({res['score_type']})")
        print(f"Status:     {res['verification_status']} ({res['academic_verification']})")

    print("\n" + "=" * 65)
    print("Evaluation Complete.")
    print("=" * 65)


if __name__ == "__main__":
    main()
