# AdaptiveLearnSE Component 3 — Claim, Evidence & Decision Log

**Document Version:** 2.0.0  
**Project:** AdaptiveLearnSE — Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Standard:** Structured Decision Architecture Log (ADR / CED Framework)  

---

## 1. Architectural & Engineering Decisions

### DEC-01: Separation of Deterministic MCQ from Subjective Generative/NLP Evaluation
- **Decision:** Implement MCQ evaluation natively in Node.js via an authoritative answer-key comparison engine (`mcqMarkingService.js`), completely isolated from the Python NLP service.
- **Why:** Multiple-choice questions have single or discrete multi-select correct answers. Passing them to an NLP model or LLM introduces non-deterministic latency, monetary cost, and the risk of hallucinated justifications.
- **Alternatives Compared:** 
  1. *Prompting an LLM with the MCQ options and key:* Rejected due to token cost and latency.
  2. *Evaluating MCQs inside Python FastAPI:* Rejected to keep objective grading decoupled from heavy NLP dependencies.
- **Evidence:** 12 automated unit tests in `c3.test.js:22-33` execute in < 30 ms with 100% deterministic accuracy.
- **Status:** **VERIFIED FACT (Implemented & Active)**

---

### DEC-02: Human-in-the-Loop Governance & Mandatory Override Reason
- **Decision:** All AI automated evaluations enter MongoDB with status `pending_review` (AI Proposed). Finalization requires lecturer sign-off. Any mark adjustment requires a mandatory string justification (`override_reason`).
- **Why:** University grading policies mandate that final marks are awarded under certified lecturer authority. Fully autonomous AI grading violates academic accountability.
- **Alternatives Compared:**
  1. *Autonomous direct finalization:* Rejected due to regulatory and academic governance non-compliance.
  2. *Optional override comments:* Rejected because lack of required justification compromises audit traceability.
- **Evidence:** Backend test `c3.test.js:13` verifies rejection (HTTP 400) when an override reason is omitted. Test `c3.test.js:14` verifies score preservation.
- **Status:** **VERIFIED FACT (Implemented & Active)**

---

### DEC-03: Single Shared Assessment Setup for Cohort Batch Marking
- **Decision:** Provide a 4-step wizard allowing a lecturer to configure one question, rubric, and maximum marks once, and evaluate a cohort of student answers against that shared setup.
- **Why:** Requiring lecturers to input the question text, criteria, and weights for each individual student creates unsustainable overhead in practical university settings.
- **Alternatives Compared:**
  1. *Individual assessment submission per student:* Retained for student practice sandbox, but unsuitable for class cohorts.
  2. *Independent batch microservice:* Rejected to avoid architectural fragmentation; implemented modularly within the existing backend.
- **Evidence:** Tested with 7-student synthetic cohort in `c3.test.js:33-40` and live verified via browser subagent (`ss/02_lecturer_batch_setup.png` to `ss/05_batch_marking_results.png`).
- **Status:** **VERIFIED FACT (Implemented & Active)**

---

### DEC-04: Idempotent Batch Processing & Duplicate Student Prevention
- **Decision:** Implement pre-validation duplicate detection and database-level upserts on compound key `(student_id, batch_id)`.
- **Why:** Network interruptions or accidental double-clicks by a lecturer could re-submit a batch, leading to duplicated database records, skewed class averages, and duplicate C1 learning events.
- **Alternatives Compared:**
  1. *Appending all submissions with timestamp:* Rejected due to duplicate rows.
  2. *Failing the entire batch if one duplicate exists:* Rejected as poor UX; instead, valid rows are marked and duplicates are flagged in preview.
- **Evidence:** Test `c3.test.js:38` explicitly tests retrying a batch and confirms in-place updates with zero duplicate documents.
- **Status:** **VERIFIED FACT (Implemented & Active)**

---

### DEC-05: Exclusion of OCR and Handwritten Document Ingestion
- **Decision:** Explicitly exclude Optical Character Recognition (OCR), handwritten scanned document ingestion, and image-to-text processing from Component 3 scope. Reject image payloads with HTTP 400.
- **Why:** The approved research scope for Component 3 focuses on semantic evaluation, rubric scoring, evidence tracing, and mind mapping of natural language text. Computer vision and handwriting recognition are distinct research fields that dilute core NLP contributions.
- **Alternatives Compared:**
  1. *Adding Tesseract.js / EasyOCR:* Rejected due to OCR error propagation confounding marking accuracy evaluations.
- **Evidence:** `routes/index.js:31-32` and `c3Controller.js:50-56` explicitly return HTTP 400; verified in `c3.test.js:16-17`.
- **Status:** **VERIFIED FACT (Implemented & Active)**

---

## 2. Research & Evaluation Decisions

### DEC-06: Controlled Synthetic Dataset vs Public Benchmark Datasets
- **Decision:** Evaluate Component 3 on a controlled synthetic dataset (167 questions, 1,002 answers, 6 quality variants) constructed from SLIIT SE module syllabi (SE3010–SE3040), rather than public datasets (ASAP, Mohler).
- **Why:** Protects against benchmark leakage, aligns with the actual degree curriculum, and guarantees controlled distribution across full, partial, missing, and irrelevant response types.
- **Alternatives Compared:**
  1. *Public ASAP Kaggle dataset:* Out of domain (middle school essays, not Software Engineering).
  2. *Authentic student exam papers:* Prohibited prior to formal institutional ethics clearance.
- **Evidence:** Verified by 12 dataset loader tests in `test_dataset_loader.py` and documented in `07_DATASET_README.md`.
- **Status:** **VERIFIED FACT (Implemented & Active)**

---

### DEC-07: Authoritative PP1 Status of Research Conditions A–F
- **Decision:** Implement and empirically evaluate Condition E (Deterministic Concept Evidence + Rubric) as the primary explainable prototype, and Condition F (Supervised Gradient Boosted Regressor) as a trained model feasibility demonstration for PP1. Conditions A & B are restricted per supervisor directive COM-07 (prohibiting uncalibrated zero-shot LLM claims); Condition C is deferred to Phase 4 (lecture slide embeddings); Condition D is blocked by unpopulated external CCKG Neo4j schemas.
- **Why:** Upholds strict academic honesty and supervisor directives.
- **Evidence:** `docs/pp1/EXPERIMENT_A_TO_F_TRACEABILITY.md` and `docs/pp1/FINAL_PP1_REQUIREMENTS_AND_EVIDENCE_MATRIX.md`.
- **Status:** **VERIFIED FACT & AUTHORITATIVE PP1 BOUNDARY**

---

### DEC-08: Correction of Length Bias in Supervised Scoring Model (Condition F)
- **Decision:** Reject initial Condition F model (v1.0.0) after feature importance inspection revealed `word_count` (68.14%) drove predictions, causing it to award 9.99/10 marks to out-of-domain historical text. Implement corrected model (v2.0.0) removing raw unnormalized length, introducing pairwise TF-IDF reference similarity (35.42% importance), and enforcing semantic gating.
- **Why:** Prevents student gaming via length inflation and restores 100% irrelevant distractor rejection (0.00 marks).
- **Evidence:** Documented in `ai-services/c3/experiments/train_semantic_model_corrected.py`, `results/trainable_model_summary_corrected.json`, and `results/diagnostic_suite_results.json`.
- **Status:** **VERIFIED FACT & EMPIRICAL CONTRIBUTION**

