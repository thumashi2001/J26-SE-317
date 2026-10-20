"""
AdaptiveLearnSE Component 3 — Experiment 4: Shared CCKG GraphRAG Assessment
Evaluates Rubric-Aware LLM assessment augmented with knowledge graph prerequisite chains and concept ontology.
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
from services.cckg.graph_adapter import get_cckg_adapter
from experiments.common import load_experiment_test_data

RESULTS_DIR = os.path.join(BASE_DIR, "experiments", "results")


def run_experiment_4(sample_size: int = 150, model_name: str = "mock-gpt4o") -> dict:
    print("=" * 80)
    print("  EXPERIMENT 4: Shared CCKG GraphRAG Assessment (Ontology & Prerequisite Grounding)")
    print(f"  Model: {model_name} | Dataset: canonical controlled_answers_test.csv")
    print("=" * 80)

    df = load_experiment_test_data(BASE_DIR, sample_size=sample_size)

    provider = get_llm_provider()
    graph_adapter = get_cckg_adapter()
    results = []
    start_total = time.perf_counter()

    for idx, row in df.iterrows():
        q_id = str(row["question_id"])
        q_text = str(row["question_text"])
        ans_text = str(row["student_answer"])
        ref_ans = str(row.get("reference_answer", ""))
        gt_mark = float(row.get("expected_mark", row.get("marks", 0.0)))
        max_marks = float(row.get("marks", 10.0))
        rubric_str = str(row.get("rubric", "Criterion 1 (50%): Core concepts; Criterion 2 (50%): Rationale and examples."))

        # Extract expected concepts from row
        expected_concepts_raw = row.get("expected_concepts", "[]")
        try:
            expected_concepts = json.loads(expected_concepts_raw) if isinstance(expected_concepts_raw, str) else []
        except Exception:
            expected_concepts = []

        # 1. GraphRAG Traversal over CCKG
        graph_rag_info = graph_adapter.retrieve_graphrag_context(q_id, concepts=expected_concepts)
        graph_context = graph_rag_info["graphrag_context_text"]
        citations = graph_rag_info["curriculum_citations"]
        prereqs = graph_rag_info["prerequisite_chain"]

        prompt = f"""
Evaluate the following student answer using the rubric and curriculum knowledge graph evidence.
Check whether the student demonstrates understanding of key prerequisite concepts.

Question: {q_text}
Reference Answer: {ref_ans}
Maximum Marks: {max_marks}

Rubric Criteria:
{rubric_str}

CCKG Knowledge Graph Context:
{graph_context}

Student Answer:
\"\"\"{ans_text}\"\"\"

Provide your evaluation in valid JSON matching this schema:
{{
  "total_awarded_mark": float,
  "max_marks": float,
  "criteria_evaluations": [
    {{
      "criterion_id": string,
      "awarded_mark": float,
      "explanation": string,
      "evidence_quotes": [string]
    }}
  ],
  "demonstrated_concepts": [string],
  "missing_concepts": [string],
  "prerequisite_concepts_checked": [string],
  "grounding_citations": [string],
  "overall_feedback": string
}}
"""
        req = LLMRequest(
            prompt=prompt,
            model=model_name,
            temperature=0.1,
            max_tokens=650,
            response_format="json"
        )
        res = provider.generate(req)

        pred_mark = 0.0
        if res.is_success and res.parsed_json:
            pred_mark = float(res.parsed_json.get("total_awarded_mark", 0.0))

        pred_mark = max(0.0, min(max_marks, pred_mark))

        results.append({
            "question_id": q_id,
            "answer_type": row.get("quality_type", row.get("answer_type", "unknown")),
            "expected_mark": gt_mark,
            "predicted_mark": pred_mark,
            "error": abs(pred_mark - gt_mark),
            "max_marks": max_marks,
            "graph_nodes": graph_rag_info["graph_nodes_retrieved"],
            "prerequisites_count": len(prereqs),
            "latency_ms": res.latency_ms,
            "tokens": res.usage.total_tokens
        })

    total_time = time.perf_counter() - start_total
    res_df = pd.DataFrame(results)

    mae = float(res_df["error"].mean())
    rmse = float(np.sqrt((res_df["error"] ** 2).mean()))
    tol_2 = float((res_df["error"] <= 2.0).mean() * 100.0)

    irrel_subset = res_df[res_df["expected_mark"] == 0.0]
    irrel_rejected = int((irrel_subset["predicted_mark"] <= 1.0).sum()) if len(irrel_subset) > 0 else 0
    irrel_total = len(irrel_subset)

    summary = {
        "experiment_id": "EXP-04-GRAPHRAG-CCKG",
        "description": "GraphRAG assessment grounded in CCKG curriculum ontology and prerequisite graph",
        "model": model_name,
        "sample_size": len(res_df),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "tolerance_within_2_marks_pct": round(tol_2, 2),
        "irrelevant_distractor_rejection": f"{irrel_rejected}/{irrel_total}",
        "mean_graph_nodes": round(float(res_df["graph_nodes"].mean()), 2),
        "total_runtime_seconds": round(total_time, 2),
        "mean_latency_ms": round(float(res_df["latency_ms"].mean()), 2),
        "total_tokens": int(res_df["tokens"].sum()),
        "output_csv": os.path.join(RESULTS_DIR, "raw_predictions_exp4_graph_rag.csv")
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    res_df.to_csv(summary["output_csv"], index=False)
    summary_path = os.path.join(RESULTS_DIR, "exp4_graph_rag_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[EXP-4 SUMMARY] MAE: {mae:.3f} | RMSE: {rmse:.3f} | Tol (<=2): {tol_2:.1f}% | Latency: {summary['mean_latency_ms']} ms")
    print(f"Results saved to: {summary_path}")
    return summary


if __name__ == "__main__":
    run_experiment_4()
