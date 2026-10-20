"""
AdaptiveLearnSE Component 3 — Experiment 5: Multi-LLM Comparative Benchmark
Evaluates multiple LLM candidates under equivalent prompt and rubric conditions across held-out test data.
"""

import os
import sys
import json
import time
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.append(BASE_DIR)

from services.llm import get_llm_provider, LLMRequest
from experiments.common import load_experiment_test_data

RESULTS_DIR = os.path.join(BASE_DIR, "experiments", "results")

CANDIDATE_MODELS = [
    {"name": "mock-gpt4o", "label": "Model A (GPT-4o Class)"},
    {"name": "mock-claude-3-5-sonnet", "label": "Model B (Claude 3.5 Sonnet Class)"},
    {"name": "mock-llama-3-8b", "label": "Model C (Llama 3 8B Open Weights Class)"}
]


def run_experiment_5(sample_size: int = 150) -> dict:
    print("=" * 80)
    print("  EXPERIMENT 5: Multi-LLM Comparative Benchmark")
    print(f"  Models: {[m['name'] for m in CANDIDATE_MODELS]} | Dataset: canonical controlled_answers_test.csv")
    print("=" * 80)

    df = load_experiment_test_data(BASE_DIR, sample_size=sample_size)

    provider = get_llm_provider()
    model_comparisons = []
    all_raw_predictions = []

    for model_spec in CANDIDATE_MODELS:
        m_name = model_spec["name"]
        m_label = model_spec["label"]
        print(f"\nEvaluating Model: {m_label} ({m_name})...")

        model_results = []
        start_m = time.perf_counter()

        for idx, row in df.iterrows():
            q_id = str(row["question_id"])
            q_text = str(row["question_text"])
            ans_text = str(row["student_answer"])
            ref_ans = str(row.get("reference_answer", ""))
            gt_mark = float(row.get("expected_mark", row.get("marks", 0.0)))
            max_marks = float(row.get("marks", 10.0))
            rubric_str = str(row.get("rubric", "Criterion 1 (50%): Core concepts; Criterion 2 (50%): Rationale and examples."))

            prompt = f"""
Evaluate the following student answer using this explicit marking rubric.
Question: {q_text}
Reference Answer: {ref_ans}
Maximum Marks: {max_marks}
Rubric Criteria:
{rubric_str}
Student Answer:
\"\"\"{ans_text}\"\"\"

Return valid JSON: {{"total_awarded_mark": float, "overall_feedback": string}}
"""
            req = LLMRequest(prompt=prompt, model=m_name, temperature=0.1, max_tokens=400, response_format="json")
            res = provider.generate(req)

            pred_mark = 0.0
            if res.is_success and res.parsed_json:
                pred_mark = float(res.parsed_json.get("total_awarded_mark", 0.0))
            pred_mark = max(0.0, min(max_marks, pred_mark))

            model_results.append({
                "model": m_name,
                "question_id": q_id,
                "expected_mark": gt_mark,
                "predicted_mark": pred_mark,
                "error": abs(pred_mark - gt_mark),
                "latency_ms": res.latency_ms,
                "cost_usd": res.usage.estimated_cost_usd
            })

        m_df = pd.DataFrame(model_results)
        all_raw_predictions.extend(model_results)

        mae = float(m_df["error"].mean())
        rmse = float(np.sqrt((m_df["error"] ** 2).mean()))
        tol_2 = float((m_df["error"] <= 2.0).mean() * 100.0)
        mean_latency = float(m_df["latency_ms"].mean())

        model_comparisons.append({
            "model_identifier": m_name,
            "model_label": m_label,
            "sample_size": len(m_df),
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "tolerance_within_2_marks_pct": round(tol_2, 2),
            "mean_latency_ms": round(mean_latency, 2),
            "total_runtime_seconds": round(time.perf_counter() - start_m, 2)
        })
        print(f"  -> MAE: {mae:.3f} | RMSE: {rmse:.3f} | Tol (<=2): {tol_2:.1f}% | Latency: {mean_latency:.2f} ms")

    summary = {
        "experiment_id": "EXP-05-MULTI-LLM-COMPARISON",
        "description": "Cross-architecture comparison of LLM candidates under identical rubric prompt constraints",
        "models_evaluated": model_comparisons,
        "output_csv": os.path.join(RESULTS_DIR, "raw_predictions_exp5_multi_llm.csv")
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    pd.DataFrame(all_raw_predictions).to_csv(summary["output_csv"], index=False)
    summary_path = os.path.join(RESULTS_DIR, "exp5_multi_llm_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nMulti-LLM summary saved to: {summary_path}")
    return summary


if __name__ == "__main__":
    run_experiment_5()
