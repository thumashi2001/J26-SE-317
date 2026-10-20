"""
AdaptiveLearnSE Component 3 — Research Experiments Common Helpers
Loads the canonical held-out test split (N=150) without question leakage.
"""

import os
import json
import pandas as pd
from typing import Optional

def load_experiment_test_data(base_dir: str, sample_size: Optional[int] = 150) -> pd.DataFrame:
    synthetic_dir = os.path.join(base_dir, "datasets", "synthetic")
    ca_test_path = os.path.join(synthetic_dir, "controlled_answers_test.csv")
    final_ca_path = os.path.join(synthetic_dir, "02_FINAL_controlled_answers.csv")
    qb_test_path = os.path.join(synthetic_dir, "question_bank_test.csv")

    if os.path.exists(ca_test_path):
        df = pd.read_csv(ca_test_path)
    elif os.path.exists(final_ca_path):
        df_all = pd.read_csv(final_ca_path)
        df = df_all[df_all["split"] == "test"].copy()
    else:
        raise FileNotFoundError(f"Controlled answers test split not found in {synthetic_dir}")

    # Enrich with reference_answer, rubric, and expected_concepts from question bank
    if os.path.exists(qb_test_path):
        df_qb = pd.read_csv(qb_test_path)
        ref_map = dict(zip(df_qb["question_id"], df_qb["reference_answer"].fillna("")))
        rubric_map = dict(zip(df_qb["question_id"], df_qb["rubric"].fillna("")))
        exp_concepts_map = dict(zip(df_qb["question_id"], df_qb["expected_concepts"].fillna("[]")))

        if "reference_answer" not in df.columns:
            df["reference_answer"] = df["question_id"].map(ref_map).fillna("")
        else:
            df["reference_answer"] = df["reference_answer"].fillna(df["question_id"].map(ref_map)).fillna("")

        if "rubric" not in df.columns:
            df["rubric"] = df["question_id"].map(rubric_map).fillna("")
        else:
            df["rubric"] = df["rubric"].fillna(df["question_id"].map(rubric_map)).fillna("")

        if "expected_concepts" not in df.columns:
            df["expected_concepts"] = df["question_id"].map(exp_concepts_map).fillna("[]")
        else:
            df["expected_concepts"] = df["expected_concepts"].fillna(df["question_id"].map(exp_concepts_map)).fillna("[]")

    if sample_size and sample_size < len(df):
        df = df.iloc[:sample_size].copy()

    return df
