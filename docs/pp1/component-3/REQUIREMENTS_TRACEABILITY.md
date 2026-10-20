# AdaptiveLearnSE Component 3 — Requirements Traceability Matrix (RTM)

**Project:** AdaptiveLearnSE — Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Milestone:** PP1 Viva (22 October 2026)  
**Standard:** ISO/IEC/IEEE 29148 Traceability Standard

---

## Traceability Matrix

| Req ID | Requirement Description | Implementation Location | Verification Evidence | Status | Remaining Gap / Planned Evolution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-C3-01** | Student typed subjective answer submission | `backend/src/modules/c3/controllers/c3Controller.js:assessAnswer`<br>`frontend/src/pages/c3/AssessmentPage.jsx` | `c3.test.js:14`<br>`ss/10_student_result_view.png` | ✅ **Complete** | None for PP1. |
| **REQ-C3-02** | Explicit rejection of scanned/handwritten documents | `backend/src/modules/c3/controllers/c3Controller.js:unsupportedOcrHandler`<br>`backend/src/modules/c3/routes/index.js:31-32` | `c3.test.js:16-17` | ✅ **Complete** | OCR intentionally out of research scope. |
| **REQ-C3-03** | Semantic answer processing & text normalization | `ai-services/c3/services/preprocessing/text_normalizer.py`<br>`ai-services/c3/services/semantic/analyzer.py` | `test_preprocessing.py`<br>`test_semantic_baseline.py` | ✅ **Complete** | Current prototype uses deterministic token normalization; neural embeddings planned in Condition C. |
| **REQ-C3-04** | Multi-criterion rubric-aware marking | `ai-services/c3/services/marking/criterion_evaluator.py`<br>`ai-services/c3/services/marking/rubric_validator.py` | `test_criterion_evaluator.py`<br>`test_rubric_validator.py` | ✅ **Complete** | Supports scoring levels, required concepts, and proportional constraints. |
| **REQ-C3-05** | Deterministic MCQ marking against answer key | `backend/src/modules/c3/services/mcqMarkingService.js`<br>`backend/src/modules/c3/controllers/c3Controller.js:markAnswer` | `c3.test.js:22-33` | ✅ **Complete** | Authoritative answer key match in 0ms without generative hallucinations. |
| **REQ-C3-06** | Sentence-level evidence extraction | `ai-services/c3/services/marking/criterion_evaluator.py:_level_evidence`<br>`frontend/src/pages/c3/components/CriterionCard.jsx` | `test_criterion_evaluator.py:10`<br>`ss/06_criterion_evidence_feedback.png` | ✅ **Complete** | Extracts exact sentence IDs providing supporting evidence. |
| **REQ-C3-07** | Concept-level diagnosis (demonstrated, partial, missing) | `ai-services/c3/services/semantic/analyzer.py:_match_concepts`<br>`frontend/src/pages/c3/components/ConceptDiagnosis.jsx` | `test_analysis_api.py`<br>`ss/07_concept_mind_map.png` | ✅ **Complete** | 94.3% F1 score on synthetic benchmark test split. |
| **REQ-C3-08** | Explainable feedback generation | `ai-services/c3/services/feedback/generator.py`<br>`ai-services/c3/services/feedback/explanation_builder.py` | `test_feedback_generator.py`<br>`ss/06_criterion_evidence_feedback.png` | ✅ **Complete** | Generates strengths, missing concepts, and actionable improvement suggestions. |
| **REQ-C3-09** | Concept mind-map DAG generation | `ai-services/c3/services/mindmap/generator.py`<br>`frontend/src/pages/c3/components/MindMapGraph.jsx` | `test_mindmap_generator.py`<br>`ss/07_concept_mind_map.png` | ✅ **Complete** | Interactive SVG DAG visualizing concept connectivity. |
| **REQ-C3-10** | Lecturer Batch Marking Studio | `backend/src/modules/c3/services/batchMarkingService.js`<br>`frontend/src/pages/c3/LecturerBatchMarkingPage.jsx` | `c3.test.js:33-40`<br>`ss/02_lecturer_batch_setup.png` | ✅ **Complete** | Configure question & rubric once; mark cohort automatically. |
| **REQ-C3-11** | Cohort pre-validation & duplicate detection | `backend/src/modules/c3/services/batchMarkingService.js:validateBatchAnswers` | `c3.test.js:36`<br>`ss/04_validation_preview.png` | ✅ **Complete** | Detects duplicate students, empty rows, and option mismatches. |
| **REQ-C3-12** | Human-in-the-loop review & mandatory override reason | `backend/src/modules/c3/services/submissionService.js:reviewSubmission`<br>`frontend/src/pages/c3/LecturerReviewPage.jsx` | `c3.test.js:13-14`<br>`ss/08_lecturer_override_reason.png` | ✅ **Complete** | Rejecting overrides without reason; preserves original AI mark. |
| **REQ-C3-13** | Batch and individual finalization | `backend/src/modules/c3/services/batchMarkingService.js:finalizeBatchSubmissions`<br>`backend/src/modules/c3/services/submissionService.js:finalizeSubmission` | `c3.test.js:15,40`<br>`ss/09_finalized_results.png` | ✅ **Complete** | Transitions state to finalized; locks results from accidental edits. |
| **REQ-C3-14** | Database persistence & retry idempotency | `backend/src/modules/c3/services/submissionService.js`<br>`backend/src/modules/c3/services/batchMarkingService.js` | `c3.test.js:38`<br>MongoDB Collections | ✅ **Complete** | Re-running a batch updates records in-place without duplicating documents. |
| **REQ-C3-15** | Role-based access control (RBAC) | `backend/src/middleware/auth.js:requireRole`<br>`backend/src/modules/c3/routes/index.js` | `c3.test.js:1-5,10-11,33` | ✅ **Complete** | Students blocked (403) from review, setup, batch, and finalize endpoints. |
| **REQ-C3-16** | Component 1 Live Integration Bridge | `backend/src/integration/c3-c1/index.js:syncC3AssessmentToC1` | `c3.test.js:18-21` | ✅ **Complete** | Synchronizes provisional and finalized events idempotently to `learning_events`. |
| **REQ-C3-17** | Research synthetic dataset & loader | `ai-services/c3/datasets/synthetic/`<br>`ai-services/c3/datasets/loader.py` | `test_dataset_loader.py:1-12` | ✅ **Complete** | 167 questions / 1,002 answers; train/val/test splits; no public benchmark leakage. |
| **REQ-C3-18** | Benchmark evaluation pipeline | `ai-services/c3/experiments/run_evaluation.py` | `test_evaluation_pipeline.py`<br>`ss/12_evaluation_results.png` | ✅ **Complete** | Measures MAE, RMSE, Pearson r, concept F1, latency on test split. |
| **REQ-C3-19** | Conditions A–D, F (Vector RAG, GraphRAG, Ensemble) | `ai-services/c3/experiments/` | Documented in `DATASET_AND_EVALUATION_REPORT.md` | ⏸️ **Deferred** | Planned research conditions for Post-PP1 Phase 4. |
