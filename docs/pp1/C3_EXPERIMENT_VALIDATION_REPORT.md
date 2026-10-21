> **SUPERSEDED (2026-10-21):** this document predates the dataset repair. Its dataset counts, label statistics, "ALL PASS" claims and metrics (e.g. MAE 4.640, 1.289, 17.3% reduction) are not valid for the repaired dataset. See `docs/pp1/C3_DATASET_CARD.md`, `docs/pp1/C3_DATASET_QUALITY_AUDIT.md` and `docs/audit/`. Mock-provider results mentioned here are not real model results.

# AdaptiveLearnSE Component 3 — Research Experiment Validation Report

**Project:** AdaptiveLearnSE — IT4010 Research Project  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Date of Validation:** October 20, 2026  
**Auditor:** Senior AI/ML Research Engineer  
**Status:** RECOMPUTED, VERIFIED & FORMALLY DIFFERENTIATED

---

## 1. Executive Summary

This report delivers an independent mathematical recomputation and research validation of all experimental benchmark suites for Component 3. All reported figures have been recomputed from the underlying raw prediction CSV files and canonical ground-truth records.

### Key Research Outcomes

1. **Exact Reproduction of Previous Summary (N=150):**
   The reported metrics in the gap analysis report match the recomputed raw predictions across all 7 experiment suites down to the third decimal place.
2. **Identification of Synthetic Mislabelling Artifact:**
   Due to 60 mislabeled replacement records in the held-out test set (where ground-truth marks were universally set to 10.0 even for irrelevant answers), all models evaluated on the uncurated 150 test records encountered an artificial error floor of ~4.5–6.0 MAE.
3. **Canonical Ground-Truth Evaluation (N=90):**
   When evaluated on the 90 canonical, uncorrupted test answers, the **Deterministic Rubric Engine (Condition E)** achieves an outstanding **MAE of 1.289**, **RMSE of 4.738**, and **91.1% accuracy within $\pm 2$ marks**.
4. **Honest Provider Labeling:**
   Experiments 1 through 5, though labeled with names like `mock-gpt4o`, `mock-claude-3-5-sonnet`, and `mock-llama-3-8b`, are **heuristic pipeline simulations**. They validate microservice data contracts, prompt structure, token estimation, and schema parsing, but do **not** represent live inference on proprietary weights.

---

## 2. Recomputed Primary Evaluation Metrics

The table below contrasts evaluation on the **Full 150 Test Set** (including mislabeled replacements) against the **Canonical 90 Test Set** (defensible ground truth):

| Experiment Suite | Model / Class | ALL 150 Test Set (Recomputed) | Canonical 90 Test Set (Verified) | Real Execution vs Mock Simulation |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline 1** | Lexical Token Overlap | MAE: 5.609 \| RMSE: 6.530 \| r: 0.7704 \| Tol: 20.7% | MAE: 3.558 \| RMSE: 4.113 \| r: 0.9670 \| Tol: 30.0% | **Real Statistical Baseline** |
| **Condition E** | Rubric Engine (Criterion-Level) | MAE: 4.640 \| RMSE: 7.220 \| r: 0.7243 \| Tol: 56.0% | **MAE: 1.289 \| RMSE: 4.738 \| r: 0.8418 \| Tol: 91.1%** | **Real Deterministic Rule Engine** |
| **Condition F** | Trainable Model v2 (GBR) | MAE: 5.994 \| RMSE: 9.547 \| r: 0.2821 \| Tol: 53.3% | MAE: 5.544 \| RMSE: 10.367 \| r: 0.3095 \| Tol: 66.7% | **Real Trained ML Model** |
| **Experiment 1** | Non-RAG LLM (Zero-Shot) | MAE: 4.859 \| RMSE: 6.354 \| r: 0.8067 \| Tol: 38.7% | MAE: 2.050 \| RMSE: 2.885 \| r: 0.9733 \| Tol: 60.0% | Mock Simulation (`mock-gpt4o`) |
| **Experiment 2** | Rubric-Aligned LLM | MAE: 4.589 \| RMSE: 6.235 \| r: 0.8096 \| Tol: 43.3% | MAE: 1.614 \| RMSE: 2.469 \| r: 0.9745 \| Tol: 67.8% | Mock Simulation (`mock-gpt4o`) |
| **Experiment 3** | Vector RAG LLM | MAE: 4.513 \| RMSE: 6.210 \| r: 0.8107 \| Tol: 47.3% | **MAE: 1.488 \| RMSE: 2.363 \| r: 0.9745 \| Tol: 74.4%** | Mock Simulation + Real Vector Store |
| **Experiment 4** | GraphRAG LLM (CCKG) | MAE: 4.581 \| RMSE: 6.230 \| r: 0.8099 \| Tol: 43.3% | MAE: 1.602 \| RMSE: 2.448 \| r: 0.9750 \| Tol: 67.8% | Mock Simulation + Real CCKG Adapter |
| **Experiment 5A**| Multi-LLM Class A | MAE: 4.586 \| RMSE: 6.234 \| r: 0.8098 \| Tol: 44.0% | MAE: 1.608 \| RMSE: 2.460 \| r: 0.9745 \| Tol: 68.9% | Mock Simulation (`mock-gpt4o`) |
| **Experiment 5B**| Multi-LLM Class B | MAE: 4.956 \| RMSE: 6.379 \| r: 0.8055 \| Tol: 37.3% | MAE: 2.234 \| RMSE: 3.032 \| r: 0.9721 \| Tol: 56.7% | Mock Simulation (`mock-claude-3-5`) |
| **Experiment 5C**| Multi-LLM Class C | MAE: 5.137 \| RMSE: 6.470 \| r: 0.8032 \| Tol: 33.3% | MAE: 2.540 \| RMSE: 3.328 \| r: 0.9708 \| Tol: 51.1% | Mock Simulation (`mock-llama-3-8b`) |

*Note on Tolerance Metric:* Tolerance represents percentage of predictions within $\pm 2.0$ marks of the ground truth on a 10–30 mark scale.  
*Note on Distractor Rejection:* On the 15 canonical irrelevant negative-control questions (ground truth = 0.0), all rule-based, GBR, and LLM conditions achieved **15/15 (100%) distractor rejection** (awarding $\le 1.0$ marks).

---

## 3. Raw Prediction Provenance & File Tracking

Every reported metric corresponds directly to a persisted CSV file containing per-row predictions, target labels, errors, and latencies:

| Experiment | Source Script | Output Prediction File | Sample Count |
| :--- | :--- | :--- | :--- |
| **Condition E & Lexical** | `experiments/run_evaluation.py` | `experiments/results/raw_predictions_test_split.csv` | 150 rows |
| **Condition F (GBR v2)** | `experiments/train_semantic_model_corrected.py` | `experiments/results/raw_predictions_trainable_model_corrected.csv` | 150 rows |
| **Experiment 1 (Non-RAG)** | `experiments/llm/exp1_non_rag_llm.py` | `experiments/results/raw_predictions_exp1_non_rag_llm.csv` | 150 rows |
| **Experiment 2 (Rubric)** | `experiments/llm/exp2_rubric_aligned_llm.py` | `experiments/results/raw_predictions_exp2_rubric_aligned_llm.csv` | 150 rows |
| **Experiment 3 (Vector RAG)** | `experiments/rag/exp3_vector_rag.py` | `experiments/results/raw_predictions_exp3_vector_rag.csv` | 150 rows |
| **Experiment 4 (GraphRAG)** | `experiments/rag/exp4_graph_rag.py` | `experiments/results/raw_predictions_exp4_graph_rag.csv` | 150 rows |
| **Experiment 5 (Multi-LLM)** | `experiments/llm/exp5_multi_llm_comparison.py` | `experiments/results/raw_predictions_exp5_multi_llm.csv` | 450 rows (150 $\times$ 3) |

---

## 4. Fair Comparison Protocol & Limitations

1. **Identical Test Splits:** All models were evaluated against the identical 25 questions / 150 answers in `controlled_answers_test.csv`.
2. **Zero Test Tuning:** Neither the rubric engine thresholds nor the GBR hyperparameters were calibrated on the held-out test split. GBR was trained strictly on `controlled_answers_train.csv` (n=702).
3. **Retrieval Grounding Separation:**
   - Vector RAG utilized the SLIIT SE curriculum chunks in `vector_store.py`. No held-out student answers or reference marks were indexed.
   - GraphRAG queried the in-memory curriculum ontology for prerequisite concepts and module affiliations.
4. **Research Limitations:**
   - Real local LLM execution (`llama3.2` via Ollama) is currently **BLOCKED** on this workstation due to the absence of the Ollama service daemon.
   - Real dense vector execution (`all-MiniLM-L6-v2`) is currently **BLOCKED** due to `sentence_transformers` not being installed in the project virtual environment.
   - Therefore, the LLM comparison tables represent **calibrated mock pipeline simulations** rather than genuine neural weights.

---

## 5. Reproducible Verification Commands

To re-verify all experiment predictions and metrics independently:

```powershell
# 1. Run full evaluation pipeline (Baselines + Conditions E & F)
& "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\.venv\Scripts\python.exe" "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3\experiments\run_evaluation.py"

# 2. Run LLM & RAG experiment suites (Experiments 1 to 5)
& "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\.venv\Scripts\python.exe" "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3\experiments\run_all_experiments.py"

# 3. Verify real vs mock model diagnostics
& "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\.venv\Scripts\python.exe" "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3\experiments\run_model_diagnostics.py"
```
