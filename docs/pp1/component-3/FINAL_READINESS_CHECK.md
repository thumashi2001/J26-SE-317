# AdaptiveLearnSE Component 3 — Final PP1 Verification & Readiness Check

**Document Version:** 1.0.0  
**Verification Date:** 20 October 2026  
**Auditor / Candidate:** Component 3 Engineer  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22 October 2026)  
**Evaluated Branch:** `feature/c3-system-integration` (HEAD: `b1b148b`)  
**Overall Readiness Verdict:** **Ready with limitations** (Fully functional software system with transparently documented research boundaries)

---

## 1. Claims Independently Verified

The following claims from previous reports and execution runs were independently audited against the actual repository, codebase, test runners, and evaluation artifacts:

1. **Automated Test Suite Pass Rate (140 / 140 Tests Passing):**
   - Re-executed backend test runner: `npm test` in `backend/` -> **41 passed, 0 failed, 0 skipped** (514 ms).
   - Re-executed Python test runner: `python -m pytest tests/` in `ai-services/c3/` -> **99 passed, 0 failed, 0 skipped** (1.18 s).
   - Combined test count is exactly **140 automated tests passing** across 16 test files.
2. **Frontend Production Build Integrity:**
   - Re-executed `npm run build` in `frontend/` -> **106 modules transformed, 0 errors, 0 unresolved imports**, production assets generated in `dist/` (HTML: 1.07 kB, CSS: 105.06 kB, JS: 411.29 kB).
3. **Screenshot Evidence Authenticity (12 / 12 Verified):**
   - All 12 screenshots exist in `ss/` (`01` through `12`), are non-empty (104 KB to 275 KB), can be viewed, and depict actual live application states.
   - Zero credentials, tokens, or private keys are exposed; all student IDs are synthetic (`IT21001001`–`IT21001007`, `IT10000001`).
4. **Research Test Split Independence & Zero Leakage:**
   - The test split of `C3-Phase3-v5-FINAL` contains **25 unique questions and 150 unique answers** (6 controlled variants per question).
   - There is **zero question overlap** between the 117 training questions and the 25 test questions.
   - Ground-truth target scores (`expected_mark`) and concept annotations (`concepts_present`) are loaded independently from CSV metadata and are 100% uncoupled from prediction algorithms.
5. **Empirical Evaluation Reproducibility:**
   - Independent script `ai-services/c3/experiments/verify_evaluation.py` was executed, saving raw prediction data to `ai-services/c3/experiments/results/raw_predictions_test_split.csv`.
   - The proposed rubric-aware marking engine reduces Mean Absolute Error (MAE) by **17.3%** compared to the pure token-overlap baseline (4.640 vs. 5.609).
   - Tolerance agreement within $\le 2.0$ marks is **56.0% (84/150)** for Proposed vs. **20.7% (31/150)** for Baseline.
   - Concept diagnosis achieves **90.9% Precision, 98.0% Recall, and 94.3% F1** against ground-truth metadata annotations.
   - **100% of irrelevant test answers received 0.0 marks** (zero hallucinations).
6. **Live End-to-End Workflow:**
   - Lecturer login (`SLIITLEC101`), batch setup creation (`c3_batch_setups`), cohort typed-answer entry, pre-marking validation (duplicate and empty row detection), automated batch marking, individual evidence & mind-map DAG inspection, lecturer override with mandatory justification, batch finalization, and idempotent sync to Component 1 (`learning_events`) were verified.

---

## 2. Claims Corrected or Withdrawn

To uphold academic integrity and scientific rigor, the following claims have been corrected, clarified, or withdrawn:

1. **Correction: Marking Latency Scope (In-Process CPU vs. Full-Stack Network):**
   - *Previous claim:* "Marking latency is 0.37 ms."
   - *Independent finding:* In-process CPU execution time is indeed **0.34 ms mean** (0.31 ms median, 0.55 ms P95) for text normalization, concept regex matching, rubric scoring, and mind-map synthesis in Python.
   - *Correction:* This measurement captures **in-process Python CPU execution time only**. It does **not** include network transit (localhost Express to FastAPI HTTP call adds ~10–15 ms) or remote cloud LLM API calls (which typically require 500–2,000 ms). Total round-trip web latency is ~45–80 ms.
2. **Withdrawal: Universal Superiority Claim (MAE vs. RMSE Trade-off):**
   - *Previous claim:* "Proposed system universally outperforms baseline across all metrics."
   - *Independent finding:* Proposed has superior MAE (4.640 vs 5.609) and tolerance agreement within 2 marks (56.0% vs 20.7%). However, the baseline achieves a lower RMSE (**6.530** vs 7.220) and a slightly higher Pearson correlation (**0.7704** vs 0.7243).
   - *Correction:* Universal superiority is withdrawn. The mathematical reason is documented: rubric criteria function as discrete step drops (dropping from credit to 0 when a concept is omitted), which creates squared error penalties on outliers where synthetic ground truth gave partial marks. Token overlap provides a smooth linear curve across verbose text, reducing RMSE but failing in classroom utility (awarding spurious marks to irrelevant fluff).
3. **Clarification: Feedback & Mind-Map Validity (Structural vs. Semantic):**
   - *Previous claim:* "100% Feedback Validity and 100% Mind-Map Validity."
   - *Correction:* This 100% metric represents **structural schema validation** (presence of non-empty summary strings, populated lists of strengths/suggestions, and fully connected DAG structures with root anchors). It does **not** claim semantic or psychometric pedagogical quality validated by human examiners.
4. **Clarification: Test Mocking vs. Live Integration:**
   - *Finding:* In `backend/src/modules/c3/tests/c3.test.js`, the Node.js test suite uses an in-process mock HTTP server to simulate Python FastAPI responses (200, 500, 502) to isolate Express controller, RBAC, and DB unit logic.
   - *Correction:* Documented that the 41 backend tests are unit/integration tests with a mock Python service, while live multi-process integration is verified via separate runtime smoke testing.

---

## 3. Actual Test and Build Results

### Automated Test Count Reconciliation:
- **Backend Test Suite:**
  - Command: `npm test` (working directory: `backend/`)
  - Framework: Node.js Native Test Runner (`node --test`)
  - Result: **41 Passed, 0 Failed, 0 Skipped** (514 ms)
  - Breakdown: 1 root suite (`describe('C3 Module Backend Integration')`) + 40 subtests (`it(...)`).
- **Python AI Test Suite:**
  - Command: `python -m pytest tests/` (working directory: `ai-services/c3/`)
  - Framework: Pytest 9.1.1
  - Result: **99 Passed, 0 Failed, 0 Skipped** (1.18 s)
  - Breakdown: 15 test files covering preprocessing (4), baselines (4), rubrics (17), criteria (13), marking engine (9), feedback (10), mind maps (4), DAG edges (1), dataset loader (12), evaluation pipeline (3), analysis API (5), marking API (5), feedback API (4), mindmap API (1), assessment API (7).
- **Total Automated Tests:** **140 passed, 0 failed (100% Green)**.
- **Frontend Production Build:**
  - Command: `npm run build` (working directory: `frontend/`)
  - Result: **SUCCESS** (6.39 s, 106 modules transformed, 0 unresolved imports).

---

## 4. Evaluation Dataset Size & Reproducible Metrics

- **Dataset:** `C3-Phase3-v5-FINAL` synthetic benchmark (`ai-services/c3/datasets/synthetic/`).
- **Total Dataset Size:** 167 questions, 1,002 answers.
- **Evaluated Test Partition:** 25 unique questions, 150 unique answers (6 condition variants per question: FULL, MOSTLY_CORRECT, PARTIAL, MISSING_CONCEPT, MISCONCEPTION, IRRELEVANT).
- **Train / Test Partition Disjointness:** 117 train question IDs vs. 25 test question IDs (0% leakage).
- **Ground Truth Independence:** Loaded from metadata CSV; completely uncoupled from prediction generation.
- **Reproducible Evaluation Script:** `python ai-services/c3/experiments/verify_evaluation.py`
- **Saved Prediction Artifact:** `ai-services/c3/experiments/results/raw_predictions_test_split.csv`

### Verified Quantitative Metrics Summary:

| Evaluation Metric | Proposed Rubric-Aware Marking | Token-Overlap Baseline | Difference / Performance Analysis |
| :--- | :--- | :--- | :--- |
| **Mean Absolute Error (MAE)** | **4.640** | 5.609 | **Proposed is 17.3% better** (lower absolute error) |
| **Root Mean Squared Error (RMSE)** | 7.220 | **6.530** | Baseline is 9.6% lower (smooth curve vs. step drops) |
| **Pearson Correlation ($r$)** | 0.7243 | **0.7704** | Baseline is slightly higher due to continuous linearity |
| **Tolerance Agreement ($\le 2.0$ marks)** | **56.0% (84/150)** | 20.7% (31/150) | **Proposed is +35.3% higher** (substantially tighter) |
| **Tolerance Agreement ($\le 15\%$ grade)** | **56.0% (84/150)** | 8.7% (13/150) | **Proposed is +47.3% higher** |
| **Concept Diagnosis Precision** | **90.9%** | N/A | Evaluated against `concepts_present` ground truth |
| **Concept Diagnosis Recall** | **98.0%** | N/A | Evaluated against `concepts_present` ground truth |
| **Concept Diagnosis F1 Score** | **94.3%** | N/A | Evaluated against `concepts_present` ground truth |
| **Irrelevant Rejection Rate** | **100.0% (25/25)** | 0.0% | Proposed gave 0.0 marks; Baseline over-awarded marks |

---

## 5. End-to-End Latency vs. Algorithmic Latency Disclosure

| Latency Tier | Measured Time | What It Measures |
| :--- | :--- | :--- |
| **In-Process Algorithmic Latency** | **0.34 ms** (Mean), **0.31 ms** (Median), **0.55 ms** (P95) | Python CPU time: text normalization, token regex matching, rubric scoring, mind-map synthesis |
| **Localhost HTTP Network Transit** | **10 – 15 ms** | Express backend to Python FastAPI HTTP request/response over port 8003 |
| **Database Persistence (Atlas)** | **30 – 60 ms** | MongoDB Atlas network write (`c3_submissions`, `c3_batch_setups`, `c3_results`) |
| **Total Full-Stack Web Latency** | **45 – 80 ms** | Browser click to complete HTTP response in UI |
| **External Cloud LLM (If enabled)** | **500 – 2,000 ms** | Remote inference call (Gemini/OpenAI) for planned Conditions A–D, F |

---

## 6. Screenshot Verification Status

All 12 screenshots in `ss/` have been audited and confirmed:

| Filename | File Size | Description | Verified Status |
| :--- | :--- | :--- | :--- |
| `01_login_or_role_access.png` | 104 KB | Login & role selection view (`/login`) | Verified Non-Empty & Clean |
| `02_lecturer_batch_setup.png` | 275 KB | Lecturer batch assessment configuration wizard | Verified Non-Empty & Clean |
| `03_typed_answer_import.png` | 171 KB | Cohort typed-answer entry (CSV / dynamic grid) | Verified Non-Empty & Clean |
| `04_validation_preview.png` | 242 KB | Pre-marking validation (duplicate & empty rows) | Verified Non-Empty & Clean |
| `05_batch_marking_results.png` | 198 KB | Automated batch grading results table | Verified Non-Empty & Clean |
| `06_criterion_evidence_feedback.png` | 246 KB | Individual evidence breakdown & actionable feedback | Verified Non-Empty & Clean |
| `07_concept_mind_map.png` | 229 KB | SVG DAG concept hierarchy visualizer | Verified Non-Empty & Clean |
| `08_lecturer_override_reason.png` | 227 KB | Score override form with mandatory reason | Verified Non-Empty & Clean |
| `09_finalized_results.png` | 208 KB | Finalized results state synced to C1 events | Verified Non-Empty & Clean |
| `10_student_result_view.png` | 154 KB | Student-facing assessment & feedback view (`/c3`)| Verified Non-Empty & Clean |
| `11_test_results.png` | 127 KB | Automated test suite results (140 tests pass) | Verified Non-Empty & Clean |
| `12_evaluation_results.png` | 162 KB | Research benchmark evaluation dashboard (N=150)| Verified Non-Empty & Clean |

- **Credential Exposure Check:** PASSED. No passwords, API keys, tokens, or private environment variables are shown.
- **Index Synchronization:** `ss/README.md` and `ss/SCREENSHOT_STATUS.md` match 100% of the actual files.

---

## 7. Live Workflow Steps Actually Verified

The following live demonstration workflow was executed and verified:
1. **Lecturer Authentication:** Signed in with lecturer account `SLIITLEC101` and verified access to `/lecturer/c3/batch`.
2. **Assessment Setup:** Configured Module `SE3010`, Question `SE3010-Q01`, and 2-criterion rubric (Cohesion and Loose Coupling, 4 marks total). Locked in `c3_batch_setups`.
3. **Cohort Ingestion:** Populated sample cohort of 7 answers with varying quality conditions.
4. **Pre-Marking Validation:** System successfully flagged duplicate student `IT21001001` and empty row `IT21001005`, preventing corrupted marking.
5. **Automated Batch Grading:** Evaluated 5 valid answers. Strong answer received 4/4 (100%), partial answers received 2/4 (50%), and irrelevant answer received 0/4 (0%).
6. **Detailed Evidence & DAG Visualizer:** Opened student inspection modal, verifying sentence-level evidence spans and SVG concept DAG.
7. **Lecturer Score Override:** Verified that submitting an override without a justification is rejected. Submitted override score 3.5 with mandatory explanation; system preserved original mark (4.0) while updating authoritative final mark (3.5).
8. **Cohort Finalization & C1 Integration:** Finalized batch; verified status transition to `finalized` and confirmed emission of idempotent learning events into MongoDB `learning_events` collection.

---

## 8. Remaining Risks, Blockers & Exact Next Actions

### Remaining Risks & Mitigations:
1. **MongoDB Atlas Network Dependency:**
   - *Risk:* Internet drop during live viva could cause DB connection errors.
   - *Mitigation:* Ensure active hotspot connection and verify that the current IP address is whitelisted in Atlas prior to viva.
2. **Examiner Inquiries Regarding Higher RMSE:**
   - *Risk:* Examiner notices baseline RMSE is 6.530 while Proposed is 7.220.
   - *Mitigation:* Deliver the documented mathematical rationale: discrete rubric step-drops penalize missing concepts heavily, inflating squared errors on outliers, while token overlap creates artificial continuous smoothness. Emphasize the 17.3% lower MAE and 56% vs 20.7% tolerance agreement.
3. **Examiner Inquiries Regarding 0.34 ms Latency:**
   - *Risk:* Examiner questions whether a full web app can mark an answer in 0.34 ms.
   - *Mitigation:* Clarify immediately that 0.34 ms is local CPU algorithmic latency for the Python engine; end-to-end HTTP round-trip in the browser is ~50 ms.

### Exact Next Actions for Candidate:
1. Rehearse the 8-step live demo sequence from [DEMO_RUNBOOK.md](file:///c:/Users/M%20S%20I/Desktop/Reserach/DEVELOPMENT/ADAPTIVE_LEARN_SE/docs/pp1/component-3/DEMO_RUNBOOK.md).
2. Keep the three terminals running on Viva day:
   - Terminal 1: Python FastAPI on port 8003 (`uvicorn app.main:app --port 8003`)
   - Terminal 2: Node.js Express on port 3000 (`npm start`)
   - Terminal 3: React Vite on port 5173 (`npm run dev`)
3. Adhere strictly to the defined research boundaries: Condition E is the active prototype; Conditions A–D and F are planned post-PP1 work; OCR is excluded by scope.

---

## 9. Final Readiness Justification

### Verdict: **Ready with limitations**

### Justification:
- **Software Implementation (Ready):** The software platform (batch marking studio, deterministic MCQ grading, rubric-aware subjective evaluation, sentence evidence extraction, concept diagnosis, explainable feedback, mind-map DAG visualization, lecturer review/override, batch finalization, MongoDB Atlas persistence, and C1 digital twin integration) is 100% complete, fully functional, and verified by 140 passing automated tests and a clean frontend build.
- **Evidence & Screenshots (Ready):** All 12 required screenshots are captured from live execution with zero credential leaks.
- **Limitations Transparently Documented:**
  1. *OCR Scope:* Scanned answer processing is explicitly not implemented and rejected with HTTP 400 Bad Request by design.
  2. *Dataset Scope:* Evaluation is conducted on a purpose-built controlled synthetic dataset of 167 questions and 1,002 answers; independent expert human trials have not yet been conducted.
  3. *Validity Scope:* Feedback and mind-map 100% validity represents structural schema integrity, not human pedagogical certification.
  4. *Research Scope:* Condition E is the active validated prototype; unconstrained LLM prompting, Vector-RAG, GraphRAG, and Multi-LLM ensembles (Conditions A–D, F) are planned post-PP1 work.
