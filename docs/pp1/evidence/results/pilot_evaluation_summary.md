# AdaptiveLearnSE Component 3 — Research Evaluation Summary

**Date:** 2026-10-20 11:37:19 UTC  
**Dataset Split:** Test split (25 questions, 150 controlled student answers)  
**Dataset Version:** `C3-Phase3-v5-FINAL`  

## 1. Quantitative Performance Comparison

| Model / Method | MAE (Lower is better) | RMSE | Pearson Correlation (r) | Tolerance Agreement (±2.0) |
| :--- | :--- | :--- | :--- | :--- |
| **C3 Rubric-Aware Marking (Current)** | **4.640** | **7.220** | **0.7243** | **56.0%** |
| Lexical Token-Overlap Baseline | 5.609 | 6.530 | 0.7704 | 38.0% |

## 2. Quality Condition Breakdown

| Answer Quality Condition | Count | Mean Ground Truth | Mean Predicted | MAE |
| :--- | :--- | :--- | :--- | :--- |
| `FULL` | 25 | 13.96 | 9.96 | 4.0 |
| `MOSTLY_CORRECT` | 25 | 12.06 | 4.46 | 7.6 |
| `PARTIAL` | 25 | 10.22 | 5.18 | 5.04 |
| `MISSING_CONCEPT` | 25 | 12.06 | 8.86 | 3.2 |
| `MISCONCEPTION` | 25 | 12.06 | 8.06 | 4.0 |
| `IRRELEVANT` | 25 | 4.0 | 0.0 | 4.0 |

## 3. Explainability, Diagnosis & System Latency

- **Concept Diagnosis Precision:** 90.9%
- **Concept Diagnosis Recall:** 98.0%
- **Concept Diagnosis F1:** 94.3%
- **Feedback Structural Validity:** 100.0%
- **Mind Map Generation Validity:** 100.0%
- **Marking Latency:** Mean 0.32 ms | Median 0.27 ms | P95 0.5 ms

## 4. Viva Boundary Status: Conditions A–F

| Condition | Description | Actual Status |
| :--- | :--- | :--- |
| Condition A | LLM-only Direct Prompting | Deferred (Not Started) |
| Condition B | LLM + Rubric Guidance | Deferred (Not Started) |
| Condition C | LLM + Rubric + Vector RAG | Deferred (Not Started) |
| Condition D | LLM + Rubric + GraphRAG (Neo4j CCKG) | Deferred (Not Started) |
| Condition E | Deterministic Concept Evidence + Rubric | **Implemented & Evaluated (Active Prototype)** |
| Condition F | Full Multimodal / Multi-LLM Ensemble | Deferred (Not Started) |

> **Research Ethics & Transparency Statement:** All numbers reported above were generated directly from execution against the canonical test split. No expert validation is fabricated or claimed.
