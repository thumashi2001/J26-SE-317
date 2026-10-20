# AdaptiveLearnSE Component 3 — SOLID Principles & Code Quality Audit

**Audit Date:** 20 October 2026  
**Auditor:** Component 3 Senior Engineer / Technical Documentation Specialist  
**Audited Artifacts:**
- Backend: `backend/src/modules/c3/controllers/c3Controller.js`
- Backend Services: `batchMarkingService.js`, `submissionService.js`, `mcqMarkingService.js`, `aiClient.js`
- Integration: `backend/src/integration/c3-c1/index.js`
- Routes & Auth: `backend/src/modules/c3/routes/index.js`, `backend/src/middleware/auth.js`
- Python AI Services: `orchestrator.py`, `analyzer.py`, `criterion_evaluator.py`, `rubric_validator.py`, `generator.py`
- Frontend: `LecturerBatchMarkingPage.jsx`, `LecturerReviewPage.jsx`, `LecturerQueuePage.jsx`, `c3Api.js`

---

## 1. SOLID Principles Audit Findings

### 1.1 Single Responsibility Principle (SRP)

> *"A module should have one, and only one, reason to change."*

| Module Audited | Responsibility Analysis | Compliance | Concrete Evidence & References |
| :--- | :--- | :--- | :--- |
| **`c3Controller.js`** | Responsible purely for HTTP request extraction, student ID resolution from JWT, delegating to domain services, and returning structured JSON. | **COMPLIANT** | Contains no embedded database queries or NLP algorithms. Functions like `createBatchSetup` (line 133) and `processBatchMarking` (line 161) delegate directly to `batchMarkingService`. |
| **`mcqMarkingService.js`** | Exclusively handles authoritative, deterministic multiple-choice question option normalization, key comparison, and scoring bounds. | **COMPLIANT** | Segregated from subjective NLP logic. Single reason to change: alterations in MCQ option parsing or grading rules. |
| **`batchMarkingService.js`** | Orchestrates batch assessment setup creation, pre-marking row validation, batch grading execution, and bulk finalization. | **COMPLIANT** | Delegates individual record persistence to `submissionService` and subjective marking to `aiClient`. Does not manipulate raw MongoDB collections for submissions directly. |
| **`submissionService.js`** | Manages persistence lifecycle for submissions and results, review overrides, and single finalization. | **COMPLIANT** | Focuses exclusively on the human-in-the-loop review workflow and MongoDB persistence. Delegates event emission to `syncC3AssessmentToC1`. |
| **`orchestrator.py` (Python)** | High-level pipeline coordinator executing F1 -> F2 -> F3 -> F4 in sequence. | **COMPLIANT** | Does not perform string parsing or SVG rendering directly; delegates to `analyzer.py`, `criterion_evaluator.py`, `feedback/generator.py`, and `mindmap/generator.py`. |

### 1.2 Open/Closed Principle (OCP)

> *"Software entities should be open for extension, but closed for modification."*

| Area | Current Implementation & Extensibility | Compliance | Concrete Evidence & Recommendations |
| :--- | :--- | :--- | :--- |
| **Question Type Selection** | Evaluator dispatch distinguishes between objective (`mcq`) and subjective (`short`, `essay`) assessments. | **PARTIALLY COMPLIANT** | Evaluator selection uses `isMcqPayload(payload)` in `c3Controller.js:8-11`. Adding a third question type (e.g. `fill-in-the-blank`) currently requires adding a branch in `c3Controller.js` and `batchMarkingService.js`. Recommended for Phase 4: Strategy registry pattern (`evaluatorRegistry.get(answerType)`). |
| **Scoring Rules & Levels** | Rubric scoring is driven entirely by data (`ScoringLevel` models with dynamic required concepts and evidence rules). | **COMPLIANT** | In `criterion_evaluator.py:155-185`, criteria and scoring levels are evaluated iteratively. Adding new levels (`L0` to `L4`) requires zero code changes in the Python service. |
| **Provenance Tracking** | Provenance classification (`detectProvenance`) in `submissionService.js:27-41` categorizes demo, student, and test fixtures dynamically. | **COMPLIANT** | Open to adding new demo question IDs without modifying database schema. |

### 1.3 Liskov Substitution Principle (LSP)

> *"Subtypes must be substitutable for their base types without altering program correctness."*

| Component Area | Evaluation | Finding |
| :--- | :--- | :--- |
| **Python Domain Models** | `AssessmentRequest` inherits from `MarkingRequest`, which inherits from `AnswerAnalysisRequest`. | **COMPLIANT** | In `ai-services/c3/app/schemas/assessment.py:9`, `AssessmentRequest` extends `MarkingRequest` without overriding methods or violating preconditions. All fields from parent schemas are preserved and validated cleanly. |
| **Evaluator Result Structures** | Both `mcqMarkingService.js` and `aiClient.js` return identical response contracts: `{ marking, analysis, feedback, mindmap, total_awarded_marks, max_marks, percentage }`. | **COMPLIANT** | Downstream consumers (review pages, C1 bridge, persistence layer) process results interchangeably regardless of whether the assessment was MCQ or subjective. |

### 1.4 Interface Segregation Principle (ISP)

> *"Clients should not be forced to depend on methods or fields they do not use."*

| Contract Audited | ISP Analysis | Compliance |
| :--- | :--- | :--- |
| **Frontend API (`c3Api.js`)** | Granular, task-specific API functions: `validateBatchAnswers`, `processBatchMarking`, `reviewSubmission`, `finalizeSubmission`. | **COMPLIANT** | Clients invoke only the specific endpoint required for their workflow step, rather than a monolithic all-in-one endpoint. |
| **C1 Integration Contract** | `syncC3AssessmentToC1` accepts a focused parameter object (`studentId`, `submissionId`, `score`, `conceptMatches`, `finalized`). | **COMPLIANT** | C3 does not force C1 to absorb raw rubric criteria trees, full answer texts, or token vectors. Only the required learner signals are emitted. |
| **Python Service Endpoints** | Exposes separate endpoints: `/analysis/answer`, `/marking/evaluate`, `/feedback/generate`, `/mindmap/generate`, alongside composite `/c3/assess`. | **COMPLIANT** | Downstream research scripts can invoke individual functions (e.g. mind-map only) without triggering full assessment. |

### 1.5 Dependency Inversion Principle (DIP)

> *"High-level modules should not depend on low-level modules. Both should depend on abstractions."*

| Module Audited | DIP Evaluation | Compliance |
| :--- | :--- | :--- |
| **Database Connection (`getDb()`)** | Controllers and services access MongoDB through an accessor function `getDb()`, not concrete client instances. | **COMPLIANT** | Enables mocking in automated unit tests (`c3.test.js`) without requiring a live cloud connection. |
| **AI Client Layer (`aiClient.js`)** | The Node.js backend abstracts HTTP communication with the Python service through `aiClient.js`. | **COMPLIANT** | Business logic in `batchMarkingService` calls `aiClient.assessAnswer(aiUrl, payload)` rather than making raw `fetch` requests with manual headers. |

---

## 2. Code Quality & Maintainability Findings

### 2.1 Issues Identified and Addressed During Audit

1. **Misplaced ES Module Import in Controller (FIXED):**
   - *Location:* `backend/src/modules/c3/controllers/c3Controller.js:125`
   - *Issue:* `import * as batchSvc from '../services/batchMarkingService.js'` was placed inline between function definitions.
   - *Resolution:* Hoisted to top-level import block (lines 1–5). Verified via `npm test`.
2. **Missing Backend Test Script in `package.json` (FIXED):**
   - *Location:* `backend/package.json`
   - *Issue:* Executing `npm test` failed with `"Missing script: test"`.
   - *Resolution:* Added `"test": "node --test src/modules/c3/tests/c3.test.js"`.
3. **Evaluation Script Feedback Field Compatibility (FIXED):**
   - *Location:* `ai-services/c3/experiments/run_evaluation.py:162`
   - *Issue:* Evaluator accessed `res.feedback.summary` instead of Pydantic model `res.feedback.overall_feedback.overall_summary`.
   - *Resolution:* Corrected field path to `res.feedback.overall_feedback.overall_summary`. Enabled successful execution across 150 test items.

### 2.2 Security & Authorization Architecture

1. **Role-Based Authorization (RBAC):**
   - All batch endpoints (`/batch/setup`, `/batch/validate`, `/batch/mark`, `/batch/:id/finalize-all`) and review endpoints (`/submissions/:id/review`, `/submissions/:id/finalize`) are strictly guarded by `requireRole('lecturer', 'admin')`.
   - Verified by test `c3.test.js:33`: An unprivileged student token attempting batch or review operations receives HTTP 403 Forbidden.
2. **Mandatory Override Accountability:**
   - Overriding an AI proposed mark strictly requires a non-empty `override_reason` string (`submissionService.js:375-378`).
   - If omitted, the backend rejects the request with HTTP 400 Bad Request.
3. **Protection of Historical Marks:**
   - The original automated mark is permanently preserved in `automated_mark`.
   - The lecturer's manual adjustment is stored in `final_mark`, with reviewer ID and timestamp recorded in the audit trail.
