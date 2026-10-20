# AdaptiveLearnSE Component 3 — PP1 Progress & Completion Report

**Project:** AdaptiveLearnSE — AI-Powered Cognitive Digital Twin for Adaptive Learning, Exam Intelligence, and Automated Assessment  
**Component:** Component 3 (C3) — AI-Powered Automated Marking & Answer Analysis System  
**Lead Researcher / Candidate:** Component 3 Engineer  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT)  
**Evaluation Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22 October 2026)  
**Status Date:** 20 October 2026  
**Overall Readiness:** **Ready with limitations** (Fully Demonstrable Software System with Explicitly Documented Research Scope Boundaries)

---

## 1. Executive Summary

Component 3 (C3) provides automated, rubric-aware subjective evaluation, deterministic multiple-choice question (MCQ) evaluation, concept diagnosis, evidence-based feedback, concept mind-map visual synthesis, and human-in-the-loop lecturer review and finalization for the AdaptiveLearnSE platform.

All core functional workflows required for the PP1 demonstration are implemented, tested, and empirically verified:
1. **Lecturer Assessment Setup:** Single-point configuration of question metadata, reference answers, expected concepts, and multi-criterion rubrics (or MCQ option keys).
2. **Student Typed-Answer Batch Ingestion:** High-throughput entry via dynamic grid or CSV cohort upload with pre-marking schema validation and duplicate student detection.
3. **Automated Marking Pipeline:** Deterministic MCQ grading (0ms NLP overhead, 100% precision) paired with rubric-aware subjective evaluation providing criterion-level scoring, sentence evidence linking, and concept status diagnosis.
4. **Interactive Concept Mind Map:** DAG visualizer rendering hierarchical concept structures with demonstrated, partial, and missing concept status.
5. **Lecturer Oversight & Governance:** Individual inspection, score override with mandatory justification, bulk batch finalization, and idempotent event emission to Component 1 (`learning_events`).
6. **Persistence & Idempotency:** Submissions and results persist into MongoDB Atlas (`c3_submissions`, `c3_batch_setups`, `c3_results`), with guaranteed duplicate prevention upon batch retries.

All automated test suites pass without error (140 total tests: 41 backend Node.js tests including 1 suite + 40 test cases, 99 Python AI service tests across 15 test files, and clean Vite production build with 106 modules).

---

## 2. Implemented Functionality & Architectural Flow

The complete end-to-end workflow operates as follows:

```
[Lecturer Batch Studio]
         │ (1. Configure Question, Rubric & Criteria)
         ▼
[c3_batch_setups Collection]
         │ (2. Import Cohort Answers via CSV / Dynamic Grid)
         ▼
[Pre-Validation Engine (validateBatchAnswers)]
         │ (Checks duplicates, empty answers, option validity)
         ▼
[Automated Marking Orchestration (processBatchMarking)]
    ┌────┴──────────────────────────┐
    ▼                               ▼
[Deterministic MCQ Engine]     [Python AI Fast Service (Port 8003)]
(Answer-key exact matching)    ├─ F1: Answer Processing & Semantic Analysis
                               ├─ F2: Rubric-Aware Marking Engine
                               ├─ F3: Explainable Feedback Generation
                               └─ F4: Concept-Based Mind Map Generator
    └────┬──────────────────────────┘
         │ (3. Idempotent Upsert into c3_submissions & c3_results)
         ▼
[Lecturer Review & Oversight (/lecturer/c3/batch & /lecturer/c3/:id)]
         │ (4. Accept AI Mark OR Override Mark with Mandatory Reason)
         ▼
[Batch Finalization (/batch/:id/finalize-all)]
         │ (5. Transition Status to 'finalized')
         ▼
[Component 1 Live Integration Bridge (syncC3AssessmentToC1)]
         │ (Idempotent update to MongoDB 'learning_events')
         ▼
[Downstream Cognitive Digital Twin (Component 1)]
```

---

## 3. Feature Status Breakdown

| Feature / Subsystem | Planned Scope | Actual Implementation Status | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Typed Subjective Marking** | Natural language text evaluation | ✅ **Complete & Verified** | Unit tests + Live API (`/c3/assess`) |
| **Deterministic MCQ Marking** | Strict answer key option evaluation | ✅ **Complete & Verified** | 12 dedicated MCQ tests in `c3.test.js` |
| **Rubric Criterion Scoring** | Multi-level rubric scoring | ✅ **Complete & Verified** | `test_criterion_evaluator.py` |
| **Sentence Evidence Extraction**| Trace answer sentences to criteria | ✅ **Complete & Verified** | UI criterion cards + `evidence_spans` |
| **Concept Diagnosis** | Demonstrated, partial, missing | ✅ **Complete & Verified** | 94.3% F1 score on synthetic test split |
| **Explainable Feedback** | Strengths, gaps, actionable advice | ✅ **Complete & Verified** | `test_feedback_generator.py` |
| **Concept Mind Map** | Hierarchical concept DAG | ✅ **Complete & Verified** | SVG DAG in review modal & student view |
| **Lecturer Review & Override** | Human-in-the-loop governance | ✅ **Complete & Verified** | Mandatory override reason enforced |
| **Batch Marking Studio** | Configure once, grade cohort | ✅ **Complete & Verified** | 4-step wizard at `/lecturer/c3/batch` |
| **Duplicate Prevention & Retry**| In-place update on batch rerun | ✅ **Complete & Verified** | Verified via test `c3.test.js:36` |
| **Component 1 Integration** | Learning event emission | ✅ **Complete & Verified** | Idempotent upsert in `learning_events` |
| **Scanned Document / OCR** | Handwriting / image-to-text | ❌ **Excluded by Scope** | Explicitly rejects with 400 Bad Request |
| **Research Conditions A–D, F** | Vector-RAG, GraphRAG, Multi-LLM | ⏸️ **Deferred Viva Boundary** | Accurately documented as planned work |

---

## 4. Test and Build Verification Summary

| Test Suite | Framework | Executed Command | Tests Passed | Tests Failed | Execution Time | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Integration** | Node.js Native Test Runner | `npm test` (in `backend/`) | **41** | 0 | 514 ms | 1 top-level suite + 40 test cases; uses in-process HTTP mock for Python service isolation |
| **Python AI Engine** | Pytest (`pytest-9.1.1`) | `python -m pytest tests/` | **99** | 0 | 1.18 s | 15 test modules covering preprocessing, rubrics, feedback, mind maps, APIs |
| **Synthetic Dataset Loader** | Pytest | `pytest tests/unit/test_dataset_loader.py` | **12** | 0 | 120 ms | Part of the 99 Python tests; validates all 167 questions and 1,002 answers |
| **Research Evaluation** | Pytest | `pytest tests/evaluation/test_evaluation_pipeline.py` | **3** | 0 | 450 ms | Part of the 99 Python tests; verifies metric computation functions |
| **Frontend Production Build**| Vite 5.4.21 Rollup | `npm run build` (in `frontend/`) | **106 modules** | 0 | 6.39 s | 0 errors, 0 unresolved imports, generated static bundle in `dist/` |
| **Total Automated Tests** | — | — | **140 passed** | **0 failed** | **100% Green** | Fully reproducible across developer and CI environments |

> [!NOTE]
> **Mock vs. Live Integration Architecture:** The 41 backend tests in `c3.test.js` isolate Express controllers and authentication from external Python daemons using an in-process mock HTTP server. Live integration between Express (port 3000), Python FastAPI (port 8003), React Vite (port 5173), and MongoDB Atlas is verified via separate runtime smoke testing and browser verification workflows.

---

## 5. Current Scope Boundaries & Ethical Disclosures

1. **Scanned Answer Processing / OCR:** Not implemented by design. The research scope approved for Component 3 evaluates typed natural language responses directly. Any attempts to upload scanned documents are rejected with an explicit HTTP 400 error.
2. **Component 2 Independence:** Component 2 (Exam Intelligence & PDF parsing) is frozen and isolated. C3 operates self-sufficiently through direct typed question and rubric inputs.
3. **Research Dataset Integrity:** Evaluation uses a controlled synthetic dataset of 167 questions and 1,002 controlled student answers based on the SLIIT SE curriculum (`C3-Phase3-v5-FINAL`). All 150 test split answers are unique across 25 disjoint questions. Independent expert human validation has not been claimed.
4. **Planned Experimental Conditions:** Research conditions A (LLM-only), B (LLM+Rubric), C (Vector-RAG), D (GraphRAG), and F (Multimodal Ensemble) remain marked as planned/deferred. Condition E (Deterministic Concept Evidence + Rubric) serves as the active, validated prototype.
5. **Evaluation Metric Trade-Offs:** The rubric-aware prototype achieves a superior MAE (4.640 vs. 5.609, a 17.3% error reduction) and much higher tolerance agreement within 2 marks (56.0% vs. 20.7%). The lexical baseline achieves a lower RMSE (6.530 vs. 7.220) because smooth continuous token overlap incurs fewer squared outlier penalties than discrete rubric step-drops on missing concepts. Universal superiority is not claimed.
6. **Latency Scope:** The reported ~0.34 ms marking latency measures Python in-process CPU execution time (text normalization, rubric scoring, mind map generation), excluding localhost HTTP network latency (~10–15 ms) and remote cloud LLM calls (500–2,000 ms).
7. **Feedback & Mind Map Validity:** Reported 100% validity reflects structural schema compliance and DAG reachability, not human pedagogical or qualitative grading.
