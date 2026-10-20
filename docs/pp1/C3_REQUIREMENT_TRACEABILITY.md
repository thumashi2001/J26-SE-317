# AdaptiveLearnSE Component 3 — Requirement Traceability Matrix
**Project:** AdaptiveLearnSE | **Component:** C3 (Automated Marking & Answer Analysis)  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Document Version:** 2.0.0 (PP1 Final Verified)

---

## 1. Traceability Overview

This matrix maps every approved objective and scope item from the Component 3 Research Proposal and Technical Assessment Framework (TAF) to the concrete source code files, automated test suites, verification commands, and reproducible evidence artifacts.

```
Proposal Objective / Scope
       │
       ▼
System Requirement (C3-REQ-xx)
       │
       ▼
Implementation Files (Frontend / Backend / AI-Services)
       │
       ▼
Test Files & Execution Commands
       │
       ▼
Evidence Artifacts & Result CSVs
```

---

## 2. Master Requirement Traceability Matrix

| Requirement ID | Proposal / TAF Objective | Functional Specification | Source Implementation Files | Automated Test Files | Exact Test Command | Evidence Status & Artifacts |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **C3-REQ-01** | Student & Lecturer Role Security | Enforce JWT authentication, extract student ID from `req.user.sub`, prevent cross-student spoofing, restrict review to lecturers. | `backend/src/middleware/auth.js`<br>`backend/src/modules/c3/controllers/c3Controller.js`<br>`frontend/src/context/AuthContext.jsx` | `backend/src/modules/c3/tests/c3.test.js` | `cd backend && npm test` | **COMPLETE**<br>Passes tests 1–6, 10–11 in `c3.test.js`. |
| **C3-REQ-02** | Subjective Answer Processing | Accept typed student answers for short/essay questions with validation against length limits and empty inputs. | `backend/src/modules/c3/services/c3Service.js`<br>`frontend/src/pages/c3/StudentAssessmentPage.jsx` | `backend/src/modules/c3/tests/c3.test.js`<br>`tests/integration/test_assessment_api.py` | `npm test`<br>`pytest tests/integration/` | **COMPLETE**<br>150 answers processed in benchmark suite. |
| **C3-REQ-03** | Deterministic MCQ Marking | Evaluate single and multi-select MCQs deterministically against key without invoking LLM or incurring non-determinism. | `backend/src/modules/c3/services/mcqMarkingService.js`<br>`frontend/src/pages/c3/MCQAssessmentPage.jsx` | `backend/src/modules/c3/tests/c3.test.js` (MCQ Suite) | `npm test` | **COMPLETE**<br>11 dedicated MCQ tests pass (tests 22–32). |
| **C3-REQ-04** | Criterion-Level Rubric Marking | Evaluate answers against multi-criterion rubrics, ensuring marks are strictly bounded within criterion limits. | `ai-services/c3/services/marking/criterion_evaluator.py`<br>`ai-services/c3/services/assessment/orchestrator.py` | `tests/unit/test_criterion_evaluator.py`<br>`tests/unit/test_marking_engine.py` | `pytest tests/unit/test_criterion_evaluator.py` | **COMPLETE**<br>MAE 4.640 vs Baseline 5.609 on test split. |
| **C3-REQ-05** | Concept Analysis & Diagnosis | Detect demonstrated, partially demonstrated, and missing concepts from submitted answers. | `ai-services/c3/services/analysis/concept_extractor.py`<br>`ai-services/c3/services/analysis/evaluator.py` | `tests/unit/test_feedback_generator.py`<br>`tests/evaluation/test_evaluation_pipeline.py` | `pytest tests/evaluation/` | **COMPLETE**<br>Precision: 90.9%, Recall: 98.0%, F1: 94.3%. |
| **C3-REQ-06** | Explainable Feedback Generation | Generate formative feedback with evidence quotes tied to the submitted answer and rubric criteria. | `ai-services/c3/services/feedback/generator.py`<br>`ai-services/c3/app/routes/feedback.py` | `tests/unit/test_feedback_generator.py`<br>`tests/integration/test_feedback_api.py` | `pytest tests/unit/test_feedback_generator.py` | **COMPLETE**<br>100.0% structural validity rate across N=150. |
| **C3-REQ-07** | Answer-Derived Concept Mind Map | Generate a valid Directed Acyclic Graph (DAG) visualizing demonstrated and missing concepts. | `ai-services/c3/services/mindmap/generator.py`<br>`frontend/src/components/c3/MindMapViewer.jsx` | `tests/unit/test_mindmap_generator.py`<br>`tests/integration/test_mindmap_api.py` | `pytest tests/unit/test_mindmap_generator.py` | **COMPLETE**<br>100.0% DAG structural validity rate. |
| **C3-REQ-08** | Lecturer Review & Mark Override | Provide authorized interface for reviewing AI marks, overriding criterion scores with audit justification, and finalization. | `backend/src/modules/c3/controllers/c3Controller.js`<br>`frontend/src/pages/c3/LecturerReviewPage.jsx` | `backend/src/modules/c3/tests/c3.test.js` | `npm test` | **COMPLETE**<br>Preserves original AI mark and override history. |
| **C3-REQ-09** | Batch Marking Workflow | Enable lecturers to upload student submissions in bulk, mark against a shared rubric, and finalize the batch. | `backend/src/modules/c3/services/batchMarkingService.js`<br>`frontend/src/pages/c3/BatchMarkingPage.jsx` | `backend/src/modules/c3/tests/c3.test.js` (Batch Suite) | `npm test` | **COMPLETE**<br>8 batch test cases passing (tests 33–40). |
| **C3-REQ-10** | C1 Learner-Model Integration | Dispatch provisional and finalized assessment events to Component 1 (Cognitive Digital Twin) with idempotency. | `backend/src/modules/c3/services/c1IntegrationService.js`<br>`backend/src/modules/c3/models/C3Submission.js` | `backend/src/modules/c3/tests/c3.test.js` (C1 Bridge) | `npm test` | **COMPLETE**<br>4 integration tests pass (tests 18–21). |
| **C3-REQ-11** | Shared CCKG Foundation | Define shared curriculum knowledge graph schema, uniqueness constraints, and seed Cypher for SLIIT SE modules. | `database/neo4j/schema/01_cckg_constraints.cypher`<br>`database/neo4j/cypher/01_seed_curriculum_ontology.cypher`<br>`ai-services/c3/services/cckg/graph_adapter.py` | `tests/unit/test_cckg_and_rag.py` | `pytest tests/unit/test_cckg_and_rag.py` | **COMPLETE**<br>GraphAdapter supports live Neo4j + offline fallback. |
| **C3-REQ-12** | Vector RAG Retrieval | Build local vector index over authorized course lecture materials and retrieve relevant passages with citations. | `ai-services/c3/services/rag/vector_store.py`<br>`ai-services/c3/experiments/rag/exp3_vector_rag.py` | `tests/unit/test_cckg_and_rag.py` | `pytest tests/unit/test_cckg_and_rag.py` | **COMPLETE**<br>Indexes SE3010–SE3040 course documents. |
| **C3-REQ-13** | GraphRAG Knowledge Grounding | Traverse CCKG prerequisite paths and concept relationships to ground rubric evaluation in curriculum ontology. | `ai-services/c3/services/cckg/graph_adapter.py`<br>`ai-services/c3/experiments/rag/exp4_graph_rag.py` | `tests/unit/test_cckg_and_rag.py` | `pytest tests/unit/test_cckg_and_rag.py` | **COMPLETE**<br>Prerequisite closure traversal verified. |
| **C3-REQ-14** | Provider-Neutral LLM Engine | Implement provider-neutral interface supporting configurable models (OpenAI, Local Ollama, Mock) with safe errors. | `ai-services/c3/services/llm/base.py`<br>`ai-services/c3/services/llm/mock_provider.py`<br>`ai-services/c3/services/llm/factory.py` | `tests/unit/test_llm_providers.py` | `pytest tests/unit/test_llm_providers.py` | **COMPLETE**<br>Zero-cost mock default; no leaked API keys. |
| **C3-REQ-15** | Multi-LLM Benchmark | Execute comparative evaluation across candidate LLM architectures under identical held-out test conditions. | `ai-services/c3/experiments/llm/exp5_multi_llm_comparison.py`<br>`ai-services/c3/experiments/run_all_experiments.py` | `ai-services/c3/experiments/run_all_experiments.py` | `python ai-services/c3/experiments/run_all_experiments.py` | **COMPLETE**<br>Output saved in `exp5_multi_llm_summary.json`. |
| **C3-REQ-16** | Trainable Model & Bias Correction | Correct length bias in supervised scoring regressor, eliminate word count exploitation, reject out-of-domain text. | `ai-services/c3/experiments/train_semantic_model_corrected.py`<br>`ai-services/c3/experiments/run_model_diagnostics.py` | `ai-services/c3/experiments/run_model_diagnostics.py` | `python ai-services/c3/experiments/run_model_diagnostics.py` | **COMPLETE**<br>Distractor receives 0.00/10.0 marks (PASS). |
| **C3-REQ-17** | Synthetic Dataset Governance | Maintain question-level train/val/test splits, verify zero question leakage, validate reference labels. | `ai-services/c3/datasets/synthetic/`<br>`ai-services/c3/datasets/loader.py` | `tests/unit/test_dataset_loader.py` | `pytest tests/unit/test_dataset_loader.py` | **COMPLETE**<br>12 dataset tests pass; zero question leakage. |

---

## 3. Verification Command Summary

All tests are verified and can be re-run at any time using the documented project commands:

```bash
# 1. Node.js Backend Integration Test Suite (41 tests)
cd ADAPTIVE_LEARN_SE/backend
npm test

# 2. Python AI Services Unit & Integration Test Suite (119 tests)
cd ADAPTIVE_LEARN_SE/ai-services/c3
& "..\..\..\.venv\Scripts\python.exe" -m pytest tests/

# 3. Master Research Experiment Matrix Runner (All 7 Suites)
cd ADAPTIVE_LEARN_SE
..\.venv\Scripts\python.exe ai-services/c3/experiments/run_all_experiments.py

# 4. Frontend Production Build Verification (112 modules)
cd ADAPTIVE_LEARN_SE/frontend
npm run build
```
