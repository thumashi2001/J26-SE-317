# AdaptiveLearnSE Component 3 — Technical Code Walkthrough & Defense Guide

**Document Version:** 2.0.0 (Authoritative Technical Defense Guide)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Candidate Preparation:** Core Code Segments to Master for the Viva  

---

## 1. Overview of Key Architectural Modules

During the viva voce, the examiners will ask you to open specific files, explain how the algorithms work, defend design choices, and explain what happens when parameters or rules change.

This guide provides deep technical breakdowns for the **5 most critical code segments** in Component 3:
1. **Segment 1:** Shared Assessment Setup & Batch Marking Orchestrator (`batchMarkingService.js`)
2. **Segment 2:** Deterministic Multiple-Choice Question Marking Engine (`mcqMarkingService.js`)
3. **Segment 3:** Rubric-Aware Criterion Scoring & Evidence Extraction (`criterion_evaluator.py`)
4. **Segment 4:** Concept-Based Mind-Map DAG Visualizer (`mindmap_generator.py`)
5. **Segment 5:** C3-to-C1 Cross-Component Live Event Bridge (`backend/src/integration/c3-c1/index.js`)

---

## 2. Segment 1: Batch Marking Orchestrator

- **File:** [`backend/src/modules/c3/services/batchMarkingService.js`](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/backend/src/modules/c3/services/batchMarkingService.js)
- **Primary Functions:** `createBatchSetup`, `validateBatchAnswers`, `processBatchMarking`, `finalizeBatchSubmissions`.

### 2.1 What the Code Does:
1. `createBatchSetup`: Validates question metadata, rubrics, and maximum marks. Verifies that the sum of criterion max marks equals the question's total mark. Persists the locked setup document into MongoDB `c3_batch_setups`.
2. `validateBatchAnswers`: Pre-scans imported student rows before grading. Flags empty answer strings, detects duplicate student IDs within the batch, and reports valid rows vs. invalid rows to the lecturer UI preview.
3. `processBatchMarking`: Iterates through the valid student answers, dispatches each to the evaluator (deterministic MCQ engine or Python FastAPI service), upserts records idempotently into `c3_submissions` and `c3_results`, and emits provisional learning events to Component 1.
4. `finalizeBatchSubmissions`: Bulk transitions all eligible cohort submissions to `status: 'finalized'` and syncs final marks to C1.

### 2.2 Why This Design Was Chosen:
- **Classroom Practicality:** Lecturers cannot configure a 5-criterion rubric 40 times for 40 students. Configuring once and evaluating against that shared setup reflects real academic workflows.
- **Pre-Marking Safety:** Pre-validating the cohort prevents costly AI evaluation on empty strings and stops duplicate student IDs from polluting grade registries.

### 2.3 Dependencies & Component Boundaries:
- Depends on `submissionService.js` for single-record persistence.
- Depends on `aiClient.js` to dispatch HTTP calls to port 8003.
- Depends on `syncC3AssessmentToC1` to notify Component 1.

### 2.4 What Happens if You Change It?
- *If you change criteria sum validation:* If you remove the check `criteriaSum === maxMarks`, a lecturer could configure a 4-mark question with two 3-mark criteria, allowing students to score 6/4 (150%), breaking percentage calculations downstream in C1.
- *Protected by Tests:* `c3.test.js:34` (`validate setup data rejects invalid max marks or criteria sum mismatch`), `c3.test.js:36` (`validate batch answers identifies valid, invalid, duplicate, and empty rows`), `c3.test.js:37` (`automated batch marking marks all valid students`), and `c3.test.js:38` (`retrying batch does not create duplicate submissions`).

---

## 3. Segment 2: Deterministic Multiple-Choice Marking Engine

- **File:** [`backend/src/modules/c3/services/mcqMarkingService.js`](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/backend/src/modules/c3/services/mcqMarkingService.js)
- **Primary Function:** `evaluateMcq(payload)`

### 3.1 What the Code Does:
1. Normalizes option formats: maps option IDs (e.g. `opt_a`, `opt_b`) to displayed letters (e.g. `A`, `B`) and text labels.
2. Evaluates student selection against the authoritative answer key:
   - For single-select: compares student selected option with `correct_answer`. If match, awards full `max_marks`; otherwise 0.
   - For multi-select: verifies that all correct options are selected and no incorrect options are chosen. Awards full marks only upon exact set equality.
3. Handles edge cases: blank/unanswered submissions award 0.0 marks safely without throwing exceptions.
4. Returns an evaluation contract structurally identical to the Python AI service (`marking`, `analysis`, `feedback`, `mindmap`, `total_awarded_marks`).

### 3.2 Why This Design Was Chosen:
- **Zero NLP Latency & Cost:** Objective MCQs have exact mathematical ground truths. Passing an MCQ to an NLP model or LLM is an anti-pattern that introduces hallucinations, non-deterministic scoring, and unnecessary API costs.
- **Contract Polymorphism:** By returning the identical response structure as the NLP service, downstream review modals and the C1 bridge handle MCQ and subjective submissions identically.

### 3.3 What Happens if You Change It?
- *If you allow partial credit on multi-select:* If you award $1$ mark for picking 1 of 2 correct options without penalizing a distractor, students who select all checkboxes would game the system and receive full marks.
- *Protected by Tests:* 12 dedicated unit tests in `c3.test.js:22-32` covering correct marks, zero marks, unanswered questions, invalid option IDs, missing keys, duplicate option IDs, label mapping, mark range bounds, and multi-select sets.

---

## 4. Segment 3: Rubric-Aware Criterion Scoring & Evidence Extraction

- **File:** [`ai-services/c3/services/criterion_evaluator.py`](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/ai-services/c3/services/criterion_evaluator.py)
- **Primary Function:** `evaluate_criterion(criterion, student_sentences, extracted_concepts)`

### 4.1 What the Code Does:
1. Iterates through the criterion's `scoring_levels` in strict descending order of marks (e.g. `Full` -> `Partial` -> `None`).
2. For each level, checks whether the level's `required_concepts` are present in the student's extracted concepts.
3. When matching concepts are found, scans the student's segmented sentences to identify the exact sentence numbers containing the evidence.
4. As soon as a scoring level is satisfied, assigns that level, extracts `evidence_spans` (linking sentence ID to criterion), and stops evaluation for that criterion (highest satisfied level wins).
5. If no concepts match, assigns the fallback level (`None` / 0 marks).

### 4.2 Why This Design Was Chosen:
- **Traceable Explainability:** Rather than outputting a black-box scalar mark, the system links every awarded point to the exact sentence where the student demonstrated the required knowledge.
- **Hierarchical Fallback:** Descending iteration ensures that a student who satisfies the `Full` criteria is awarded full credit without being downgraded by lower partial levels.

### 4.3 What Happens if You Change It?
- *If you iterate in ascending order:* If you iterate from `None` -> `Partial` -> `Full`, the loop would match the `None` level first (which requires 0 concepts) and award every student 0 marks!
- *Protected by Tests:* 13 unit tests in `ai-services/c3/tests/unit/test_criterion_evaluator.py` verifying highest level selection, partial credit, and sentence ID linking.

---

## 5. Segment 4: Concept-Based Mind-Map DAG Visualizer

- **File:** [`ai-services/c3/services/mindmap_generator.py`](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/ai-services/c3/services/mindmap_generator.py) & [`frontend/src/pages/c3/components/MindMapGraph.jsx`](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/frontend/src/pages/c3/components/MindMapGraph.jsx)
- **Primary Function:** `generate_mindmap(question_text, concepts, rubric)`

### 5.1 What the Code Does:
1. Python engine constructs a Directed Acyclic Graph (DAG) with:
   - Root Node: The assessment question itself (`type: 'root'`).
   - Concept Nodes: Child nodes representing syllabus concepts, partitioned by status:
     - `demonstrated` (green): Concept verified in student answer with sentence evidence.
     - `partial` (orange): Concept partially mentioned or incomplete.
     - `missing` (gray): Mandatory concept completely omitted from the answer.
   - Directed Edges: Links connecting root to concepts and showing conceptual dependencies.
2. Frontend component (`MindMapGraph.jsx`):
   - Computes dynamic node coordinates using an radial/hierarchical layout algorithm.
   - Renders native scalable vector graphics (SVG) with interactive hover tooltips, pulse animations on demonstrated nodes, and clean legend badges.

### 5.2 Why This Design Was Chosen:
- **Formative Visual Diagnosis:** Traditional feedback is a wall of text that students rarely read. A visual concept hierarchy enables students and lecturers to see conceptual gaps in under 3 seconds.
- **Pure SVG Implementation:** Avoided heavy third-party graph rendering libraries (like D3 or Cytoscape) that increase bundle size and cause React reconciliation lag.

### 5.3 Protected by Tests:
- `test_mindmap_generator.py`: 4 tests verifying root anchor, child hierarchy, and status assignment.
- `test_relationship_builder.py`: 1 test verifying structural DAG edge connectivity.
- `test_mindmap_api.py`: 1 integration test verifying FastAPI response schema.

---

## 6. Segment 5: C3-to-C1 Cross-Component Live Event Bridge

- **File:** [`backend/src/integration/c3-c1/index.js`](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/backend/src/integration/c3-c1/index.js)
- **Primary Function:** `syncC3AssessmentToC1(params)`

### 6.1 What the Code Does:
1. Translates C3 evaluation outputs into the cognitive digital twin contract:
   - Maps question context to syllabus domain topic (`sa_patterns_styles`, `ds_components_formats`, `ds_cloud_microservices`, `qm_testing_basics`).
   - Maps semantic matches into `concepts_demonstrated`, `concepts_partial`, and `concepts_missing`.
2. Implements a two-stage lifecycle:
   - When called at grading time (`finalized: false`): Sets `lifecycle_stage: 'provisional'`, `provisional_score: score`, `type: 'c3_automated_assessment'`.
   - When called at lecturer sign-off (`finalized: true`): Sets `lifecycle_stage: 'finalized'`, `final_score: score`, `lecturer_decision`, `override_reason`.
3. Ensures idempotency: uses `updateOne({ submission_id: subIdStr }, { $set: ... })` to update in-place without duplicating database records on batch retries.

### 6.2 Mutual Agreement with Component 1:
- In `backend/src/modules/c1/services/eventService.js:71`, Component 1 explicitly filters out events with `lifecycle_stage !== 'provisional'`.
- This ensures that unapproved AI proposed marks do not prematurely distort student cognitive state or trigger false academic risk alerts.

### 6.3 Protected by Tests:
- `c3.test.js:18`: Provisional event sync verification.
- `c3.test.js:19`: Idempotency on repeated provisional calls.
- `c3.test.js:20`: Finalization score preservation and status transition.
- `c3.test.js:21`: Idempotency on repeated finalization calls.
- `c3.test.js:40`: Batch finalization event sync.
