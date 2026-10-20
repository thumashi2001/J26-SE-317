# AdaptiveLearnSE Component 3 — Research Experiment Matrix & Condition Status

**Document Version:** 2.0.0 (Authoritative PP1 Experiment Audit)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  

---

## 1. Research Experimental Framework Overview

In the research methodology for Component 3, six experimental conditions (Conditions A through F) were formulated to evaluate the progression from unconstrained generative scoring to hybrid deterministic-retrieval architectures:

```
[Progression of Component 3 Research Conditions]

Condition A: Zero-Shot Generative LLM
     │ (Unconstrained direct prompt; high hallucination risk)
     ▼
Condition B: In-Context Rubric LLM
     │ (Few-shot prompt with rubric descriptors)
     ▼
Condition C: Vector-RAG + Rubric LLM
     │ (Dense embeddings over course lecture notes)
     ▼
Condition D: GraphRAG (Neo4j CCKG) + Rubric LLM
     │ (Curriculum graph traversal of prerequisite concepts)
     ▼
Condition E: Deterministic Concept Evidence + Rubric Evaluator ◄── [ACTIVE PP1 PROTOTYPE]
     │ (Regex token matching + discrete rubric level scoring + SVG DAG)
     ▼
Condition F: Full Multimodal Multi-Model Ensemble
       (Combined ensemble for final dissertation)
```

---

## 2. Experimental Condition Status & Milestone Auditing

| Condition ID | Architectural Description | Planned Scope | Current Milestone Status | Empirical Evidence in Repo | Defense Justification for Viva |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Condition A** | **Direct LLM Zero-Shot Prompting** | Generative scoring using direct prompt without explicit rubric constraint. | ⏸️ **Deferred (Not Started)** | Documented in `DATASET_AND_EVALUATION_REPORT.md` | Deferred to Phase 4. Avoids volatile API costs and uncalibrated scores during initial baseline establishment. |
| **Condition B** | **LLM + In-Context Rubric** | Prompt augmented with structured scoring levels and criteria descriptors. | ⏸️ **Deferred (Not Started)** | Documented in `DATASET_AND_EVALUATION_REPORT.md` | Deferred to Phase 4. Serves as direct generative comparator to Condition E. |
| **Condition C** | **LLM + Rubric + Dense Vector RAG** | Retrieval-Augmented Generation retrieving course notes via vector embeddings. | ⏸️ **Deferred (Not Started)** | Documented in `DATASET_AND_EVALUATION_REPORT.md` | Requires course slide embedding index; scheduled for post-PP1 Phase 4. |
| **Condition D** | **LLM + Rubric + Neo4j GraphRAG** | Graph-augmented prompt traversing CCKG curriculum prerequisite ontology. | ⏸️ **Deferred (Not Started)** | Documented in `CCKG_STATUS_AND_GAPS.md` | Dependent on team-wide CCKG implementation in Neo4j. |
| **Condition E** | **Deterministic Concept Evidence + Rubric** | Deterministic token normalization, concept regex evidence matching, discrete rubric level scoring, and SVG DAG synthesis. | ✅ **Implemented, Evaluated & Authoritative** | `ai-services/c3/services/`<br>`verify_evaluation.py`<br>`raw_predictions_test_split.csv`<br>`ss/12_evaluation_results.png` | **Primary Active PP1 Prototype.** 100% reproducible, 140 passing tests, 17.3% lower MAE than baseline, 0.34ms in-process CPU latency. |
| **Condition F** | **Trainable Semantic Ensemble** | Supervised Gradient Boosting Regressor trained on TF-IDF + rubric coverage, fused with Condition E discrete rubric bounds. | ✅ **Implemented, Trained & Evaluated** | `ai-services/c3/models/c3_scoring_regressor.joblib`<br>`ai-services/c3/experiments/train_semantic_model.py`<br>`raw_predictions_trainable_model.csv` | **PP1 Trainability PoC.** Satisfies PP1 model trainability requirement with learned parameters, N=702 train split fitting, and zero-leakage evaluation. |

---

## 3. Detailed Profile of the Active Prototype: Condition E

Condition E serves as the authoritative, demonstrable baseline prototype for PP1:

### 3.1 Architectural Pipeline:
1. **F1: Answer Preprocessing & Semantic Matching:**
   - Input answer text is segmented into numbered sentences (`SentenceSegmenter`).
   - Lexical terms are normalized (lowercased, punctuation-stripped, stopword-handled).
   - Concept evidence is discovered using deterministic token regex matching against `required_concepts`.
2. **F2: Rubric-Aware Marking Engine:**
   - Evaluates each rubric criterion independently.
   - Iterates through defined scoring levels (`Full`, `Partial`, `None`) in descending order of marks.
   - Selects the highest level whose `required_concepts` are demonstrably present in the extracted sentence evidence spans.
   - Bounded strictly between $0.0$ and `max_marks`.
3. **F3: Explainable Feedback Generation:**
   - Summarizes overall performance.
   - Explicitly enumerates demonstrated strengths.
   - Diagnoses missing concepts and provides actionable guidance.
4. **F4: Concept Mind-Map Visualizer:**
   - Constructs a hierarchical Directed Acyclic Graph (DAG) with the assessment question as the root node.
   - Children represent syllabus concepts, color-coded by mastery status (green = demonstrated, orange = partial, gray = missing).
   - Rendered natively in React using clean, interactive SVG without external charting library bloat.

### 3.2 Key Empirical Metrics on N=150 Held-Out Test Split:
- **Mean Absolute Error (MAE):** **4.640** (vs. 5.609 for token overlap; **17.3% reduction**).
- **Tolerance Agreement ($\le 2.0$ marks):** **56.0% (84/150)** (vs. 20.7% for baseline).
- **Tolerance Agreement ($\le 15\%$ grade):** **56.0% (84/150)** (vs. 8.7% for baseline).
- **Concept Diagnosis:** Precision = **90.9%**, Recall = **98.0%**, F1 = **94.3%**.
- **Irrelevant Answer Rejection:** **100.0% (25/25)** awarded 0.0 marks (0 hallucinations).
- **Algorithmic CPU Latency:** **0.34 ms** mean in-process execution.

---

## 4. Profile of the Trainable Model Proof-of-Concept: Condition F

Condition F satisfies the PP1 assessment requirement for **trainable machine learning models**:

### 4.1 Architecture & Training Pipeline:
- **Model Type:** Supervised `GradientBoostingRegressor` ($n=100$, max depth $=3$, learning rate $=0.05$) alongside L2-regularized `Ridge` regression.
- **Dataset Splits:** Fitted exclusively on `controlled_answers_train.csv` ($N=702$ answers across $117$ questions); evaluated on held-out `controlled_answers_test.csv` ($N=150$ answers across $25$ questions). **Disjoint question ID intersection $= 0$ (zero train/test data leakage).**
- **Feature Extraction:** Pairwise TF-IDF cosine similarity between question and answer, concept hit ratio against syllabus concepts, length and character normalized ratios, sentence segmentation counts, and empty response indicators.
- **Model Persistence:** Saved to [`ai-services/c3/models/c3_scoring_regressor.joblib`](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/ai-services/c3/models/c3_scoring_regressor.joblib).
- **Evaluation Command:** `python ai-services/c3/experiments/train_semantic_model.py`.

---

## 5. Academic Defense Strategy for Examiners

The candidate will defend this decision to examiners as follows:

> *"Our research methodology follows a principled progression from unconstrained probabilistic models to hybrid deterministic-retrieval architectures. For PP1, we prioritized building a dependable, ultra-fast (0.34 ms), hallucination-free, rubric-aware prototype (**Condition E**) integrated with live MongoDB persistence and C1 event emission. Furthermore, under supervisor directive **COM-07**, we deliberately avoided presenting uncalibrated zero-shot LLM figures during this milestone to protect evaluation validity. To satisfy the PP1 model trainability requirement, we implemented a supervised semantic regression model (**Condition F proof-of-concept**) trained on the 702-answer synthetic training set and evaluated on the held-out 150-answer test set. Conditions A, B, C, and D are fully specified in `EXPERIMENT_A_TO_F_TRACEABILITY.md` and scheduled for Phase 4 dissertation completion."*

