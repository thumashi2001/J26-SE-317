# AdaptiveLearnSE Component 3 — API & Integration Contracts
**Project:** AdaptiveLearnSE | **Component:** C3 (Automated Marking & Answer Analysis)  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Document Version:** 2.0.0 (PP1 Final Verified)

---

## 1. System API Architecture

Component 3 operates a multi-tier API structure:
1. **Node.js Express Backend (`http://localhost:3000/api/v1/c3`):** Manages authentication, RBAC authorization, submission persistence, lecturer reviews, batch workflows, and cross-component integration event publishing.
2. **Python FastAPI AI Microservice (`http://localhost:8003`):** Handles CPU/GPU-bound algorithmic tasks: text tokenization, concept extraction, rubric criterion evaluation, explainable feedback generation, and mind map DAG construction.

---

## 2. Express Backend API Specification

All endpoints require JWT Bearer token authentication in the `Authorization: Bearer <token>` header, unless otherwise noted.

### A. Assessment Endpoints
#### 1. `POST /api/v1/c3/assess`
- **Role:** Student / Lecturer
- **Description:** Submits a typed subjective student answer for automated marking.
- **Request Body:**
```json
{
  "question_id": "PP-SE3010-001",
  "question_text": "Explain statement coverage and branch coverage in software testing.",
  "student_answer": "Statement coverage measures executed statements. Branch coverage tests decision branches.",
  "reference_answer": "Statement coverage tests statements. Branch coverage tests decision paths.",
  "max_marks": 10.0,
  "rubric": {
    "rubric_id": "RUB-SE3010-01",
    "criteria": [
      {
        "criterion_id": "C1",
        "description": "Explains statement coverage",
        "max_marks": 5.0,
        "required_concepts": ["statement coverage"]
      },
      {
        "criterion_id": "C2",
        "description": "Explains branch coverage",
        "max_marks": 5.0,
        "required_concepts": ["branch coverage"]
      }
    ]
  }
}
```
- **Response (`201 Created`):**
```json
{
  "submission_id": "SUB-1729420000000",
  "student_id": "IT23000001",
  "total_awarded_mark": 10.0,
  "max_marks": 10.0,
  "percentage": 100.0,
  "demonstrated_concepts": ["statement coverage", "branch coverage"],
  "missing_concepts": [],
  "criteria_evaluations": [
    {
      "criterion_id": "C1",
      "awarded_mark": 5.0,
      "max_marks": 5.0,
      "level_label": "Proficient",
      "explanation": "Fully addresses statement coverage."
    }
  ],
  "feedback": "Excellent response with strong conceptual coverage.",
  "mindmap": {
    "nodes": [{"id": "n1", "label": "Statement Coverage", "status": "demonstrated"}],
    "edges": []
  },
  "is_finalized": false
}
```

#### 2. `POST /api/v1/c3/mcq/assess`
- **Role:** Student / Lecturer
- **Description:** Submits multiple-choice answer selection for deterministic evaluation against answer key.
- **Request Body:**
```json
{
  "question_id": "MCQ-SE3040-001",
  "question_text": "Which HTTP method is idempotent?",
  "selected_option_ids": ["OPT-B"],
  "answer_key": ["OPT-B"],
  "max_marks": 2.0
}
```
- **Response (`201 Created`):**
```json
{
  "submission_id": "MCQ-SUB-1729420000000",
  "awarded_marks": 2.0,
  "max_marks": 2.0,
  "is_correct": true,
  "evaluation_type": "deterministic_mcq"
}
```

### B. Lecturer Review & Audit Endpoints
#### 3. `GET /api/v1/c3/submissions`
- **Role:** Lecturer only (`role: 'lecturer'`)
- **Query Params:** `question_id`, `status` (`provisional`, `finalized`)
- **Response (`200 OK`):** Array of submission records with student IDs, AI marks, and final marks.

#### 4. `PUT /api/v1/c3/submissions/:id/override`
- **Role:** Lecturer only
- **Description:** Overrides AI-proposed marks. Preserves original AI score in audit history.
- **Request Body:**
```json
{
  "override_mark": 8.5,
  "reason": "Student provided valid alternative design justification in paragraph 2."
}
```
- **Response (`200 OK`):** Updated submission with `override_history` containing timestamp, lecturer ID, old mark, new mark, and reason.

#### 5. `PUT /api/v1/c3/submissions/:id/finalize`
- **Role:** Lecturer only
- **Description:** Finalizes assessment score and triggers authoritative final event sync to C1.

### C. Batch Marking Endpoints
- `POST /api/v1/c3/batch/setup`: Configures shared question, max marks, and rubric for a batch.
- `POST /api/v1/c3/batch/validate`: Validates CSV rows for empty entries, duplicates, and malformed answers.
- `POST /api/v1/c3/batch/mark`: Executes automated marking across all valid student submissions.
- `POST /api/v1/c3/batch/finalize`: Bulk finalizes all batch submissions and dispatches learning events.

---

## 3. Python FastAPI AI Microservice API Specification

Base URL: `http://localhost:8003`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/assess` | End-to-end marking: concepts, rubric, feedback, and mind map DAG. |
| `POST` | `/evaluate-criterion` | Evaluates a single rubric criterion against student answer evidence. |
| `POST` | `/extract-concepts` | Extracts technical concepts and identifies missing expected concepts. |
| `POST` | `/generate-feedback` | Generates evidence-tied formative feedback. |
| `POST` | `/generate-mindmap` | Builds Directed Acyclic Graph (DAG) for visual feedback. |
| `GET` | `/health` | Health check returning service status, active version, and model provider. |

---

## 4. Cross-Component Integration Contracts

### C3 to C1 (Cognitive Digital Twin) Event Contract
Component 3 dispatches assessment events to Component 1 via `c1IntegrationService.js`.

#### Provisional Assessment Event (On Student Submission)
```json
{
  "event_type": "ASSESSMENT_SUBMITTED",
  "event_id": "EVT-C3-PROV-1729420000000",
  "timestamp": "2026-10-20T10:15:30.000Z",
  "student_id": "IT23000001",
  "assessment_id": "SUB-1729420000000",
  "question_id": "PP-SE3010-001",
  "module_code": "SE3010",
  "provisional_score": 10.0,
  "max_score": 10.0,
  "mastery_status": "PROVISIONAL",
  "demonstrated_concepts": ["statement coverage", "branch coverage"],
  "missing_concepts": [],
  "idempotency_key": "c3_sub_SUB-1729420000000"
}
```

#### Finalized Assessment Event (On Lecturer Sign-off)
```json
{
  "event_type": "ASSESSMENT_FINALIZED",
  "event_id": "EVT-C3-FINAL-1729420000000",
  "timestamp": "2026-10-20T10:25:00.000Z",
  "student_id": "IT23000001",
  "assessment_id": "SUB-1729420000000",
  "provisional_score": 10.0,
  "final_authoritative_score": 9.5,
  "lecturer_id": "LEC-001",
  "override_applied": true,
  "mastery_status": "CONFIRMED",
  "idempotency_key": "c3_final_SUB-1729420000000"
}
```

### Idempotency & Fault Tolerance
- All event dispatches use deterministic `idempotency_key` headers.
- If the C1 service is temporarily unreachable, events are recorded with `sync_status: 'pending_retry'` without failing the student's submission.
