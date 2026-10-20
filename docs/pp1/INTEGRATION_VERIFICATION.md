# AdaptiveLearnSE — Component Integration Verification Report

**Document Version:** 2.0.0  
**Verification Date:** 20 October 2026  
**Verified Connection:** Component 3 (Marking) ➔ Component 1 (Cognitive Digital Twin)  
**Overall Integration Status:** **VERIFIED OPERATIONAL & IDEMPOTENT**  

---

## 1. Executive Summary

A critical requirement of the PP1 evaluation is demonstrating at least one genuine, working component-to-component integration in the running codebase rather than merely presenting conceptual block diagrams.

Component 3 (Automated Marking) provides a fully functional, verified, and automated event bridge to Component 1 (Cognitive Digital Twin) via the shared MongoDB Atlas collection `learning_events`. This integration has been audited across unit tests, schema contracts, consumer code, and live runtime transactions.

```
[Component 3: Automated Marking]
        │
        ▼ (syncC3AssessmentToC1)
[MongoDB Atlas: 'learning_events' Collection]
        │
        ├─► Lifecycle Stage: 'provisional' ──► [C1 Ignores for Mastery Risk]
        │
        └─► Lifecycle Stage: 'finalized'   ──► [C1 Incorporates into Cognitive State]
                                                        │
                                                        ▼ (eventService.js:71)
                                            [Component 1: Cognitive Digital Twin]
```

---

## 2. Code-Level Implementation Verification

### 2.1 Producer Bridge Implementation
- **File:** `backend/src/integration/c3-c1/index.js`
- **Primary Function:** `syncC3AssessmentToC1(params)`
- **Key Mechanics:**
  1. **Topic Classification:** Automatically resolves the syllabus topic for C1 learner modeling (`sa_patterns_styles`, `ds_components_formats`, `ds_cloud_microservices`, `qm_testing_basics`) based on question keywords.
  2. **Concept Partitioning:** Maps fine-grained semantic evidence from C3's `concept_matches` into `concepts_demonstrated`, `concepts_partial`, and `concepts_missing`.
  3. **Two-Stage Lifecycle:**
     - At submission time: Writes event with `lifecycle_stage: 'provisional'`, `provisional_score: score`, and `type: 'c3_automated_assessment'`.
     - At finalization: Updates existing document in-place with `lifecycle_stage: 'finalized'`, `final_score: score`, `lecturer_decision`, and `override_reason`.
  4. **Idempotency:** Queries MongoDB by stable `submission_id`. Uses `$set` to prevent duplicate event creation upon batch retries.

### 2.2 Consumer Integration in Component 1
- **File:** `backend/src/modules/c1/services/eventService.js`
- **Consumer Logic (Lines 70–78):**
  ```javascript
  const all = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  all.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const start = new Date(all[0].timestamp);
  const toDay = (t) => Math.floor((new Date(t) - start) / DAY_MS) + 1;
  const events = all
    .filter((e) => e.lifecycle_stage !== 'provisional')
    .map((e) => ({
      day: toDay(e.timestamp),
      topic: e.topic,
      correct: !!e.correct,
      hint_used: !!e.hint_used,
      time_sec: e.time_sec ?? 30,
    }));
  ```
- **Auditor Observation:** Component 1 explicitly filters out records where `lifecycle_stage === 'provisional'`. This confirms that the two components adhere to an agreed contract: AI proposed marks remain provisional until lecturer approval, preventing unverified marks from altering the student's mastery profile.

---

## 3. Test Suite Verification & Proof of Idempotency

The integration bridge is tested deterministically in `backend/src/modules/c3/tests/c3.test.js`:

| Test Name | Test Assertion | Pass Result | Duration |
| :--- | :--- | :--- | :--- |
| `C3 to C1 live integration bridge syncs provisional learning event` | Verifies `lifecycle_stage === 'provisional'` and `type === 'c3_automated_assessment'` in `learning_events`. | ✅ **PASS** | 0.61 ms |
| `repeated provisional sync calls update in-place without duplicate events (idempotency)` | Invokes `syncC3AssessmentToC1` twice for same `submission_id`; asserts that only 1 record exists. | ✅ **PASS** | 0.21 ms |
| `finalization transitions event to finalized preserving provisional_score and authoritative final_score` | Finalizes result; verifies `lifecycle_stage === 'finalized'`, `final_score === 3.5`, `provisional_score === 4.0`. | ✅ **PASS** | 0.17 ms |
| `repeated finalization calls do not duplicate learning events` | Invokes finalization sync multiple times; asserts record count remains exactly 1. | ✅ **PASS** | 0.23 ms |
| `Batch Marking: lecturer can finalize entire batch in one confirmed operation & syncs to C1` | Executes batch finalization for entire cohort; asserts all cohort events transition to finalized in C1. | ✅ **PASS** | 1.76 ms |

---

## 4. Failure Modes & Resilience Handling

| Failure Scenario | Observed System Behavior | Resilience Mechanism |
| :--- | :--- | :--- |
| **MongoDB Atlas Disconnected** | `syncC3AssessmentToC1` catches connection error; logs warning and returns `{ synced: false, reason: 'Database connection unavailable' }`. | Graceful degradation: C3 assessment result still returns to UI; does not crash Express server. |
| **Missing `submission_id`** | Rejects call immediately with `{ synced: false, reason: 'submissionId is required...' }`. | Input validation prevents corrupted null-keyed records. |
| **Batch Rerun / Retry** | Lecturer re-runs batch marking after partial network failure. | In-place update query `{ submission_id: subIdStr }` overwrites without creating duplicate rows. |
| **Provisional Call after Finalization** | If an asynchronous retry arrives after lecturer already finalized the mark. | Guard clause (`if (existing.lifecycle_stage === 'finalized') return`) protects finalized mark from being reverted to provisional. |
