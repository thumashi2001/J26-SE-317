# AdaptiveLearnSE Component 3 — Service Contracts & Schema Specifications
**Project ID:** J26-SE-317 | **Academic Module:** IT4010 Research Project  
**Component:** Component 3 (C3) — AI-Powered Automated Marking & Answer Analysis System  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Contract Version:** 2.1.0 | **Audit Date:** 2026-10-20

---

## 1. Overview of Microservice Boundaries & Communication

Component 3 employs a clean three-tier architecture:
1. **Tier 1 (Presentation):** React 18 SPA communicates exclusively with the Express Backend via `/api/v1/c3/*` using JWT Bearer authentication.
2. **Tier 2 (Application & Persistence):** Express.js Backend handles authentication, RBAC authorization, submission lifecycle management, MongoDB persistence, and cross-component integration event publishing. It proxies AI requests to the Python service using `fetch` with configurable timeout signals.
3. **Tier 3 (AI & NLP Inference):** Python FastAPI Microservice (running at `http://127.0.0.1:8003`) executes the algorithmic 4-function assessment pipeline. It operates statelessly, returning structured Pydantic v2 schemas.

---

## 2. React Frontend ↔ Express Backend Contracts

Base URL: `http://localhost:3000/api/v1/c3`  
Header: `Authorization: Bearer <jwt_token>`  
Content-Type: `application/json`

### A. Subjective Answer Assessment
- **Endpoint:** `POST /assess`
- **Access:** Student / Lecturer / Admin
- **Request Schema:**
```json
{
  "question_id": "string (required, min: 1)",
  "question_text": "string (required, min: 5)",
  "student_answer": "string (required)",
  "reference_answer": "string (optional)",
  "max_marks": "number (optional, default: 10.0)",
  "answer_type": "string (optional, 'short' | 'essay' | 'structured', default: 'short')",
  "expected_concepts": ["string (optional)"],
  "rubric": {
    "rubric_id": "string (required)",
    "title": "string (required)",
    "criteria": [
      {
        "criterion_id": "string (required, e.g., 'C1')",
        "description": "string (required)",
        "max_marks": "number (required, gt: 0)",
        "required_concepts": ["string (optional)"],
        "scoring_levels": [
          {
            "level_id": "string (required, e.g., 'L0', 'L1', 'L2')",
            "label": "string (required)",
            "mark": "number (required, ge: 0)",
            "descriptor": "string (required)",
            "required_concepts": ["string (optional)"]
          }
        ]
      }
    ]
  }
}
```
- **Response Schema (`200 OK`):**
```json
{
  "question_id": "SE3010-ARCH-01",
  "total_awarded_marks": 5.0,
  "total_possible_marks": 5.0,
  "percentage": 100.0,
  "status": "pending_review",
  "submission_id": "6715... (MongoDB ObjectId)",
  "result_id": "6715... (MongoDB ObjectId)",
  "analysis": {
    "question_id": "SE3010-ARCH-01",
    "normalized_answer": "...",
    "sentence_count": 2,
    "token_count": 34,
    "sentences": [
      { "sentence_id": 1, "text": "High cohesion means single responsibility." }
    ],
    "reference_similarity": 0.88,
    "concept_matches": [
      { "concept": "high cohesion", "status": "demonstrated", "overlap_score": 1.0 }
    ],
    "analysis_version": "baseline-v1"
  },
  "marking": {
    "question_id": "SE3010-ARCH-01",
    "criteria_results": [
      {
        "criterion_id": "C1",
        "criterion_description": "Understanding of High Cohesion",
        "selected_level_id": "L2",
        "selected_level_label": "Proficient",
        "rubric_descriptor": "Explains single responsibility and high cohesion.",
        "awarded_mark": 5.0,
        "max_marks": 5.0,
        "evidence_sentence_ids": [1],
        "supporting_concepts": ["high cohesion"],
        "explanation": "Criterion C1 received proposed mark 5/5 at level L2.",
        "warnings": []
      }
    ],
    "total_awarded_marks": 5.0,
    "total_possible_marks": 5.0,
    "percentage": 100.0,
    "overall_explanation": "The overall proposed mark is derived by summing...",
    "marking_version": "baseline-v1"
  },
  "feedback": {
    "criteria_feedback": [
      {
        "criterion_id": "C1",
        "awarded_mark": 5.0,
        "selected_level_descriptor": "Explains single responsibility and high cohesion.",
        "strengths": ["Demonstrated concept supported by answer: high cohesion."],
        "missing_or_partial_areas": [],
        "improvement_suggestions": []
      }
    ],
    "overall_feedback": {
      "total_mark": 5.0,
      "total_possible": 5.0,
      "percentage": 100.0,
      "overall_summary": "Function 2 proposed 5 of 5 marks across 1 criterion(s).",
      "overall_strengths": ["Demonstrated concept: high cohesion."],
      "overall_missing_concepts": [],
      "overall_improvement_suggestions": []
    },
    "feedback_version": "baseline-v1"
  },
  "mindmap": {
    "root_node_id": "root-concept",
    "title": "SE3010-ARCH-01 Concept Mind Map",
    "nodes": [
      { "id": "node-1", "label": "High Cohesion", "status": "demonstrated", "node_type": "demonstrated" }
    ],
    "relationships": [],
    "summary": "1 concepts mapped (1 demonstrated, 0 missing).",
    "generation_version": "baseline-v1"
  },
  "pipeline_version": "integrated-v1"
}
```

### B. Lecturer Review & Mark Override
- **Endpoint:** `POST /submissions/:id/review`
- **Access:** Lecturer / Admin
- **Request Schema:**
```json
{
  "decision": "accepted | overridden (required)",
  "new_mark": "number (required if overridden, ge: 0)",
  "override_reason": "string (required if overridden, min: 3 chars)"
}
```
- **Response Schema (`200 OK`):**
```json
{
  "result": {
    "submission_id": "6715...",
    "decision": "overridden",
    "automated_mark": 5.0,
    "final_mark": 8.0,
    "override_reason": "Student provided excellent microservice coupling example.",
    "reviewed_by": "SLIITLEC101",
    "reviewed_at": "2026-10-20T16:00:00.000Z",
    "status": "reviewed"
  }
}
```

### C. Lecturer Assessment Finalization
- **Endpoint:** `POST /submissions/:id/finalize`
- **Access:** Lecturer / Admin
- **Request Schema:** `{}` (Empty body)
- **Response Schema (`200 OK`):**
```json
{
  "result": {
    "submission_id": "6715...",
    "status": "finalized",
    "final_mark": 8.0,
    "finalized_at": "2026-10-20T16:05:00.000Z"
  }
}
```

---

## 3. Express Backend ↔ Python FastAPI Microservice Contracts

Base URL: `http://127.0.0.1:8003`  
Header: `Content-Type: application/json`

### A. End-to-End Assessment
- **Endpoint:** `POST /c3/assess` (Alias: `POST /assess`)
- **Pydantic Model:** `AssessmentRequest` -> `AssessmentResponse`
- **Validation Rules:**
  - `question_id`: Non-empty string.
  - `question_text`: Non-empty string.
  - `student_answer`: String (empty answers evaluated safely to 0.0 marks).
  - `answer_type`: Literal `["short", "structured", "essay"]` (defaulted to `'short'` by Express).
  - `rubric.criteria`: Minimum 1 criterion required.
  - `scoring_levels`: Minimum 1 level per criterion required.
  - `max_marks`: Strictly positive float (> 0.0).

### B. Specialized Sub-Pipeline Endpoints
- **F1 Semantic Analysis:** `POST /analysis/answer` (returns normalized text, sentence splits, token counts, and concept matches).
- **F2 Rubric Marking:** `POST /marking/evaluate` (returns criterion-level scoring, evidence sentence IDs, and totals).
- **F3 Explainable Feedback:** `POST /feedback/generate` (returns criterion-specific strengths, gaps, and remedial suggestions).
- **F4 Mind Map DAG:** `POST /mindmap/generate` (returns Graphviz/SVG node-link DAG data structure).

---

## 4. Error Code & Fault Response Mapping

| Originating Layer | Underlying Condition | HTTP Status | Response Schema | Recoverable UI Behavior |
| :--- | :--- | :---: | :--- | :--- |
| **FastAPI** | Invalid Pydantic schema (e.g. empty rubric criteria) | **400** *(mapped from 422)* | `{"error": "Validation error (422): body.rubric.criteria: List should have at least 1 item..."}` | Displays inline form validation error |
| **Express** | Missing JWT or expired token | **401** | `{"error": "Authentication required"}` | Clears session and redirects to `/login` |
| **Express** | Student accessing lecturer review route | **403** | `{"error": "Forbidden: Requires lecturer or admin role"}` | Shows permission denied notification |
| **Express** | Student impersonating another student ID | **403** | `{"error": "You can only see your own data"}` | Prevents submission; logs security alert |
| **Express** | Submission ID not found in database | **404** | `{"error": "Submission not found"}` | Displays "Submission not found" banner |
| **Express** | Attempting to override a finalized record | **409** | `{"error": "This assessment has already been finalized and cannot be modified"}` | Locks form controls; disables buttons |
| **FastAPI** | Python unhandled exception or 500 crash | **502** | `{"error": "C3 AI service returned 500: Internal Server Error"}` | Displays "AI evaluation failed; please retry" |
| **Network** | Python service down / port 8003 closed | **502** | `{"error": "C3 AI service unreachable at http://127.0.0.1:8003. Is it running?"}` | Shows service connection warning badge |
| **Network** | Python processing exceeds `C3_AI_TIMEOUT_MS` | **504** | `{"error": "C3 AI service request timed out after 15000ms at http://127.0.0.1:8003/c3/assess"}` | Prompts student to retry |

---

## 5. Cross-Component Integration Contracts (C3 → C1)

Published to MongoDB collection `c1_learning_events` via `backend/src/integration/c3-c1/index.js`:

### Event 1: Provisional Assessment Completed
- **Event Name:** `c3_assessment_provisional`
- **Trigger:** Immediate student submission evaluation.
- **Payload Schema:**
```json
{
  "event_id": "evt-c3-prov-6715...",
  "student_id": "IT21001001",
  "submission_id": "6715...",
  "question_id": "SE3010-ARCH-01",
  "topic_id": "Software Architecture",
  "module_id": "SE3010",
  "provisional_score": 5.0,
  "total_possible": 5.0,
  "percentage": 100.0,
  "concept_matches": [
    { "concept": "high cohesion", "status": "demonstrated", "overlap_score": 1.0 }
  ],
  "authoritative": false,
  "timestamp": "2026-10-20T16:00:00.000Z"
}
```

### Event 2: Authoritative Assessment Finalized
- **Event Name:** `c3_assessment_finalized`
- **Trigger:** Lecturer approves or overrides mark and clicks "Finalize".
- **Payload Schema:**
```json
{
  "event_id": "evt-c3-fin-6715...",
  "student_id": "IT21001001",
  "submission_id": "6715...",
  "question_id": "SE3010-ARCH-01",
  "topic_id": "Software Architecture",
  "module_id": "SE3010",
  "provisional_score": 5.0,
  "final_score": 8.0,
  "override_applied": true,
  "override_reason": "Student provided excellent microservice coupling example.",
  "authoritative": true,
  "timestamp": "2026-10-20T16:05:00.000Z"
}
```
