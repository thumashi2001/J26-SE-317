# AdaptiveLearnSE Component 3 — PP1 Presentation Slide Deck Outline

**Presentation Title:** AI-Powered Automated Marking & Answer Analysis System  
**Event:** Project Performance 1 (PP1) Viva Presentation (22 October 2026)  
**Allocated Time:** 10–12 Minutes + 5 Minutes Demonstration + Q&A  
**Visual Artifacts:** Referencing screenshots in `ss/` and diagrams in `docs/pp1/component-3/`

---

## Slide 1: Title & Project Context
- **Heading:** AdaptiveLearnSE — Component 3
- **Subheading:** AI-Powered Automated Marking & Answer Analysis System
- **Key Details:**
  - Candidate Name / Registration Number: Component 3 Lead
  - Degree: B.Sc. (Hons) in Information Technology Specializing in Software Engineering
  - Department: Software Engineering, Faculty of Computing, SLIIT
  - Date: 22 October 2026
- **Speaker Note:** Introduce Component 3's role as the automated evaluation, diagnostic analysis, and feedback pillar within the AdaptiveLearnSE platform.

---

## Slide 2: Problem Statement & Research Gaps
- **Heading:** The Challenges in Automated Software Engineering Assessment
- **Key Bullet Points:**
  - **Black-Box Evaluation:** Traditional AES systems award single numbers without sentence-level justification.
  - **Generative Hallucinations:** Unconstrained LLMs award unearned marks simply because technical keywords appear.
  - **Lack of Cognitive Diagnosis:** Graders tell students *what* mark they got, but not *which specific concepts* are missing or misunderstood.
  - **Classroom Inefficiency:** Lecturers cannot easily grade entire cohorts against a single shared rubric setup.
- **Speaker Note:** Emphasize that our research addresses explainability, concept diagnosis, and real classroom usability.

---

## Slide 3: Component 3 Research Objectives & Pipeline
- **Heading:** High-Level Conceptual Pipeline
- **Visual:** Flow diagram: Student Answer → Text Normalization → Semantic Analysis → Rubric-Aware Marking → Concept Diagnosis → Explainable Feedback → Mind Map DAG → Lecturer Oversight
- **Core Research Objectives:**
  1. Rubric-aware semantic evaluation with partial credit handling.
  2. Explainable AI linking marks directly to answer sentences.
  3. Automatic synthesis of structured concept mind maps.
  4. Human-in-the-loop lecturer governance.
- **Speaker Note:** Walk through the 8 stages of the pipeline. Stress that the lecturer remains the final authoritative decision-maker.

---

## Slide 4: System Architecture & Three-Tier Implementation
- **Heading:** Modular Three-Tier Architecture
- **Visual:** Mermaid architecture diagram from `ARCHITECTURE_AND_DATA_FLOW.md`
- **Key Modules:**
  - **React Vite Frontend (Port 5173):** Batch studio wizard, review queue, interactive SVG DAG mind map.
  - **Node.js/Express Backend (Port 3000):** JWT RBAC, batch orchestration, deterministic MCQ marking, MongoDB persistence.
  - **Python FastAPI AI Service (Port 8003):** Specialized NLP, rubric validator, criterion evaluator, feedback & mind map generators.
- **Speaker Note:** Highlight our clean separation of concerns: Node handles business rules and security, Python handles AI/NLP algorithms.

---

## Slide 5: The Lecturer Batch Marking Studio Workflow
- **Heading:** Practical Classroom Workflow (4-Step Wizard)
- **Visuals:** Screenshots `ss/02_lecturer_batch_setup.png`, `ss/03_typed_answer_import.png`, `ss/04_validation_preview.png`, `ss/05_batch_marking_results.png`
- **Workflow Highlights:**
  - **Step 1:** Configure question & rubric once (saves hours of repetitive setup).
  - **Step 2:** Ingest cohort answers via CSV or dynamic grid.
  - **Step 3:** Pre-validation engine checks duplicates, empty rows, and option mismatches.
  - **Step 4:** Cohort automated grading with real-time results table.
- **Speaker Note:** Point out how the pre-validation engine isolates errors and prevents duplicate grading.

---

## Slide 6: Explainability, Evidence Linking & Concept Mind Maps
- **Heading:** Transparent Evidence & Cognitive Diagnostics
- **Visuals:** Screenshots `ss/06_criterion_evidence_feedback.png` and `ss/07_concept_mind_map.png`
- **Key Features:**
  - **Criterion Breakdown Cards:** Exact scoring level selected (`L0`–`Ln`) with sentence IDs.
  - **Concept Diagnosis:** Demonstrated concepts (green), partial (yellow), missing (red).
  - **Interactive Mind Map Graph:** Directed acyclic graph rooted at the question, illustrating the student's cognitive model.
- **Speaker Note:** Show how a student or lecturer can click any criterion and see the exact sentences that justified the mark.

---

## Slide 7: Lecturer Review, Override & Audit Governance
- **Heading:** Human-in-the-Loop Oversight
- **Visuals:** Screenshot `ss/08_lecturer_override_reason.png` and `ss/09_finalized_results.png`
- **Governance Mechanisms:**
  - AI proposed marks start in `pending_review`.
  - Override requires mandatory written justification (`override_reason`).
  - Original AI mark is permanently preserved in `automated_mark`.
  - Complete audit trail with timestamps and reviewer IDs.
  - Finalization locks records and emits idempotent event to Component 1 (`learning_events`).
- **Speaker Note:** Reiterate compliance with university grading regulations.

---

## Slide 8: Research Benchmark Dataset
- **Heading:** Canonical Synthetic Dataset (C3-Phase3-v5-FINAL)
- **Key Characteristics:**
  - 167 Questions across SE3010–SE3040 curriculum.
  - 1,002 Controlled synthetic answers (6 quality variants per question).
  - 117 Train / 25 Validation / 25 Test split (zero leakage).
  - Quality conditions: FULL, MOSTLY_CORRECT, PARTIAL, MISSING_CONCEPT, MISCONCEPTION, IRRELEVANT.
  - Ethical disclosure: Controlled synthetic research stimulus; no authentic student submissions used.
- **Speaker Note:** Explain why synthetic data was ethically and scientifically superior for this milestone.

---

## Slide 9: Quantitative Evaluation Results
- **Heading:** Empirical Benchmark Evaluation Findings (Test Split, N=150)
- **Visual:** Screenshot `ss/12_evaluation_results.png`
- **Key Metrics Table:**
  - **Rubric-Aware Marking MAE:** **4.640** (vs 5.609 for token-overlap baseline → **17.3% error reduction**).
  - **Pearson Correlation (r):** **0.7243** (Strong agreement with ground truth).
  - **Concept Diagnosis F1:** **94.3%** (Precision: 90.9%, Recall: 98.0%).
  - **Irrelevant Answer Rejection:** **100%** awarded 0 marks without hallucinated credit.
  - **Marking Latency:** **0.37 ms** mean per submission.
- **Speaker Note:** Walk through the metrics. Highlight that C3 strictly rejects irrelevant answers while baselines over-award marks.

---

## Slide 10: Comprehensive Testing & Verification
- **Heading:** Rigorous Multi-Tier Automated Verification
- **Visual:** Screenshot `ss/11_test_results.png`
- **Results Summary:**
  - Backend Integration Tests: **41 / 41 Passed** (514 ms)
  - Python AI Engine Tests: **99 / 99 Passed** (1.18 s)
  - Synthetic Dataset Loader Tests: **12 / 12 Passed** (120 ms)
  - Frontend Production Build: **106 modules, 0 errors** (6.39 s)
  - **Total:** **140 automated tests passing (100% green)**
- **Speaker Note:** Emphasize that all claimed functionality is backed by executable tests.

---

## Slide 11: Future Roadmap & Post-PP1 Research Conditions
- **Heading:** Project Trajectory for Final Viva
- **Conditions A–F Progression:**
  - Phase 3 (Current / PP1): Condition E (Deterministic Concept Evidence + Rubric) — **COMPLETED**.
  - Phase 4 (Post-PP1): Condition C (Vector-RAG) and Condition D (GraphRAG using Neo4j CCKG).
  - Phase 5: Condition F (Full Multimodal Ensemble) & longitudinal lecturer usability trial.
- **Scope Preservations:** Scanned answers / OCR remains excluded to maintain research focus.

---

## Slide 12: Conclusion & Demonstration Transition
- **Heading:** Summary of Achievements
- **Summary Points:**
  - Robust, explainable, and rubric-bounded automated assessment prototype.
  - Functional batch marking studio solving real university grading bottlenecks.
  - Zero hallucinations, strict lecturer governance, sub-millisecond latency.
  - 140 passing tests, reproducible evaluation, and complete documentation.
- **Speaker Note:** Conclude presentation and transition smoothly into the live system demonstration.
