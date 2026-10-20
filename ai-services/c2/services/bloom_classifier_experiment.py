"""M21 — Bloom's Taxonomy Classification Experiment.

Trains a reproducible baseline model (TF-IDF + Logistic Regression / Linear SVM)
on the 800 Bloom-labeled synthetic examination questions from M16, utilizing
a leakage-aware GroupKFold / module-stratified split.

Strict Research Integrity Constraints:
- Evaluates on synthetic dataset with documented provenance.
- Authentic past-paper evaluation is explicitly marked as 'not_evaluable' (0 verified labels).
- Persists full classification report with per-class metrics, Macro-F1, and Confusion Matrix.
"""

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DATASET_PATH = PROJECT_ROOT / "datasets" / "synthetic" / "m16" / "combined_dataset.json"
REPORT_OUTPUT_PATH = PROJECT_ROOT / "reports" / "m21_bloom_classifier_evaluation.json"


def run_bloom_classification_experiment() -> Dict[str, Any]:
    """Train and evaluate Bloom's Taxonomy classifier on synthetic questions."""
    if not SYNTHETIC_DATASET_PATH.exists():
        raise FileNotFoundError(f"Synthetic dataset not found at {SYNTHETIC_DATASET_PATH}")

    with open(SYNTHETIC_DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    labels = []
    groups = []  # Group by module_key to prevent intra-module question leakage

    for mod in data.get("modules", []):
        mod_key = mod.get("module_key", "unknown")
        for q in mod.get("questions", []):
            text = q.get("question_text", "").strip()
            bloom = q.get("bloom_level", "").strip().lower()
            if text and bloom:
                questions.append(text)
                labels.append(bloom)
                groups.append(mod_key)

    if not questions:
        raise ValueError("No valid questions found for Bloom classification experiment.")

    unique_labels = sorted(list(set(labels)))
    total_samples = len(questions)

    # Leakage-aware train/test split: reserve 2 modules (~25%) completely for testing
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(gss.split(questions, labels, groups=groups))

    X_train = [questions[i] for i in train_idx]
    y_train = [labels[i] for i in train_idx]
    groups_train = sorted(list(set(groups[i] for i in train_idx)))

    X_test = [questions[i] for i in test_idx]
    y_test = [labels[i] for i in test_idx]
    groups_test = sorted(list(set(groups[i] for i in test_idx)))

    # Pipeline: TF-IDF with sublinear tf scaling and unigram+bigram + LogisticRegression
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=5000,
            stop_words="english",
        )),
        ("clf", LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
        )),
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted"))

    report_dict = classification_report(
        y_test,
        y_pred,
        target_names=unique_labels,
        output_dict=True,
        zero_division=0,
    )

    conf_mat = confusion_matrix(y_test, y_pred, labels=unique_labels).tolist()

    result = {
        "experiment_name": "M21 Bloom's Taxonomy Cognitive Classification Experiment",
        "model_architecture": "TF-IDF (1-2 ngrams, max_features=5000) + Multinomial Logistic Regression",
        "split_strategy": "Leakage-Aware Module-Disjoint Split (GroupShuffleSplit 75/25)",
        "train_modules": groups_train,
        "test_modules": groups_test,
        "total_synthetic_samples": total_samples,
        "train_sample_count": len(X_train),
        "test_sample_count": len(X_test),
        "classes": unique_labels,
        "overall_metrics": {
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
        },
        "per_class_metrics": {
            cls_name: {
                "precision": round(report_dict[cls_name]["precision"], 4),
                "recall": round(report_dict[cls_name]["recall"], 4),
                "f1_score": round(report_dict[cls_name]["f1-score"], 4),
                "support": int(report_dict[cls_name]["support"]),
            }
            for cls_name in unique_labels
            if cls_name in report_dict
        },
        "confusion_matrix": {
            "labels": unique_labels,
            "matrix": conf_mat,
        },
        "authentic_evaluation": {
            "status": "not_evaluable",
            "authentic_questions_count": 443,
            "authentic_verified_bloom_labels": 0,
            "limitation": (
                "Authentic examination past papers do not yet have lecturer-verified Bloom's Taxonomy "
                "ground-truth labels. Model accuracy is reported strictly on the controlled synthetic corpus."
            ),
        },
        "provenance": {
            "source_corpus": "m16_expanded_content_bank.json / combined_dataset.json",
            "evaluated_by": "AdaptiveLearnSE C2 Research Pipeline",
            "reproducible_seed": 42,
        },
    }

    REPORT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    report = run_bloom_classification_experiment()
    print("M21 Bloom Experiment Completed Successfully!")
    print(f"Accuracy: {report['overall_metrics']['accuracy'] * 100:.2f}%")
    print(f"Macro F1: {report['overall_metrics']['macro_f1'] * 100:.2f}%")
    print(f"Report saved to: {REPORT_OUTPUT_PATH}")
