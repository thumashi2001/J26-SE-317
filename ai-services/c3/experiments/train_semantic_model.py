"""
AdaptiveLearnSE Component 3 — Trainable Semantic Regression Model (Proof of Concept)
Implements a supervised machine-learning model with learnable parameters to satisfy PP1 trainability.

Training split: ai-services/c3/datasets/synthetic/controlled_answers_train.csv (N=702, 117 unique questions)
Evaluation split: ai-services/c3/datasets/synthetic/controlled_answers_test.csv (N=150, 25 unique questions)
Disjoint question IDs: 0 overlap (zero data leakage)

Target: Percentage score (expected_mark / marks) in [0.0, 1.0]
Output artifact: ai-services/c3/models/c3_scoring_regressor.joblib
"""

import json
import os
import re
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DATASET_DIR = os.path.join(BASE_DIR, "datasets", "synthetic")
MODELS_DIR = os.path.join(BASE_DIR, "models")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "is", "are", "was", "were", "be", "been", "this", "that", "it", "as",
    "from", "which", "into", "can", "will", "should", "does", "not", "have", "has"
}

def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    words = re.findall(r"\b[a-zA-Z0-9_\-\./#+]+\b", text.lower())
    return [w for w in words if w not in STOPWORDS]

def parse_concepts(concept_str: Any) -> list[str]:
    if not isinstance(concept_str, str) or not concept_str.strip():
        return []
    try:
        val = json.loads(concept_str)
        if isinstance(val, list):
            return [str(v).strip().lower() for v in val if v]
    except Exception:
        pass
    parts = concept_str.replace("[", "").replace("]", "").replace('"', '').replace("'", "").split(",")
    return [p.strip().lower() for p in parts if p.strip()]

def extract_dense_features(df: pd.DataFrame, tfidf: TfidfVectorizer, is_train: bool = False) -> np.ndarray:
    answers = df["student_answer"].fillna("").astype(str).tolist()
    questions = df["question_text"].fillna("").astype(str).tolist()

    # TF-IDF cosine similarity between student answer and question
    if is_train:
        tfidf.fit(questions + answers)

    ans_vecs = tfidf.transform(answers)
    q_vecs = tfidf.transform(questions)

    # Pairwise cosine similarity: row-wise dot product of normalized sparse vectors
    tfidf_sim = np.asarray((ans_vecs.multiply(q_vecs)).sum(axis=1)).flatten()

    features = []
    for i, row in df.reset_index(drop=True).iterrows():
        ans_text = str(row.get("student_answer", "") or "")
        q_text = str(row.get("question_text", "") or "")
        expected_concepts = parse_concepts(row.get("expected_concepts", ""))

        ans_tokens = set(tokenize(ans_text))
        q_tokens = set(tokenize(q_text))

        # Jaccard overlap with question
        q_jaccard = len(ans_tokens.intersection(q_tokens)) / max(1, len(ans_tokens.union(q_tokens)))

        # Concept hit ratio
        matched_concepts = 0
        ans_lower = ans_text.lower()
        for c in expected_concepts:
            if c and c in ans_lower:
                matched_concepts += 1
        concept_hit_ratio = matched_concepts / max(1, len(expected_concepts))

        # Length ratios
        word_count = len(ans_tokens)
        q_word_count = len(q_tokens)
        len_ratio = min(5.0, word_count / max(1, q_word_count))
        char_len_norm = min(1.0, len(ans_text) / 1000.0)

        # Sentence count heuristic
        sentences = [s for s in re.split(r"[.!?]+", ans_text) if s.strip()]
        sentence_count_norm = min(1.0, len(sentences) / 10.0)

        # Zero answer flag
        is_empty = 1.0 if not ans_text.strip() else 0.0

        row_feat = [
            float(tfidf_sim[i]),
            float(q_jaccard),
            float(concept_hit_ratio),
            float(matched_concepts),
            float(len(expected_concepts)),
            float(len_ratio),
            float(char_len_norm),
            float(sentence_count_norm),
            float(word_count),
            float(is_empty)
        ]
        features.append(row_feat)

    return np.array(features, dtype=np.float32)

def train_and_evaluate():
    train_path = os.path.join(DATASET_DIR, "controlled_answers_train.csv")
    test_path = os.path.join(DATASET_DIR, "controlled_answers_test.csv")

    print(f"[C3 Trainability] Loading training data from: {train_path}")
    df_train = pd.read_csv(train_path)
    print(f"[C3 Trainability] Loading test data from: {test_path}")
    df_test = pd.read_csv(test_path)

    print(f"Train samples: {len(df_train)} (Questions: {df_train['question_id'].nunique()})")
    print(f"Test samples:  {len(df_test)} (Questions: {df_test['question_id'].nunique()})")

    # Target variable: Percentage score in [0.0, 1.0]
    # For answers where marks == 0 (e.g. IRRELEVANT variants), effective max marks is 10.0
    train_marks = np.where(df_train["marks"].values > 0, df_train["marks"].values, 10.0)
    test_marks = np.where(df_test["marks"].values > 0, df_test["marks"].values, 10.0)

    y_train = np.clip(df_train["expected_mark"].fillna(0.0).values / train_marks, 0.0, 1.0)
    y_test = np.clip(df_test["expected_mark"].fillna(0.0).values / test_marks, 0.0, 1.0)

    # Feature extraction
    tfidf = TfidfVectorizer(max_features=500, stop_words="english")
    X_train = extract_dense_features(df_train, tfidf, is_train=True)
    X_test = extract_dense_features(df_test, tfidf, is_train=False)

    print(f"Feature matrix X_train: {X_train.shape}, X_test: {X_test.shape}")

    # Train Model: Ridge Regressor with learned weights w and bias b
    # Also train Gradient Boosting Regressor for non-linear comparison
    model_ridge = Ridge(alpha=1.0, random_state=42)
    model_ridge.fit(X_train, y_train)

    model_gbr = GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    model_gbr.fit(X_train, y_train)

    # Save best model artifact
    artifact_path = os.path.join(MODELS_DIR, "c3_scoring_regressor.joblib")
    joblib.dump({"ridge": model_ridge, "gbr": model_gbr, "tfidf": tfidf}, artifact_path)
    print(f"[C3 Trainability] Model artifact saved to: {artifact_path}")

    # Predictions
    pred_train_pct = np.clip(model_gbr.predict(X_train), 0.0, 1.0)
    pred_test_pct = np.clip(model_gbr.predict(X_test), 0.0, 1.0)

    # Convert percentage predictions back to absolute marks for standard evaluation
    pred_train_marks = pred_train_pct * train_marks
    pred_test_marks = pred_test_pct * test_marks
    y_train_marks = df_train["expected_mark"].fillna(0.0).values
    y_test_marks = df_test["expected_mark"].fillna(0.0).values

    train_mae = mean_absolute_error(y_train_marks, pred_train_marks)
    train_rmse = np.sqrt(mean_squared_error(y_train_marks, pred_train_marks))
    test_mae = mean_absolute_error(y_test_marks, pred_test_marks)
    test_rmse = np.sqrt(mean_squared_error(y_test_marks, pred_test_marks))

    # Pearson correlation on test split
    if np.std(pred_test_marks) > 1e-6 and np.std(y_test_marks) > 1e-6:
        pearson_r = float(np.corrcoef(pred_test_marks, y_test_marks)[0, 1])
    else:
        pearson_r = 0.0

    # Tolerance agreement on test split (<= 2.0 marks error)
    abs_err = np.abs(pred_test_marks - y_test_marks)
    tol_2m = float(np.mean(abs_err <= 2.0)) * 100.0
    tol_15pct = float(np.mean((abs_err / test_marks) <= 0.15)) * 100.0

    # Irrelevant rejection (where quality is IRRELEVANT)
    irrelevant_mask = (df_test["answer_quality"].str.upper() == "IRRELEVANT").values
    irrelevant_count = int(np.sum(irrelevant_mask))
    irrelevant_pred_max = float(np.max(pred_test_marks[irrelevant_mask])) if irrelevant_count > 0 else 0.0

    # Save raw predictions
    df_test_out = df_test[["question_id", "answer_id", "answer_quality", "marks", "expected_mark"]].copy()
    df_test_out["predicted_mark"] = np.round(pred_test_marks, 2)
    df_test_out["absolute_error"] = np.round(abs_err, 2)
    df_test_out["model_type"] = "GradientBoostingRegressor (Trained)"

    pred_csv_path = os.path.join(RESULTS_DIR, "raw_predictions_trainable_model.csv")
    df_test_out.to_csv(pred_csv_path, index=False)
    print(f"[C3 Trainability] Raw predictions saved to: {pred_csv_path}")

    summary = {
        "model_name": "C3 Supervised Semantic Scoring Regressor",
        "model_type": "GradientBoostingRegressor(n_estimators=100, max_depth=3, lr=0.05)",
        "train_samples": int(len(df_train)),
        "train_questions": int(df_train["question_id"].nunique()),
        "test_samples": int(len(df_test)),
        "test_questions": int(df_test["question_id"].nunique()),
        "train_mae": round(float(train_mae), 3),
        "train_rmse": round(float(train_rmse), 3),
        "test_mae": round(float(test_mae), 3),
        "test_rmse": round(float(test_rmse), 3),
        "test_pearson_r": round(float(pearson_r), 3),
        "tolerance_le_2_marks_pct": round(tol_2m, 1),
        "tolerance_le_15_pct_pct": round(tol_15pct, 1),
        "irrelevant_samples": irrelevant_count,
        "artifact_path": artifact_path
    }

    summary_json_path = os.path.join(RESULTS_DIR, "trainable_model_summary.json")
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*70)
    print("       C3 TRAINABLE MODEL PROOF OF CONCEPT — EVALUATION RESULTS")
    print("="*70)
    print(f"Train MAE:                 {train_mae:.3f} marks")
    print(f"Train RMSE:                {train_rmse:.3f} marks")
    print(f"Held-Out Test MAE:         {test_mae:.3f} marks")
    print(f"Held-Out Test RMSE:        {test_rmse:.3f} marks")
    print(f"Held-Out Pearson r:        {pearson_r:.3f}")
    print(f"Tolerance (<= 2.0 marks):  {tol_2m:.1f}%")
    print(f"Tolerance (<= 15% grade):  {tol_15pct:.1f}%")
    print("="*70)
    return summary

if __name__ == "__main__":
    train_and_evaluate()
