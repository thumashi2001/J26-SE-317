"""M17 — Topic Classification Model Training CLI Script.

Trains Baseline A (TF-IDF + Logistic Regression) and Baseline B (TF-IDF + Linear SVM)
on M16 synthetic development data across all 8 Year 3 SE modules.
Selects best model architecture based strictly on validation split Macro-F1.

Usage:
    python -m scripts.m17_train --seed 42
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.m17_topic_classifier_trainer import (
    DEFAULT_DATA_DIR,
    DEFAULT_MODELS_DIR,
    M17TopicClassifierTrainer,
)
from services.m17_model_evaluator import M17ModelEvaluator


def main():
    parser = argparse.ArgumentParser(
        description="M17 Topic Classification Model Training Pipeline",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help="Directory containing M16 training_export splits",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help="Directory to save trained model artifacts",
    )
    parser.add_argument(
        "--c",
        type=float,
        default=1.0,
        help="Regularization strength C for models (default: 1.0)",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("M17: Topic Classification Model Training Pipeline")
    print("=" * 65)
    print(f"Random Seed: {args.seed}")
    print(f"Data Directory: {args.data_dir}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Regularization C: {args.c}")
    print("-" * 65)

    trainer = M17TopicClassifierTrainer(
        data_dir=Path(args.data_dir),
        models_dir=Path(args.output_dir),
    )

    # 1. Load splits
    print("[1/5] Loading M16 synthetic development splits...")
    train_data = trainer.load_split("train")
    val_data = trainer.load_split("validation")
    test_data = trainer.load_split("test")

    print(f"  Loaded Train: {len(train_data['questions'])} questions")
    print(f"  Loaded Validation: {len(val_data['questions'])} questions")
    print(f"  Loaded Test: {len(test_data['questions'])} questions")

    # 2. Validate split integrity & scenario disjointness
    print("\n[2/5] Validating data integrity and partition isolation...")
    integrity = trainer.validate_split_integrity(train_data, val_data, test_data)
    print("  [OK] Question IDs disjoint across all splits")
    print("  [OK] Scenario groups 100% disjoint across all splits")
    if integrity["template_family_risk"]["risk_flagged"]:
        print(
            f"  ! Template-family risk flagged: {integrity['template_family_risk']['train_test_overlap_count']} "
            "templates overlap train/test (documented limitation of synthetic scenario-based splitting)"
        )

    # 3. Train Baseline A: Logistic Regression
    print("\n[3/5] Training Baseline A (TF-IDF + Logistic Regression) on train split...")
    models_a = trainer.train_all_modules(
        questions=train_data["questions"],
        model_type="logistic_regression",
        seed=args.seed,
        C=args.c,
    )
    total_time_a = sum(pkg["training_time_seconds"] for pkg in models_a.values())
    print(f"  [OK] Trained 8 module models in {total_time_a:.3f}s")

    # 4. Train Baseline B: Linear SVM
    print("\n[4/5] Training Baseline B (TF-IDF + Linear Support Vector Machine) on train split...")
    models_b = trainer.train_all_modules(
        questions=train_data["questions"],
        model_type="linear_svc",
        seed=args.seed,
        C=args.c,
    )
    total_time_b = sum(pkg["training_time_seconds"] for pkg in models_b.values())
    print(f"  [OK] Trained 8 module models in {total_time_b:.3f}s")

    # 5. Evaluate on Validation Split & Select Best
    print("\n[5/5] Comparing Baseline A vs B on Validation Split (128 questions)...")
    evaluator = M17ModelEvaluator()
    val_a = evaluator.evaluate_model_suite(models_a, val_data["questions"])
    val_b = evaluator.evaluate_model_suite(models_b, val_data["questions"])

    print("\n" + "=" * 65)
    print("VALIDATION BASELINE COMPARISON RESULTS")
    print("=" * 65)
    print(f"{'Metric':<25} {'Baseline A (LogReg)':<20} {'Baseline B (LinSVC)':<20}")
    print("-" * 65)
    print(f"{'Overall Macro-F1':<25} {val_a['overall_macro_f1']:<20.4f} {val_b['overall_macro_f1']:<20.4f}")
    print(f"{'Overall Accuracy':<25} {val_a['overall_accuracy']:<20.4f} {val_b['overall_accuracy']:<20.4f}")
    print(f"{'Overall Macro Precision':<25} {val_a['overall_macro_precision']:<20.4f} {val_b['overall_macro_precision']:<20.4f}")
    print(f"{'Overall Macro Recall':<25} {val_a['overall_macro_recall']:<20.4f} {val_b['overall_macro_recall']:<20.4f}")
    print(f"{'Overall Weighted F1':<25} {val_a['overall_weighted_f1']:<20.4f} {val_b['overall_weighted_f1']:<20.4f}")
    print(f"{'Inference Latency':<25} {val_a['total_inference_time_seconds'] * 1000:<17.1f}ms {val_b['total_inference_time_seconds'] * 1000:<17.1f}ms")
    print("-" * 65)

    winner, rationale = evaluator.select_best_model(val_a, val_b)
    print(f"WINNING MODEL: {winner.upper()}")
    print(f"Rationale: {rationale}")
    print("-" * 65)

    # Save artifacts
    print("\nPersisting model artifacts to outputs/models/m17...")
    trainer.save_artifacts(
        models_dict=models_a,
        model_type="logistic_regression",
        integrity_summary=integrity,
        is_selected_production_candidate=(winner == "logistic_regression"),
    )
    trainer.save_artifacts(
        models_dict=models_b,
        model_type="linear_svc",
        integrity_summary=integrity,
        is_selected_production_candidate=(winner == "linear_svc"),
    )

    print("[OK] Saved Baseline A artifacts (logistic_regression)")
    print("[OK] Saved Baseline B artifacts (linear_svc)")
    print(f"[OK] Saved candidate production model symlinks/artifacts for '{winner}'")
    print("\nM17 Training Complete. Next step: run `python -m scripts.m17_evaluate`.")


if __name__ == "__main__":
    main()
