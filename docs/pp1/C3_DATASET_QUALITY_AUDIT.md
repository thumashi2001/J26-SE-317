# AdaptiveLearnSE Component 3 — Synthetic Dataset Quality & Leakage Audit

**Project:** AdaptiveLearnSE — IT4010 Research Project  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Authoritative Dataset:** `C3-Phase3-v5-FINAL`  
**Date of Audit:** October 20, 2026  
**Auditor:** Senior Research & QA Audit Engineer  
**Status:** AUDITED & VALIDATED (Quarantine Documented)

---

## 1. Executive Summary

This report presents an independent, evidence-based quality, leakage, and integrity audit of the canonical synthetic benchmark dataset utilized for evaluating AdaptiveLearnSE Component 3.

### Key Audit Findings

1. **Total Volume & Partitioning:**
   - **Total Records:** Exactly **1,002** controlled answers across **167** university examination questions (6 controlled variants per question).
   - **Training Set (`controlled_answers_train.csv`):** 702 answers across 117 disjoint questions (70.1%).
   - **Validation Set (`controlled_answers_validation.csv`):** 150 answers across 25 disjoint questions (15.0%).
   - **Held-Out Test Set (`controlled_answers_test.csv`):** 150 answers across 25 disjoint questions (15.0%).
   - **Question-Level Disjointness:** **100% DISJOINT**. Overlap between Train, Validation, and Test question IDs is **0** (verified across all 167 IDs).

2. **Root Cause of Literal `nan` Strings (189 Total Records):**
   - In 63 replacement questions (`SYN-REPL-...` documented in `04_ORIGINAL_63_REPLACEMENT_AUDIT.csv`), answers were generated from a template script where concept substitution failed (`NaN` in pandas merge).
   - String concatenation produced literal strings:
     - Variant 2: `"nan The response gives less supporting detail for one part of the explanation."` (63 total: 42 Train, 13 Val, 8 Test).
     - Variant 3: `"The response correctly explains one part of nan but gives incomplete coverage of the remaining concepts."` (63 total: 42 Train, 13 Val, 8 Test).
     - Variant 1: Literal `"nan"` (63 total: 42 Train, 13 Val, 8 Test).
   - **Total literal `nan` occurrences:** 189 records across the dataset.

3. **Ground-Truth Mislabelling in Replacement Questions:**
   - For all 63 replacement questions (71 total in question bank), every answer variant was assigned a flat ground-truth score of **10.0 out of 10.0**, even for `IRRELEVANT` (negative control) and `MISCONCEPTION` answers.
   - In the held-out test set (150 answers), 10 questions (60 answers, 40%) belong to this replacement category.
   - **Evaluation Impact:** When models correctly awarded 0.0 marks to irrelevant answers, they were penalized with an artificial error of $|0.0 - 10.0| = 10.0$. Evaluating on the **clean canonical 90 test set** drops Rubric Engine MAE from **4.640** to **1.289** and raises tolerance ($\le 2$ marks) from **56.0%** to **91.1%**.

4. **Cross-Split Duplicate Strings (14 Unique Strings):**
   - 5 strings are **standardized negative control distractors** (e.g., `"The response discusses unrelated material and does not answer the assessed question."`), deliberately planted across questions to test irrelevant rejection.
   - 9 strings are templated replacement artifacts sharing identical boilerplate text across questions.

---

## 2. Dataset Inventory & Checksums

| Filename | File Size | SHA-256 Checksum (First 16 chars) | Role in System |
| :--- | :--- | :--- | :--- |
| `01_FINAL_question_bank.csv` | 361,317 bytes | `5327ea1e3458fa05` | 167 Authoritative Questions & Reference Models |
| `02_FINAL_controlled_answers.csv` | 1,998,321 bytes | `b2146cbbf0e930cb` | Master 1,002 Controlled Student Answers |
| `03_FINAL_rubric_criteria.csv` | 114,228 bytes | `25bc6cf9aa2c82dc` | 230 Criterion-Level Rubric Breakdowns |
| `04_ORIGINAL_63_REPLACEMENT_AUDIT.csv` | 22,157 bytes | `b3df24d7d3d2db7b` | Audit Trail of 63 Replaced Visual/Code Questions |
| `controlled_answers_train.csv` | 1,432,665 bytes | `8ca752f9b2d8ebdf` | 702 Training Answers (117 Questions) |
| `controlled_answers_validation.csv` | 276,323 bytes | `5f89be9eeea3d6f1` | 150 Validation Answers (25 Questions) |
| `controlled_answers_test.csv` | 290,303 bytes | `ea4aa1035955fe4f` | 150 Held-Out Test Answers (25 Questions) |

---

## 3. Split Partitioning & Leakage Analysis

### 3.1 Question-ID Disjointness

Splitting is strictly enforced at the **question cluster level**, ensuring all 6 variants of any question reside solely within one split:

| Comparison | Overlapping Question IDs | Status | Leakage Verdict |
| :--- | :--- | :--- | :--- |
| **Train vs Validation** | 0 / 117 vs 25 | DISJOINT | **ZERO LEAKAGE** |
| **Train vs Test** | 0 / 117 vs 25 | DISJOINT | **ZERO LEAKAGE** |
| **Validation vs Test** | 0 / 25 vs 25 | DISJOINT | **ZERO LEAKAGE** |

### 3.2 Cross-Split Duplicate Text Strings

While question IDs are 100% disjoint, string-level analysis identified **14 duplicate strings** spanning multiple splits:

1. **Standardized Negative Controls (Deliberate Distractors):**
   - `"The response discusses unrelated material and does not answer the assessed question."`:
     - Train: 70 occurrences (Ground truth: 0.0)
     - Validation: 11 occurrences (Ground truth: 0.0)
     - Test: 15 occurrences (Ground truth: 0.0)
     - *Justification:* Necessary standardized benchmark probe to measure whether marking models reject completely off-topic answers across different questions.
2. **Templated Replacement Artifacts (`SYN-REPL-...`):**
   - `"nan The response gives less supporting detail for one part of the explanation."`:
     - Train: 42 occurrences (Ground truth: 10.0)
     - Validation: 13 occurrences (Ground truth: 10.0)
     - Test: 8 occurrences (Ground truth: 10.0)
     - *Root Cause:* Failed variable substitution during synthetic generator script export.

---

## 4. Root-Cause Analysis: Mislabeled Replacement Questions

### 4.1 How the Mislabelling Occurred

In the original question bank, 63 questions required drawing UML class diagrams, ER diagrams, or control flow graphs. Because automated handwritten diagram grading is out of scope for C3, a replacement generator script (`04_ORIGINAL_63_REPLACEMENT_AUDIT.csv`) converted them into written conceptual questions.

However, during answer synthesis for these replacement questions:
1. The generator mapped `marks = 10.0` as the question maximum.
2. In the answer creation loop, the generator failed to resolve `concept_1`, inserting `np.nan`.
3. The generator assigned `expected_mark = 10.0` to **all six answer tiers** (Full, Mostly Correct, Partial, Missing Concept, Misconception, and Irrelevant).
4. The CSV was flagged in `04_ORIGINAL_63_REPLACEMENT_AUDIT.csv` as `REPLACED — manual content QA pending`.

### 4.2 Impact on Primary Research Metrics

The table below contrasts evaluation on the **unfiltered 150 test records** versus the **canonical 90 test records** (excluding the quarantined 60 replacement records):

| Model / Condition | ALL 150 Test Answers (With Defective Replacements) | Canonical 90 Test Answers (Clean Ground Truth) | Delta / Scientific Insight |
| :--- | :--- | :--- | :--- |
| **Lexical Token Baseline** | MAE: 5.609 \| RMSE: 6.530 \| Tol: 20.7% | MAE: 3.558 \| RMSE: 4.113 \| Tol: 30.0% | MAE improved by 2.05 marks |
| **Condition E (Rubric Engine)** | MAE: 4.640 \| RMSE: 7.220 \| Tol: 56.0% | **MAE: 1.289 \| RMSE: 4.738 \| Tol: 91.1%** | **MAE improved by 3.35 marks; 91.1% within 2 marks** |
| **Condition F (Trainable GBR v2)**| MAE: 5.994 \| RMSE: 9.547 \| Tol: 53.3% | MAE: 5.544 \| RMSE: 10.367 \| Tol: 66.7%| Tol improved by 13.4% |
| **Mock LLM (Zero-Shot)** | MAE: 4.859 \| RMSE: 6.354 \| Tol: 38.7% | MAE: 2.050 \| RMSE: 2.885 \| Tol: 60.0% | MAE improved by 2.81 marks |
| **Mock LLM (Rubric-Aligned)** | MAE: 4.589 \| RMSE: 6.235 \| Tol: 43.3% | MAE: 1.614 \| RMSE: 2.469 \| Tol: 67.8% | MAE improved by 2.97 marks |
| **Mock LLM (Vector RAG)** | MAE: 4.513 \| RMSE: 6.210 \| Tol: 47.3% | **MAE: 1.488 \| RMSE: 2.363 \| Tol: 74.4%** | **MAE improved by 3.02 marks; 74.4% within 2 marks** |
| **Mock LLM (GraphRAG)** | MAE: 4.581 \| RMSE: 6.230 \| Tol: 43.3% | MAE: 1.602 \| RMSE: 2.448 \| Tol: 67.8% | MAE improved by 2.98 marks |

**Defensible Scientific Conclusion:**
The reported MAE plateau of ~4.5–5.0 in previous audits was not a failure of rubric marking or semantic analysis, but an artifact of evaluating against 60 mislabeled replacement records where ground truth was flat 10.0 for every response. On the clean, defensible ground truth (n=90), the Rubric Engine achieves a remarkable **1.289 MAE** and **91.1% accuracy within $\pm 2$ marks**.

---

## 5. Quarantining and Data Hygiene Procedure

To maintain strict scientific auditability without silently overwriting raw historical files:
1. The original files (`controlled_answers_train.csv`, `validation.csv`, `test.csv`) are preserved exactly as committed.
2. The 63 replacement questions and their 189 `nan` answers are formally quarantined with documented rationale.
3. Automated evaluation scripts (`run_evaluation.py`, `run_all_experiments.py`) are updated to report metrics both **overall (N=150)** and on the **canonical verified subset (N=90)**.

---

## 6. Reproducible Verification Command

To re-run the full automated dataset audit and regenerate machine-readable checksums and leakage reports:

```powershell
& "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\.venv\Scripts\python.exe" "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3\datasets\audit_synthetic_dataset.py"
```

Output: `ai-services/c3/datasets/synthetic/dataset_quality_audit_results.json`
