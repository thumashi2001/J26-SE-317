# Demo submission fix, improvement-feedback guidance and live-marking audit (2026-10-22)

C3-owned files only. Evidence types are labelled: **code** = inspection, **runtime** = executed in this session on an isolated local stack (disposable database, never the shared one), **historical** = earlier runs not repeated.

## 1. "We could not find that item" on Submit
**Request path (code + runtime).** `AssessmentPage.jsx` `submit()` builds `{ demo_id: <selected card id>, student_answer | selected_option_id }` → `c3Api.assessAnswer` → `POST /api/v1/c3/assess` (via the Vite `/api` proxy) → `rateLimit('assess')` → `controller.assessAnswer` → `resolveStudentAssessment` (`assessmentConfig.js`) looks up `DEMO_ASSESSMENTS[demo_id]` → Node MCQ engine or one Python call → `createSubmissionWithResult` → response.
**What returns 404.** In the demo path only `httpError(404, 'Unknown demo assessment')` (an id not in the bank) and the C3 router fallback `Not found`; the page maps any 404 to the generic "We could not find that item."
**Runtime result.** On a fresh local stack running the repository code, all **7** demo ids submitted as a student return **HTTP 200** and are marked (written: `arch-full`, `arch-partial`, `arch-zero`, `oop-higher`, `quality-multi`; MCQ: `mcq-correct`, `mcq-incorrect`), so the current code does not produce the error for valid ids. The error could therefore not be reproduced from the code.
**Most probable cause on your machine (process check, read-only).** Your backend on :3000 was started 10/21 11:10 PM with plain `node src/server.js` (no watch mode), but `assessmentConfig.js` was last edited 10/22 7:39 AM and other C3 files the night before; the Vite server (HMR) serves the new page while the old backend process still runs older code. This is not proven for your machine because the 404 could not be observed there. **Restart the backend (`npm run dev` in `backend/`), the Python service and refresh the page before the viva.** At the end of this session ports 3000, 5173 and 8003 were not listening, so all three must be started again.
**Hardening made (verified root-cause-independent):**
| | Before | After |
|---|---|---|
| Payload from the page | `{ demo_id, student_answer \| selected_option_id }` | unchanged |
| Student `{ batch_id }` | resolved against lecturer batches in MongoDB (404 if absent) | **400** "Lecturer batches are not available in the student assessment flow"; also when sent next to a valid `demo_id`; nothing stored |
| Unknown / prototype names (`constructor`, `__proto__`, `toString`) | `constructor` passed the lookup and produced an empty configuration (unverified downstream effect) | **404** via own-property check |
| Non-string, empty, array, object, number demo ids | partly 400 | all **400**, response is `{ error }` only |
| 404 on submit in the page | generic "could not find that item" | actionable message ("restart the backend, refresh and choose again") and the list is re-requested |
Files: `backend/src/modules/c3/services/assessmentConfig.js`, `frontend/src/pages/c3/AssessmentPage.jsx`.
**Tests:** backend (`c3_audit.test.js`): every demo id listed and submitted, stored with the right `question_id`/student/`is_demo`, no key fields; written and MCQ results valid; 15 malformed ids rejected with nothing stored; batch ids rejected (AUDIT-B10 now enforced and its todo removed); finalized-demo re-post (AUDIT-B2) kept. Browser: S22 (404 message and list re-request), S20/S21.

## 2. "How to improve" feedback
**Source of the generic text (code).** `ai-services/c3/services/feedback/explanation_builder.py::build_improvement_suggestions` is a **hard-coded template**. At level L0 the higher-level concepts are classified as "next level", so the partial and missing lists are empty and the fallback sentence "Provide answer evidence that can be traced to the rubric requirements." fired. Feedback is rule-based (no LLM).
**Change (feedback text only; marks untouched).** New `build_contextual_improvements` (same file) is used by `generator.py` and receives the criterion, selected result, concept lists and the question text (passed through `orchestrator.py`). Behaviour:
- no evidence: says no sentence matched, that the system **cannot tell** what the student understood, current mark and the next rubric level (label and mark), and lists the concepts to write about;
- partial/some evidence: names the concepts found (by wording) and what to cover next;
- top level: advanced guidance (design justification/trade-off in architecture contexts, otherwise a specific example), no "missing" claims;
- software-architecture hints (structure, responsibilities of components, communication between components, a concrete example) appear **only** when the question, criterion or concepts are architecture-related; other subjects get neutral concept-based wording (tested with a photosynthesis rubric);
- incomplete rubric metadata: states that the rubric lists no expected concepts instead of inventing specifics;
- every non-top suggestion list ends with a note that matching is lexical, not verified understanding; student text is never quoted; next-level descriptors are not shown (only labels, marks and the concepts already displayed).
Example (0/4, no evidence): "No sentence in your answer matched the concepts for this criterion, so the system cannot tell what you did or did not understand. It currently scores 0/4; to reach 'Developing' (2/4), write about 'high-level structure', 'components', 'relationships'." followed by one hint per concept, one example hint and the lexical note.
Files: `explanation_builder.py`, `generator.py`, `orchestrator.py`, new `tests/unit/test_feedback_guidance.py` (7 tests: zero/no evidence, partial, high score, non-architecture subject, marks unchanged, incomplete rubric, legacy helper unchanged). The old helper is kept so existing tests are unchanged.

## 3. Live marking audit
**Flow (written demo).** Browser → Vite `/api` proxy → Node `POST /api/v1/c3/assess` (auth, rate limit, server resolves question/rubric from `demoAssessments.js`) → **one** call `POST {C3_AI_URL}/c3/assess` → Python `orchestrator.assess_answer`: `semantic.analyzer.analyze_answer` (tokenise, concept status by token overlap) → `marking.criterion_evaluator.evaluate_criterion` (picks the highest rubric level whose evidence rule is met; the mark is that level's `mark`) → `feedback.generator` (templated text) → `mindmap.generator` (root + concept nodes) → Node stores the whole response in MongoDB `c3_submissions` / `c3_results.ai_evaluation` (status `pending_review`) → student gets the (redacted for MCQ) result; a lecturer later reviews/finalizes.
**Flow (MCQ demo).** Same Node endpoint, but `mcqMarkingService.evaluateMcqAnswer` in Node compares the selected option with the server-held key; **Python is not called**.
| Component | Actual responsibility |
|---|---|
| `AssessmentPage.jsx` | choose card, send demo id + answer, show result |
| Node `assessAnswer` / `assessmentConfig.js` | authorization, demo-only config, calls marking, persists, role-based redaction |
| Node `mcqMarkingService` | deterministic MCQ marking (`mcq-deterministic-v1`) |
| Python `/c3/assess` (the only Python endpoint used in a live submission) | analysis → rubric marking → feedback → mind map in one call |
| `analyzer.py` + `baseline.py` | concept status from token overlap (not semantic) |
| `criterion_evaluator.py` | **awards the marks** (rubric level lookup) |
| `explanation_builder.py`, `generator.py` | rule-based feedback and improvement text |
| `mindmap/*` | structural map (root→concept links only) |
| MongoDB | stores submissions and results; supplies the lecturer batch setups; **does not supply or compute marks, and demo rubrics/answers come from `demoAssessments.js`, not the database** |
**Answers to the questions.** Marks: `evaluate_criterion` using rubric levels selected by keyword/token-overlap concept evidence (fixed rules; no percentage formula); MCQ: key comparison. Embeddings/MiniLM, an LLM, Neo4j and RAG: **not used** in live marking; the Python service reports a configured Gemini provider and an unbuilt vector index in `/health` but nothing in the submission path calls them. `reference_similarity` is computed and shown but does not affect the mark. So the live system is a **deterministic, rubric-driven, lexical baseline**, not an AI/semantic grader; the research experiments (semantic matching, model comparison) are separate and exploratory.
**Runtime evidence (this session).** Python received exactly `GET /health` and one `POST /c3/assess` for the written demo and **no request for the MCQ**; log shows no model-loading lines. In-process check after a real `/c3/assess` request: `sentence_transformers`, `torch`, `transformers`, `google.genai`/`generativeai`, `openai`, `neo4j` **not loaded**. Written trace (`arch-full`, answer naming all three concepts): 4/4, criterion C1 level L4, evidence sentences [1,2], pipeline `integrated-v1`, marking/analysis `baseline-v1`, `processing_time_ms` 34, mind map 4 nodes with `child` relationships only, stored with status `pending_review`. MCQ trace (`mcq-correct`, option B): 2/2, `mcq-deterministic-v1`, student view redacted, lecturer view shows key `["B"]`.
**Service health:** my test Python service reported healthy with the provider configured (no credentials shown). Your own services on 3000, 5173 and 8003 were not running at the end of the session.

## 4. Tests (this session)
| Command (working directory) | Result | Type |
|---|---|---|
| `pytest -q -p no:cacheprovider` (`ai-services/c3`) | 349 passed, 9 deselected, 13 xfailed | fresh |
| `C3_AI_URL=http://127.0.0.1:8004 npm test` (`backend`, live Python available) | 117 tests: 115 pass, 0 fail, 0 skipped, 2 todo (AUDIT-B9a, B9b). Without a Python service on :8003 the 3 live-boundary tests skip (112 pass, 3 skipped) | fresh |
| `node --test tests/*.test.mjs` (`frontend`) | 10 pass | fresh |
| `npx vite build` (`frontend`) | built | fresh |
| `node --test reports/c3_remediation/ui_tests/guard.test.mjs` | 9 pass | fresh |
| Guarded browser suite `e2e.mjs` (disposable local DB, backend → Python on :8004) | 106 checks, 106 passed; API matrix 35/35 | fresh |
Not re-run: functional suite (historical, 43 records), C4 check (historical), lint.
Browser history kept unmodified: `browser_results_historical_{99,103,105_before_demo_only,105_demo_only}.json`.

## 5. Remaining limitations
Marking is lexical (paraphrases score 0, FR-C3-09 FAIL); no concept-to-concept map links; C2 assessment source and student enrolment not available; the cause of your 404 is unverified on your machine (stale processes are the evidence-backed suspect); feedback remains templated.
