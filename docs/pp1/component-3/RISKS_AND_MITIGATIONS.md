# AdaptiveLearnSE Component 3 — Risk Management & Mitigation Matrix

**Document Version:** 1.0.0  
**Target Milestone:** PP1 Viva (22 October 2026)  
**Scope:** AI Marking Reliability, Data Integrity, System Availability & Governance

---

## 1. Risk Matrix

| Risk ID | Risk Description | Severity | Probability | Impact Area | Mitigation Strategy Implemented in C3 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RSK-01** | AI Hallucinations awarding unearned marks | **HIGH** | Medium | Grading Accuracy | **Deterministic Rubric Bounding:** Function 2 awards marks solely by verifying lexical/concept evidence against rubric scoring levels. It never converts arbitrary text similarity into marks. |
| **RSK-02** | Autonomous grading replacing academic judgment | **CRITICAL**| High | Academic Governance | **Human-in-the-Loop Architecture:** All AI results start in `pending_review` (AI Proposed). Finalization requires lecturer review; overrides require mandatory written justifications. |
| **RSK-03** | Batch submission duplicates upon retry | **HIGH** | Medium | Database Consistency | **Idempotent Upsert Strategy:** `createSubmissionWithResult` queries `(student_id, batch_id)` and updates existing documents in-place rather than inserting duplicate records. |
| **RSK-04** | Python AI Service unavailability or crash | **MEDIUM** | Low | System Availability | **Graceful Fallback & Error Isolation:** Backend catches HTTP 502/500 errors from FastAPI. In batch marking, failures on individual students are isolated, allowing the rest of the cohort to finish. |
| **RSK-05** | Unauthorized student score tampering | **CRITICAL**| Low | Security & RBAC | **Server-Side Role Guard:** Express routes enforce `requireRole('lecturer', 'admin')` on all review, override, and finalization endpoints. Verified by test `c3.test.js:33`. |
| **RSK-06** | Student privacy & data leakage | **HIGH** | Low | Compliance & Ethics | **Synthetic Research Data:** Production tests and demo pipelines utilize controlled synthetic records. No authentic student submissions or confidential university records are processed. |
| **RSK-07** | Rubric criteria sum mismatch | **MEDIUM** | Medium | Assessment Fairness | **Pre-Submission Validation:** `validateSetupData` strictly verifies that the sum of criteria maximum marks equals the overall assessment `max_marks` (within 0.001 tolerance). |
| **RSK-08** | Duplicate C1 learning events on repeated finalization | **MEDIUM** | Medium | Downstream Digital Twin | **Idempotent Upsert on Submission ID:** `syncC3AssessmentToC1` uses MongoDB `findOneAndUpdate` keyed by `submission_id`, updating the existing event in-place. |
| **RSK-09** | Large payload latency degradation | **LOW** | Low | User Experience | **Optimized In-Memory NLP:** Semantic tokenization and rubric evaluation execute in under 1 ms per answer (mean 0.37 ms on test split), supporting rapid batch processing. |

---

## 2. Deep Dive: Key Mitigations

### 2.1 Mitigation for RSK-01: Hallucination Elimination
In purely generative LLM marking systems, models frequently hallucinate that a student explained a concept when they merely mentioned a keyword. Component 3 mitigates this through **Function 2: Rubric-Aware Marking Engine** (`criterion_evaluator.py`). 
- Every scoring level (`L0` to `Ln`) specifies explicit required concepts and evidence rules (`minimum_demonstrated`, `minimum_partial`).
- If evidence is absent, the system defaults to the lowest rubric level with a clear audit warning (`No positive scoring level was supported...`).

### 2.2 Mitigation for RSK-02: Lecturer Authority & Audit Trail
Under Sri Lankan academic regulations, automated systems cannot unilaterally assign final degree credit. Component 3 enforces:
1. Two-tier score preservation: `automated_mark` (immutable record of AI proposal) and `final_mark` (authoritative mark confirmed or overridden by the lecturer).
2. Mandatory justification: Any override requires a non-empty string in `override_reason`.
3. Audit logging: Records `reviewed_by`, `reviewed_at`, and `finalized_at` timestamps on every result document.
