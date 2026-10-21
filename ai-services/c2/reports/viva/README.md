# Component 2 (C2) Machine Learning Evaluation Visualizations

This directory contains publication-quality (300 DPI) evaluation figures and artifacts prepared for the undergraduate research viva. All visualizations are grounded in **actual, measured evaluation artifacts** from the `ai-services/c2` research pipeline.

---

## 1. Figure Inventory

| Figure File | Title / Focus | Evaluation Protocol | Source Data / Service |
|---|---|---|---|
| **`fig1_m17_model_comparison.png`** | M17 Topic Classifier: Baseline Architecture Comparison | **SYNTHETIC EVALUATION** (Validation Split, N=128) | `outputs/reports/m17_evaluation_report.json` |
| **`fig2_m17_abstention.png`** | M17 Topic Classifier: Confidence Abstention & Coverage Trade-Off | **SYNTHETIC EVALUATION** (Validation Split, N=128) | `outputs/reports/m17_evaluation_report.json` |
| **`fig3_m21_confusion_matrix.png`** | M21 Bloom's Taxonomy Cognitive Classification: Confusion Matrix | **SYNTHETIC EVALUATION** (Module-Disjoint Test, N=200) | `reports/m21_bloom_classifier_evaluation.json` |
| **`fig4_m21_class_f1.png`** | M21 Bloom's Taxonomy: Per-Class Performance Breakdown | **SYNTHETIC EVALUATION** (Module-Disjoint Test, N=200) | `reports/m21_bloom_classifier_evaluation.json` |
| **`fig5_m22_prediction_comparison.png`** | M22 Exam Topic Prediction: Baseline Algorithmic Comparison | **SYNTHETIC WALK-FORWARD DEMONSTRATION** (5 Sessions) | `SyntheticTopicPredictionService.generate_experimental_demonstration()` |

---

## 2. Detailed Figure Descriptions

### Figure 1: `fig1_m17_model_comparison.png`
- **Objective:** Compares Baseline A (TF-IDF + Multinomial Logistic Regression) against Baseline B (TF-IDF + Linear Support Vector Machine) across all 8 Year 3 Software Engineering modules.
- **Metrics Plotted:**
  - *Left Panel (Performance):* Overall Accuracy (1.0000 vs 1.0000), Macro-F1 (1.0000 vs 1.0000), Macro-Precision (1.0000 vs 1.0000), Macro-Recall (1.0000 vs 1.0000), Weighted-F1 (1.0000 vs 1.0000).
  - *Right Panel (Latency):* Total inference time over 128 validation questions (Logistic Regression: 18.5 ms vs Linear SVM: 11.3 ms).
- **Key Viva Finding:** Because both linear models achieve a perfect Macro-F1 tie on synthetic validation scenarios, Logistic Regression was selected as the frozen production model using a deterministic tie-breaker for native, well-calibrated posterior class probabilities.
- **Dataset & Provenance:** M16 synthetic development dataset (`training_export` split). Authentic examination evaluation was explicitly **NOT PERFORMED**.

### Figure 2: `fig2_m17_abstention.png`
- **Objective:** Evaluates the conservative abstention framework across confidence probability thresholds $\tau \in [0.20, 0.50]$.
- **Metrics Plotted:** Automated decision coverage (% retained) vs accuracy on retained questions.
- **Key Viva Finding:**
  - At the recommended operating threshold $\tau = 0.38$, the model retains **93.8%** coverage (120/128 questions) with **100.0%** retained accuracy, abstaining on 8 uncertain questions.
  - At $\tau \ge 0.50$, the system safely exhibits complete abstention (0% coverage), routing all ambiguous questions to lecturer review.
- **Dataset & Provenance:** M16 synthetic validation split (128 questions).

### Figure 3: `fig3_m21_confusion_matrix.png`
- **Objective:** Assesses cognitive level classification across Bloom's Taxonomy categories (`analyze`, `apply`, `create`, `evaluate`).
- **Metrics Plotted:** $4 \times 4$ confusion matrix displaying absolute sample counts and row-normalized class recall percentages.
- **Key Viva Finding:** Overall accuracy is **35.0%** (Macro-F1: 0.3247). The highest confusion occurs between `analyze` and `evaluate` (27/60 true `analyze` questions misclassified as `evaluate`), reflecting the linguistic reality that software engineering scenarios often blend analysis prompts with comparative evaluation tasks.
- **Dataset & Provenance:** 800 synthetic questions partitioned via `GroupShuffleSplit` (75% train / 25% test across disjoint modules: 600 train / 200 held-out test). Authentic evaluation is marked **not_evaluable** due to 0 lecturer-verified authentic Bloom labels.

### Figure 4: `fig4_m21_class_f1.png`
- **Objective:** Details per-class precision, recall, and F1-score for Bloom's Taxonomy levels.
- **Metrics Plotted:** Grouped bars for Precision, Recall, and F1 per class against benchmark lines for Macro-F1 (0.3247) and Overall Accuracy (0.3500).
- **Key Viva Finding:** The `create` level achieved the highest performance (F1 = 0.5098, Precision = 0.6190, N=60) due to distinct generative vocabulary (e.g., *design, implement, construct*). The `apply` category exhibited the lowest performance (F1 = 0.0968, N=40) due to syntactic overlap with common assignment verbs.
- **Dataset & Provenance:** 200 held-out synthetic test questions across disjoint Year 3 curriculum modules.

### Figure 5: `fig5_m22_prediction_comparison.png`
- **Objective:** Compares three examination topic prediction baselines evaluated using a chronological walk-forward split protocol.
  1. *Baseline A:* Historical Frequency
  2. *Baseline B:* Recency-Weighted Frequency ($\lambda = 0.75$)
  3. *Baseline C:* Regularized Statistical Model (L2 Trend Regression)
- **Metrics Plotted:**
  - *Left Panel (Retrieval Quality):* Mean Precision@3 (A: 0.556, B: 0.556, C: 0.667), Mean Recall@3 (A: 0.556, B: 0.556, C: 0.667), Mean Reciprocal Rank (1.000 for all).
  - *Right Panel (Prediction Error):* Mean Brier Score (A: 0.4005, B: 0.3798, C: 0.3520).
- **Key Viva Finding:** Baseline C demonstrates an **12.1% reduction in Brier error** over Baseline A and improves Precision@3 / Recall@3 from 0.556 to 0.667 by capturing temporal trend signals without overfitting.
- **Ranking Terminology Note:** Prediction outputs represent **ranking priority and trend scores**, NOT calibrated probabilities.
- **Dataset & Provenance:** 5-year deterministic chronological synthetic examination sequence (2019–2023) modeling authentic SLIIT examination structures. Authentic predictions remain strictly blocked awaiting lecturer verification.

---

## 3. Academic Integrity & Research Limitations

1. **Synthetic Corpus Scope:** M17, M21, and M22 models were evaluated on deterministic synthetic datasets derived from the approved SLIIT Year 3 curriculum. Performance on synthetic data does not guarantee equivalent accuracy on genuine examination papers.
2. **Template Family Overlap:** In M17, scenario groups are strictly disjoint across splits, but task phrasing templates share common structures to preserve all 5 curriculum topics across train/val/test splits.
3. **Authentic Data Isolation:** Authentic SLIIT past-paper questions (443 items) remain strictly gated from automated decision-making pending lecturer verification.
4. **Reproducibility:** All figures can be re-rendered deterministically at any time using:
   ```powershell
   # From ai-services/c2:
   .\.venv\Scripts\python.exe reports/viva/generate_viva_charts.py
   ```
