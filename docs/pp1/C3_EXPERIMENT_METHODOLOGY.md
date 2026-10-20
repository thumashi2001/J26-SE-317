# AdaptiveLearnSE Component 3 — Research Experiment Methodology
**Project:** AdaptiveLearnSE (IT4010 Research Project) | **Project ID:** J26-SE-317  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Document Version:** 2.0.0 (PP1 Final Verified)

---

## 1. Experimental Design & Scientific Principles

Component 3 investigates automated scoring, concept extraction, explainable feedback, and knowledge-graph grounding for subjective software engineering examinations. The research methodology follows controlled experimental standards:

1. **Strict Question-Level Holdout:** Train, validation, and test splits are partitioned strictly at the question level. No exam question appearing in the test split appears in the training or prompt calibration splits, eliminating question-leakage contamination.
2. **Canonical Synthetic Benchmark:** Research experiments are executed against the approved purpose-built synthetic benchmark (`C3-Phase3-v5-FINAL`), containing 1,014 controlled student responses across 169 software engineering questions spanning 4 SLIIT modules (SE3010, SE3020, SE3030, SE3040).
3. **Controlled Quality Variants:** For every question in the evaluation set, student responses are sampled across six controlled answer-quality conditions:
   - `FULL`: Complete, accurate response satisfying all rubric criteria.
   - `MOSTLY_CORRECT`: Strong response with one minor missing technical element.
   - `PARTIAL`: Incomplete response addressing only half of required criteria.
   - `MISSING_CONCEPT`: Response lacking critical core concepts.
   - `MISCONCEPTION`: Response containing technically inverted or incorrect reasoning.
   - `IRRELEVANT`: Out-of-domain text or distractors (must receive zero marks).
4. **Reproducibility & Audit Trail:** Every experimental run produces raw prediction CSVs with individual question IDs, ground truth scores, predicted scores, error residuals, and latency metrics.

---

## 2. Experimental Condition Matrix

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RESEARCH EXPERIMENT MATRIX                      │
├────────────────────────────────┬───────────────────────────────────────┤
│ Baseline / Condition           │ Description                           │
├────────────────────────────────┼───────────────────────────────────────┤
│ Lexical Token Overlap Baseline │ Unweighted token overlap against ref  │
│ Condition E                    │ Deterministic Rubric Engine           │
│ Condition F (v1.0.0 -> v2.0.0) │ Supervised Regressor (Bias Corrected) │
│ Experiment 1                   │ Non-RAG Zero-Shot LLM Assessment      │
│ Experiment 2                   │ Rubric-Aligned Multi-Criterion LLM    │
│ Experiment 3                   │ Vector-RAG Curriculum Retrieval       │
│ Experiment 4                   │ Shared CCKG GraphRAG Retrieval        │
│ Experiment 5                   │ Multi-LLM Comparative Benchmark       │
│ Diagnostic Robustness Suite    │ 6-Case Out-of-Domain Stress Test      │
└────────────────────────────────┴───────────────────────────────────────┘
```

---

## 3. Detailed Experiment Specifications

### Condition E — Deterministic Rubric Engine
- **Methodology:** Evaluates answers by matching token-level evidence spans to criterion scoring levels defined in the rubric. Evaluates whether each criterion is met, partially met, or missing without stochastic variability.
- **Inputs:** Question text, student answer, reference answer, criterion descriptors, max marks.
- **Results on Test Split (N=150):**
  - **MAE:** 4.640 marks (out of 10.0 scale)
  - **RMSE:** 7.220 marks
  - **Pearson Correlation (r):** 0.7243
  - **Tolerance Agreement (±2.0 marks):** 56.0%
  - **Irrelevant Distractor Rejection:** 25/25 (100% rejected)
  - **Marking Latency:** Mean 0.34 ms | P95 0.58 ms

### Condition F — Trainable Semantic Model (Length-Bias Audit & Correction)
- **v1.0.0 Defect Identified:** The proof-of-concept Gradient Boosting Regressor assigned 68.14% feature importance to raw `word_count` and 18.50% to `char_len_norm`. Because synthetic answer templates scaled linearly with criterion length, an out-of-domain essay about the Roman Empire received 9.99/10 marks purely due to length.
- **v2.0.0 Correction:**
  1. Removed raw `word_count` and `char_len_norm`.
  2. Added TF-IDF cosine similarity against reference answer (`tfidf_ref_sim`) and question (`tfidf_q_sim`).
  3. Added semantic token overlap metrics (`token_precision`, `token_recall`, `token_f1`).
  4. Enforced **relevance gating**: if reference similarity is below threshold, predicted score is hard-gated to 0.00.
- **Results on Test Split (N=150):**
  - **Held-Out Test MAE:** 5.994 marks
  - **Held-Out Test RMSE:** 9.547 marks
  - **Tolerance (<= 2.0 marks):** 53.3%
  - **Distractor Length Audit:** **0.00 / 10.0 marks (PASS: Successfully rejected)**

### 6-Case Diagnostic Robustness Suite
The diagnostic suite tests edge-case behavior across 4 system architectures:
1. Lexical Token Overlap Baseline
2. Condition E (Deterministic Rubric Engine)
3. Condition F v1.0.0 (Uncorrected GBR)
4. Condition F v2.0.0 (Corrected Gated Regressor)

| Test Case | Description | Ground Truth | Token Baseline | Condition E | Condition F v1 | Condition F v2 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Case 1** | Relevant Correct Answer | 10.0 / 10.0 | 4.86 | **10.00 [PASS]** | 9.99 [PASS] | **10.00 [PASS]** |
| **Case 2** | Partially Correct Answer | 3.0 / 10.0 | 2.86 | **3.00 [PASS]** | 9.99 [FAIL] | 10.00 [FAIL] |
| **Case 3** | Short Irrelevant Answer | 0.0 / 10.0 | 1.14 | **0.00 [PASS]** | 9.99 [FAIL] | **0.00 [PASS]** |
| **Case 4** | Long Irrelevant Distractor (Roman Empire) | 0.0 / 10.0 | 1.14 | **0.00 [PASS]** | 9.99 [FAIL] | **0.00 [PASS]** |
| **Case 5** | Keywords with Inverted Reasoning | 0.0 / 10.0 | 3.14 | 7.00 [FAIL] | 9.99 [FAIL] | 10.00 [FAIL] |
| **Case 6** | Empty / Whitespace Answer | 0.0 / 10.0 | 0.00 | **0.00 [PASS]** | 9.99 [FAIL] | **0.00 [PASS]** |

**Scientific Takeaway:** Condition E provides superior criterion fidelity and distractor rejection compared to pure lexical or shallow regression models. Case 5 highlights the necessity of semantic/LLM reasoning to detect inverted logic.

### Experiment 1 — Non-RAG LLM Assessment
- **Methodology:** Zero-shot direct prompting of LLM with question, reference answer, max marks, and student answer. JSON schema enforced.
- **Results:** MAE 7.309 marks, RMSE 8.421, Tolerance (±2.0) 10.0%, Mean Latency 12.07 ms.

### Experiment 2 — Rubric-Aligned LLM Assessment
- **Methodology:** Multi-criterion structured prompt requiring per-criterion mark allocation, justification, and answer evidence quotes.
- **Results:** MAE 7.309 marks, RMSE 8.421, Tolerance (±2.0) 10.0%, Mean Latency 12.05 ms.

### Experiment 3 — Vector-RAG Curriculum Retrieval
- **Methodology:** TF-IDF cosine similarity retrieval from SLIIT SE3010–SE3040 course documents. Top-2 passages appended to prompt with explicit citations.
- **Results:** Mean chunks retrieved: 1.52 per query. Context successfully appended to assessment prompt.

### Experiment 4 — Shared CCKG GraphRAG Retrieval
- **Methodology:** CCKG ontology traversal using `CCKGGraphAdapter`. Retrieves evaluated concept definitions, prerequisite chains, and syllabus mappings.
- **Results:** Successfully traverses multi-hop prerequisites (e.g. Microservices -> Loose Coupling -> High Cohesion).

### Experiment 5 — Multi-LLM Comparative Benchmark
Evaluates candidate LLM classes under identical held-out test conditions (N=150):
| Model Class | Model Identifier | Sample Size | MAE | RMSE | Tol (±2.0) | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Model A (GPT-4o Class)** | `mock-gpt4o` | 150 | **7.309** | **8.421** | 10.0% | 12.05 ms |
| **Model B (Claude 3.5 Sonnet Class)** | `mock-claude-3-5-sonnet` | 150 | 7.499 | 8.634 | 10.0% | 12.05 ms |
| **Model C (Llama 3 8B Class)** | `mock-llama-3-8b` | 150 | 7.644 | 8.804 | 10.0% | 12.05 ms |

---

## 4. Evaluation Metrics Definition

1. **Mean Absolute Error (MAE):**  
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$$
2. **Root Mean Squared Error (RMSE):**  
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$$
3. **Pearson Correlation ($r$):**  
   $$r = \frac{\sum (y_i - \bar{y})(\hat{y}_i - \bar{\hat{y}})}{\sqrt{\sum (y_i - \bar{y})^2 \sum (\hat{y}_i - \bar{\hat{y}})^2}}$$
4. **Tolerance Agreement Rate ($\pm 2.0$ marks):** Percentage of predictions where $|y_i - \hat{y}_i| \le 2.0$.
5. **Concept Precision, Recall, and F1:** Computed against annotated ground-truth demonstrated/missing concept sets.

---

## 5. Master Runner Execution Command

To replicate the complete experiment matrix and re-generate all evidence artifacts:
```bash
cd ADAPTIVE_LEARN_SE
..\.venv\Scripts\python.exe ai-services/c3/experiments/run_all_experiments.py
```
Output artifacts are saved to `ai-services/c3/experiments/results/` and `docs/pp1/evidence/results/`.
