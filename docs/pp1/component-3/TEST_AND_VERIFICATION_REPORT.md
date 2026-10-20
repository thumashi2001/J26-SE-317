# AdaptiveLearnSE Component 3 — Test & Verification Report

**Document Version:** 1.0.0  
**Test Execution Date:** 20 October 2026  
**Environment:**
- OS: Windows 11
- Node.js: v20.18.0 / npm 10.8.2
- Python: 3.14 / 3.13 (`.venv_c3`)
- Database: MongoDB Atlas (`adaptivelearnse_dev`)
- Test Frameworks: Node.js Native Test Runner (`node --test`), Pytest 9.1.1, Vite 5.4.21 Rollup Build

---

## 1. Executive Summary

Component 3 automated testing covers 100% of implemented features across unit, integration, validation, batch processing, regression, and build tiers.

```
Total Automated Tests Executed: 140
Total Tests Passed:            140 (41 Backend Node.js + 99 Python AI Services)
Total Tests Failed:              0
Total Tests Skipped:             0
Pass Rate:                   100.0%
Frontend Production Build:    SUCCESS (0 errors, 106 modules transformed)
```

> [!NOTE]
> **Test Count Reconciliation:** The Node.js native test runner (`node --test`) reports 41 passed tests, comprising 1 root suite (`describe('C3 Module Backend Integration')`) and 40 individual subtests (`it(...)`). Pytest reports 99 passed test items across 15 test files. No tests are skipped or silently ignored.

---

## 2. Test Suite 1: Node.js Backend Integration

**Command Executed:**
```powershell
npm test
# Equivalent to: node --test src/modules/c3/tests/c3.test.js
```
**Working Directory:** `backend/`  
**Execution Time:** 514 ms  
**Pass/Fail Status:** 41 Passed (1 suite + 40 test cases), 0 Failed, 0 Skipped

### Mocking vs. Live Integration Disclosure
In `backend/src/modules/c3/tests/c3.test.js`, the Node.js test suite employs an in-process mock HTTP server (`http.createServer`) to simulate Python FastAPI responses (200 success, 500 internal error, 502 timeout/unreachable). This design pattern ensures:
1. **Hermetic CI Execution:** Backend controller, authentication, RBAC, schema validation, and MongoDB transactions can be verified reliably offline in ~500 ms without spinning up external Python daemons.
2. **Failure Injection:** Error handling for remote service failures (HTTP 500 and 502) is verified deterministically.
3. **Live End-to-End Separation:** Live end-to-end integration (Node -> FastAPI on port 8003 -> MongoDB Atlas) is verified independently via runtime smoke tests and browser automation sessions, rather than conflating mock tests with live multi-process tests.

### Detailed Test Cases:
1. `unauthenticated request rejected (401)` — PASS (25.7 ms)
2. `authenticated request works and routes correctly` — PASS (8.6 ms)
3. `student identity comes from req.user.sub` — PASS (5.6 ms)
4. `student cannot impersonate another student` — PASS (3.0 ms)
5. `lecturer authorization where applicable (can supply studentId)` — PASS (5.3 ms)
6. `invalid request is rejected (lecturer missing student_id)` — PASS (2.9 ms)
7. `Python service failure is handled (500)` — PASS (10.2 ms)
8. `Python service timeout/unreachable is handled (502)` — PASS (5.6 ms)
9. `all C3 endpoints including /assess are registered` — PASS (13.1 ms)
10. `student forbidden from lecturer review endpoints (403)` — PASS (1.8 ms)
11. `student forbidden from lecturer finalize endpoint (403)` — PASS (1.8 ms)
12. `lecturer can list all submissions` — PASS (2.1 ms)
13. `lecturer override without reason is rejected (400)` — PASS (1.7 ms)
14. `lecturer override with reason preserves original AI mark` — PASS (1.6 ms)
15. `lecturer finalize transitions assessment to finalized` — PASS (3.4 ms)
16. `scanned image / OCR upload endpoint explicitly rejects with 400` — PASS (2.8 ms)
17. `assessAnswer with image/scanned document payload explicitly rejects with 400` — PASS (1.8 ms)
18. `C3 to C1 live integration bridge syncs provisional learning event` — PASS (0.6 ms)
19. `repeated provisional sync calls update in-place without duplicate events (idempotency)` — PASS (0.19 ms)
20. `finalization transitions event to finalized preserving provisional_score and authoritative final_score` — PASS (0.17 ms)
21. `repeated finalization calls do not duplicate learning events` — PASS (0.13 ms)
22. `MCQ: correct answer awards full marks (2/2, 100%)` — PASS (2.6 ms)
23. `MCQ: incorrect answer awards zero marks (0/2, 0%)` — PASS (1.6 ms)
24. `MCQ: unanswered question awards zero marks safely without crashing` — PASS (1.6 ms)
25. `MCQ: invalid option ID is rejected with 400` — PASS (1.4 ms)
26. `MCQ: missing question_id or text is rejected with 400` — PASS (2.9 ms)
27. `MCQ: missing answer key is rejected with 400` — PASS (2.6 ms)
28. `MCQ: duplicate option IDs are rejected with 400` — PASS (1.6 ms)
29. `MCQ: option ID versus displayed-label mapping resolves correctly` — PASS (2.6 ms)
30. `MCQ: valid and invalid mark ranges are validated strictly` — PASS (1.5 ms)
31. `MCQ: multi-select behaviour awards full marks only when all correct options are selected` — PASS (4.0 ms)
32. `MCQ: assessAnswer persists into c3_submissions & allows lecturer review & override` — PASS (4.0 ms)
33. `Batch Marking: unauthorized student rejected from batch endpoints (403)` — PASS (5.6 ms)
34. `Batch Marking: validate setup data rejects invalid max marks or criteria sum mismatch` — PASS (2.8 ms)
35. `Batch Marking: lecturer creates subjective question & rubric setup once` — PASS (2.9 ms)
36. `Batch Marking: validate batch answers identifies valid, invalid, duplicate, and empty rows` — PASS (1.6 ms)
37. `Batch Marking: automated batch marking marks all valid students against shared setup` — PASS (5.3 ms)
38. `Batch Marking: retrying batch does not create duplicate submissions (idempotency)` — PASS (3.1 ms)
39. `Batch Marking: MCQ batch marking evaluates students deterministically using answer key` — PASS (3.0 ms)
40. `Batch Marking: lecturer can finalize entire batch in one confirmed operation & syncs to C1` — PASS (2.0 ms)

---

## 3. Test Suite 2: Python AI Services

**Command Executed:**
```powershell
.\.venv_c3\Scripts\python.exe -m pytest tests/
```
**Working Directory:** `ai-services/c3/`  
**Execution Time:** 1.18 s  
**Pass/Fail Status:** 99 Passed, 0 Failed, 0 Skipped

### Test Module Summary:
- `tests/unit/test_preprocessing.py`: 4 passed (Tokenization, whitespace removal, sentence segmentation).
- `tests/unit/test_semantic_baseline.py`: 4 passed (Lexical cosine similarity, token overlap bounds [0.0, 1.0]).
- `tests/unit/test_rubric_validator.py`: 17 passed (Rubric criteria count, scoring level order, criteria sum validation).
- `tests/unit/test_criterion_evaluator.py`: 13 passed (Highest level selection, partial credit, sentence ID linking).
- `tests/unit/test_marking_engine.py`: 9 passed (Mark authority, percentage calculation, warning propagation).
- `tests/unit/test_feedback_generator.py`: 10 passed (Strengths formatting, missing concept extraction, constructive guidance).
- `tests/unit/test_mindmap_generator.py`: 4 passed (Root node anchor, child node hierarchy, status assignment).
- `tests/unit/test_relationship_builder.py`: 1 passed (Structural DAG edge verification).
- `tests/unit/test_dataset_loader.py`: 12 passed (File presence, split sizes, structured parser validation).
- `tests/evaluation/test_evaluation_pipeline.py`: 3 passed (Pearson correlation logic, rubric scaling, pipeline execution).
- `tests/integration/test_analysis_api.py`: 5 passed (`/analysis/answer` endpoint response schema).
- `tests/integration/test_marking_api.py`: 5 passed (`/marking/evaluate` endpoint validation).
- `tests/integration/test_feedback_api.py`: 4 passed (`/feedback/generate` endpoint validation).
- `tests/integration/test_mindmap_api.py`: 1 passed (`/mindmap/generate` endpoint DAG response).
- `tests/integration/test_assessment_api.py`: 7 passed (`/c3/assess` end-to-end composite pipeline).

---

## 4. Test Suite 3: Frontend Production Build

**Command Executed:**
```powershell
npm run build
```
**Working Directory:** `frontend/`  
**Execution Time:** 6.39 s  
**Result:**
```
✓ 106 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.07 kB │ gzip:   0.59 kB
dist/assets/index-CO4f3Mcq.css  105.06 kB │ gzip:  21.04 kB
dist/assets/index-TipDg5K8.js   411.29 kB │ gzip: 117.06 kB
✓ built in 6.39s (0 errors, 0 unresolved imports)
```

---

## 5. Verification Limitations & Boundary Notes

1. **OCR / Scanned Answers:** No tests exist for scanned answer parsing or OCR because handwriting recognition is explicitly outside Component 3's research scope.
2. **Component 2 Dependency Isolation:** All tests run independently of Component 2. C3 does not invoke or depend on C2's PDF parser.
3. **Condition A–D, F Models:** No unit tests are run for Vector-RAG or GraphRAG since these remain planned research conditions for future post-PP1 work.
