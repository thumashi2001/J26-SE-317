# 13 C3 frontend UX/UI audit, redesign and verification

Date 2026-10-21. Scope: every C3 page, component and API call used by the **student, lecturer and admin** roles. (The task asked for `11_…`; that number was already used by `11_vector_rag_implementation.md`, so this is 13.)
Nothing was committed or pushed. Work is on branch `feature/c3-pp1-experiments-20261020` as uncommitted changes.

## 1. Proposal check (FR-C3, proposal pp.40–45) against the UI
| Proposal requirement | Where in the UI | Status after this work |
|---|---|---|
| Accept question and student response (FR-01/02, 07) | Student page: assessment picker + answer box / MCQ options | Works; students no longer see or send question/key/rubric |
| Reference comparison, rubric-aware marking, partial credit, proposed mark (FR-08..15) | Result: mark card, "Marking by criterion" cards with rubric level reached | Works (verified in browser: written and MCQ answers) |
| Explainable evidence (FR-25/26) | Criterion cards: evidence sentences, "Why this mark" | Works |
| Concept classes demonstrated/partial/missing (FR-21..24) | "Concept diagnosis" table with word-overlap bar and supporting sentence | Works; overlap labelled as a word-match measure, not meaning |
| Feedback (FR-27..31) | "Feedback" panel + per-criterion strengths/gaps/suggestions | Works (text is the service's templated wording) |
| Answer-derived mind map (FR-32..35) | "Concept map" (SVG + list alternative) | Works; star graph only (no concept-to-concept links exist in the data) |
| Lecturer review, accept/override with reason, record status (FR-36..41) | Review page and batch review dialog | Works; original automatic mark kept; reason mandatory; finalize asks for confirmation |
| Integration with C1/C2/C4 (FR-42..46) | not a UI concern | C3→C1 events unchanged and **not** browser-tested; C2/C4 not implemented |
No functionality was added beyond the proposal (no OCR upload, no admin C3 page, no analytics).

## 2. Routes and workflows audited (from `App.jsx`, `menus.js`, pages and the API client)
| Route | Role area | Component | Notes |
|---|---|---|---|
| `/c3`, `/c3/*` | student | `AssessmentPage` | picker, answer, result, history |
| `/lecturer/c3` | lecturer + admin area | `LecturerQueuePage` ("Marking Review") | |
| `/lecturer/c3/:id`, `/lecturer/c3/review/:id` | lecturer + admin area | `LecturerReviewPage` | |
| `/lecturer/c3/batch`, alias `/c3/batch` | lecturer + admin area | `LecturerBatchMarkingPage` (+ `batch/SetupForm`, `batch/Panels`) | alias sits inside the lecturer area |
| `/c3/review`, `/c3/review/:id` | lecturer + admin area | queue / review | aliases |
| `/admin`, `/admin/lecturers` | admin | admin dashboard, approvals | **no C3 page and no C3 menu item exist for admins** |
| `/lecturer` | lecturer + admin area | `LecturerHome` | showed "Component N" chips on every tool card |
Shared components: `CriterionCard`, `ConceptDiagnosis`, `MindMapGraph` (all rewritten), new `AssessmentResult`, `c3ui` (PageHeader, StatusPill, Notice, Dialog, ConfirmDialog, Stepper, EmptyState, Spinner, friendlyError). API calls: `/c3/assessments` (new), `/c3/examples` (new, staff only), `/c3/assess`, `/c3/submissions[/:id[/review|/finalize]]`, `/c3/batch/*`. Raw `/c3/analysis|marking|feedback|mindmap` proxies are not used by any page.

## 3. C1/shared patterns reused
Global classes and tokens from `index.css`: `.page-head`, `.btn` (+ `.secondary`, `.danger`, `.back`), `.btn-ghost`, `.tabs`, `.pill` + `.status-pending/approved/rejected`, `.chip`, `.panel` (+ `.flush`), `.table-wrap .data-table`, `.hint`, `.muted`; all colours come from the shared tokens, so the pages follow the existing light/dark switch (`data-theme`). `c3.css` was re-tokenised (122 hard-coded colours replaced by tokens; dark banner and purple provenance styles removed). No UI library was added. C1/C2/C4 pages were not touched except the shared "Component N" chip on `LecturerHome` cards (removed for all cards) and the lecturer menu `end` flag so "Batch marking" and "Marking review" are no longer both highlighted on the batch page.

## 4. Prototype artefacts removed or replaced
- "AdaptiveLearnSE Component 3 …" subtitles and the "AdaptiveLearnSE • Component 3" badge (student, batch, queue); `pipeline_version • Component 3` badge; "Evaluated via F1–F4 pipeline"; "Function 1 lexical overlap … baseline-v1"; "Function 2" wording in the feedback summary (rewritten in the UI as "The automatic marking proposed …").
- "PP1 Demo", "Curriculum Benchmarks", "Automated Test Fixtures", "Controlled PP1 Benchmark Scenario": queue filters are now **All / Student submissions / Sample assessments (/ Test data only when such records exist)**, backed by the real provenance fields.
- Emoji buttons, `alert()` (3), `window.confirm` (1), ~200 inline styles in the batch page, raw preset ids as buttons, "Component N" chips, dark gradient banner.
- Prefilled fake form defaults in the batch setup (a sample architecture question and two sample criteria): the setup form now starts blank; examples are explicit, optional "Start from an example" buttons and example CSV rows are labelled "not real students".
- User-hostile errors ("Ensure the C3 Python AI service is running on port 8003") replaced by `friendlyError` messages (no ports, addresses or stack text; verified in the browser with a mocked 502).
Kept on purpose: real statuses **Awaiting review / Reviewed / Finalized / Failed**, shown by `StatusPill` from backend state only.

## 5. Pages redesigned
1. **Student** (`AssessmentPage`): task title, assessment picker (cards), question + answer form (MCQ radio group), loading text "Marking your answer…", inline validation, retry on failure, result view, "My submissions" table + detail. No reference answer, rubric, expected concepts or answer-key editor; "Insert an example answer" button for written assessments only (MCQ deliberately has none so the key cannot be inferred).
2. **Batch Marking**: four-step `Stepper` (Assessment setup → Student answers → Validate and confirm → Results and review), inline field errors (title, question, marks, rubric sum, MCQ options/correct), CSV or row entry, check summary with skipped rows listed, marking progress, results table with filter/search, review dialog (accept / change with reason / finalize), finalize-all behind a confirm dialog, past batches list. Presentational code moved to `batch/SetupForm.jsx` and `batch/Panels.jsx`; the page keeps state and handlers.
3. **Marking Review queue**: stats, source and status filters, search, empty state with "Clear filters", error with "Try again".
4. **Review page**: automatic mark vs your mark, status, recorded reason, accessible "Change the mark" dialog (label, bounds, reason required, focus return), finalize confirmation, reviewer/time fields from the backend.
5. Shared: `AssessmentResult` (mark card, feedback, criteria, concepts, map), `ConceptDiagnosis` (filter tabs, word-overlap bars), `MindMapGraph` (tokens, keyboard-focusable nodes, list alternative, accepts both the Python and the in-app MCQ response shape so MCQ results no longer risk a crash).

## 6. Functional, security and accessibility changes
- **Backend (contract changes, tested):** `GET /api/v1/c3/assessments` (login required; question + options only), `GET /api/v1/c3/examples` (lecturer/admin only; examples with keys and rubrics), and **student submission detail now redacts `reference_answer`, `expected_concepts`, `rubric` and `correct_options`** (they were returned to students before; found during this audit). Frontend `presets.js` (which shipped every answer key and rubric to all browsers) was deleted; the student bundle now contains only sample answer text.
- Student request body is exactly `{demo_id | batch_id, student_answer | selected_option_id}` (verified by intercepting the browser request).
- Accessibility: labelled inputs, `aria-invalid`/`aria-describedby` + `role="alert"` on field errors, real `<button>`s and tab roles/`aria-pressed`, focus-trapped dialogs with Escape and focus return, `aria-current` stepper, table captions/`scope`, visually-hidden labels, SVG nodes focusable with Enter/Space, list alternative for the map, `prefers-reduced-motion` handling for the spinner, token colours for contrast in light/dark.

## 7. Backend and integration issues found (not fixed unless stated)
1. FIXED: student could read reference answer/rubric/key of their own submission via `GET /submissions/:id`.
2. FIXED: answer keys and rubrics bundled in the student JavaScript (`presets.js`).
3. OPEN: after an MCQ attempt the result text/explanation names the correct option ("does not match the answer key (B)") — kept as post-attempt feedback; students can repeat demo assessments without limit.
4. OPEN: admins can open lecturer URLs directly and the backend authorises review/finalize/batch for `admin`; there is no admin C3 page or menu item. Policy decision for the owner; not extended.
5. OPEN: raw proxy endpoints `/c3/analysis|marking|feedback|mindmap` accept any authenticated user (unused by the UI); no review-history array (only reviewer, time, reason of the last review); `finalize-all` accepts unreviewed results as the automatic mark (the confirm dialog now says so); AUDIT-B9 (JSON 404/error middleware).
6. Observed (C1, not C3): with an empty local fixture database the C1 `DashboardPage` throws a runtime error ("Cannot convert undefined or null to object") after student login. Excluded from C3 results; it did not occur on any C3 page.
7. The Node MCQ engine names its concept nodes "Key: B" and the single concept "B"; shown to lecturers only after the redesign.

## 8. Files changed
Frontend: `pages/c3/{AssessmentPage,LecturerBatchMarkingPage,LecturerQueuePage,LecturerReviewPage}.jsx`, `pages/c3/components/{CriterionCard,ConceptDiagnosis,MindMapGraph}.jsx`, new `components/{AssessmentResult,c3ui}.jsx`, new `batch/{SetupForm,Panels}.jsx`, new `samples.js`, `c3.css`, deleted `presets.js`, `services/c3Api.js`, `config/menus.js`, `pages/lecturer/LecturerHome.jsx`. Backend: `controllers/c3Controller.js`, `routes/index.js`, `services/assessmentConfig.js`, `services/submissionService.js`, `tests/c3_audit.test.js`. Test assets (outside the app): `reports/c3_remediation/ui_tests/*`, `ui_screenshots/*`. A temporary `frontend/vite.uitest.config.js` used for the test server was deleted afterwards.

## 9. Automated results (executed after the changes)
| Check | Result |
|---|---|
| `npx vite build` (frontend) | succeeds |
| Backend `npm test` | 97 tests: **95 pass, 0 fail, 2 todo** (AUDIT-B9). New: assessments list, examples staff-only, student detail redaction |
| C3 Python `pytest` | 334 passed, 13 xfailed, 0 failed (unchanged) |
| Backend `npm run lint` | 15 errors, all pre-existing and none in files changed here (C1/C3 legacy plus 5 in the merged C4 module) |
| Frontend lint / unit tests | none exist in the project |

## 10. Browser and API verification — HISTORICAL first run, superseded for lecturer analysis by section 14 (real Chrome via playwright-core, local MongoDB, real C3 Python service)
Environment: a separate backend on :3100 against a **local** MongoDB container (not the shared Atlas database), Vite dev server on :5174, seeded test accounts (student `IT10000001`, lecturer `SLIITLEC101`, admin `SLIITADMIN1`), the running C3 service on :8003. Raw results of that first run: `ui_tests/browser_results_historical_72.json` (72 checks, 72 passed) and `ui_tests/api_permission_matrix_historical.json`; the current run is `ui_tests/browser_results.json` (79 checks, section 14). Scripts: `ui_tests/ui.mjs`, `ui_tests/e2e.mjs` (password via `C3_TEST_PASSWORD`). Screenshots: `ui_screenshots/`. Several earlier runs failed and drove fixes (see section 11).

## 11. Workflow coverage matrix (actual results)
Status key: Passed / Failed / Blocked / Not Tested / Not Applicable. IDs refer to `browser_results.json`.
### Student
| Route | Action → expected | Components / endpoint (permission) | Problems before → change | Test and result | Status |
|---|---|---|---|---|---|
| `/c3` | Open page: title + assessment choices | `AssessmentPage`; `GET /c3/assessments` (any role with login) | author console, component badge → picker, clean header | S1, S2 | Passed |
| `/c3` | Answer form shows no reference answer, rubric, key | `AssessmentPage` | preset data and rubric editor exposed → removed | S3 + API-leak | Passed |
| `/c3` | Submit empty → inline error, no request | form | alert-style error → inline `role=alert` | S4 | Passed |
| `/c3` | Submit a written answer → mark, criteria, concepts, map, "Awaiting review" | `AssessmentResult`; `POST /c3/assess` (student; body `demo_id` + answer) | dark banner, jargon → mark card, plain labels | S5, S6 (body keys verified) | Passed |
| `/c3` | Open concept node → evidence; list alternative | `MindMapGraph` | colours hard-coded, no keyboard → tokens, focusable | S7 | Passed |
| `/c3` | MCQ: choose option, submit | `POST /c3/assess` | | S8 | Passed |
| `/c3` | My submissions: list, open detail (no reference answer) | `GET /c3/submissions`, `/:id` (own only) | | S9, API-redact | Passed |
| `/c3` | Finalized by lecturer → "Final result", lecturer mark, reason | same | | S16 | Passed |
| `/c3` | API 502 on submit → friendly message + retry, no ports/stack | `friendlyError` | raw backend text → plain message | S10 | Passed |
| `/c3` | Assessment list fails → retry | `Notice` | | S11 | Passed |
| `/lecturer*`, `/c3/batch`, `/c3/review`, `/admin*` | Direct URL as student → redirected to student home | `area()` route guard | | S12a–g | Passed |
| `/c3` | Responsive 375/768 px; dark theme; keyboard reaches cards | CSS | | S13, S14, S15 | Passed |
| any | Browser page errors on C3 pages | | | S-console (C1 dashboard errors excluded, see 7.6) | Passed |
| `/c3` | Retry/recovery after leaving mid-assessment, long-answer limits | | | not exercised | Not Tested |
### Lecturer
| Route | Action → expected | Components / endpoint (permission) | Problems before → change | Test and result | Status |
|---|---|---|---|---|---|
| `/lecturer` | Overview without "Component N" | `LecturerHome` | chips → removed | L1 | Passed |
| `/lecturer/c3/batch` | Header, 4-step stepper, no labels | `PageHeader`, `Stepper` | "Component 3" subtitle, emoji → clean | L2 | Passed |
| batch setup | Empty save → inline errors; rubric ≠ total flagged | `SetupForm` | fake prefilled defaults, no field errors → blank + inline | L3, L4 | Passed |
| batch setup | Save valid setup → answers step | `POST /c3/batch/setup` (lecturer/admin) | | L5 | Passed |
| answers | Example rows → duplicates/empty listed | `POST /c3/batch/validate` | | L6 | Passed |
| marking | Run marking → results with automatic marks | `POST /c3/batch/mark` | no progress text → spinner + text | L7 | Passed |
| results | Review dialog: invalid override errors; valid override saved with reason | `POST /submissions/:id/review` | alert() errors → inline | L8 | Passed |
| results | Finalize one; finalized cannot be edited | `POST /submissions/:id/finalize` | | L9 | Passed |
| dialog | Escape closes, focus returns | `Dialog` | custom overlay, no focus handling | L10 | Passed |
| results | Finalize all: confirm, cancel keeps, confirm finalizes all | `POST /batch/:id/finalize-all` | `window.confirm` | L11, L12 | Passed |
| past batches | List and reopen | `GET /c3/batch/setup` | | L13 | Passed |
| MCQ batch | Setup, check, mark, inspect without page errors | `mcqMarkingService` shape → `MindMapGraph` | likely crash on MCQ map shape → normalised | L14 | Passed |
| `/lecturer/c3` | Queue lists student + batch submissions; filters; search; empty state | `GET /c3/submissions` | "PP1 Demo" tabs → Source/Status filters | L15, L16 | Passed |
| `/lecturer/c3/:id` | Review page: validation, accept, finalize confirm | review/finalize endpoints | | L17 | Passed |
| `/lecturer/c3` | Queue API failure → notice + Try again | `Notice` | | L18 | Passed |
| `/admin*`, `/c3` | Lecturer direct URL → redirected | route guard | | L19a–c | Passed |
| both pages | 375/768 px, dark theme | CSS | table overflow found and fixed | L20, L21 | Passed |
| any | Review history beyond last reviewer/reason | backend has no history array | | not available | Not Applicable |
| any | Scanned-answer/OCR upload | rejected by backend (400) | | no UI by design | Not Applicable |
### Admin
| Route | Action → expected | Endpoint (permission) | Test and result | Status |
|---|---|---|---|---|
| `/admin` | Landing; menu has no marking item | admin role | A1 (menu: Learning insights, Lecturer approvals) | Passed |
| `/admin/lecturers` | Approvals page loads | admin module | A2 | Passed |
| `/lecturer/c3`, `/lecturer/c3/batch` | Direct URL renders the lecturer pages in the lecturer layout | route guard allows admin; backend allows admin | A3, A4 (observed, not a designed admin feature) | Passed (observation) |
| `/c3` | Admin redirected away from the student page | `area('student')` | A5 | Passed |
| API | Admin: list batches 200, read any submission 200, assess as student 403 | see matrix | API-14, 15, 16 | Passed |
| any | Dedicated admin C3 dashboard / oversight page | does not exist | not invented | Not Applicable |
### API permission checks (direct HTTP with each role's token)
Unauthenticated `GET /c3/assessments` 401; student: own key/rubric rejected 400, review/finalize/batch create/mark/list 403, `/c3/examples` 403, another student's submission 403; lecturer: list/examples 200; admin: batch list 200, submission read 200, assess-as-student 403 (API-1…17, API-leak, API-redact).

## 12. Problems found by testing and fixed during this work
MCQ examples button flow, a stray absolute-positioned hidden label that created page-wide horizontal scroll at 375 px on the queue, concept pills showing list bullets, status pills wrapping, a clipped "Review" column, duplicate sidebar highlight, jargon in the feedback summary, and the "New batch" tab not starting a new batch (tab renamed "Mark a batch"; the explicit "New batch" button resets).

## 13. Remaining limitations and deferred work
- Not run: automated accessibility scanner (axe), screen-reader testing, real devices/other browsers (only headless Chrome with viewport emulation), the theme toggle button itself (theme was set through the same `data-theme` attribute), C3→C1 event sync from the browser, real Atlas data, concurrency/two-lecturer scenarios in the browser, very large cohorts and long answers.
- Dark/light visual review was done on the screenshots listed above only.
- Mind map is a star graph; word-overlap "semantic" analysis is lexical (unchanged backend behaviour).
- Open backend items in section 7. Frontend has no lint or unit-test setup; browser tests live outside `src` and need Chrome, a local MongoDB, the C3 service and `C3_TEST_PASSWORD`.

---

## 14. Second pass: complete lecturer analysis, MCQ redaction and the "Assessments unavailable" error (2026-10-21, later)

**The 72/72 browser result in sections 10–11 is historical evidence for the first redesign only. It does not cover anything in this section.** The new run is reported separately in 14.7 (`ui_tests/browser_results.json`, 79 checks); the old file is kept as `browser_results_historical_72.json`.

### 14.1 What was missing (root causes)
| Page | Gap found | Cause |
|---|---|---|
| Lecturer review page | Nothing was rendered, with no explanation, when a submission had no saved `ai_evaluation`; warnings hidden | frontend (empty `{}` fallback, `showSummary={false}`) |
| Batch inspect dialog | Student's **question and submitted answer not shown** at all | frontend (context panel lived inside the hidden summary block) |
| All roles, MCQ | **MCQ feedback never displayed** although it exists | frontend mapping (MCQ returns `feedback.summary/strengths/...`, the view read only `feedback.overall_feedback`) |
| All roles, MCQ | "Concept diagnosis: B" and a "Key: B" map presented as analysis | frontend labelling (the MCQ engine only maps option ids) |
| **Student MCQ views** | **Correct option disclosed** in the live response and in history: `correct_option_ids`, `correct_labels`, rubric descriptor, explanation ("answer key (B)"), feedback ("Authoritative key: Option B"), concept name, map node | **backend** (security) |
| Subjective results | Nothing missing: the Python response contains criteria + evidence, concept matches, feedback, relationships and is stored whole in `c3_results.ai_evaluation` | none |

So: frontend mapping/rendering for the lecturer gaps, backend for the student key leak.

### 14.2 Feature comparison (verified in code, component tests and browser)
Legend: ✔ shown from real data; N/P = not produced for that assessment type (explicit note shown); — not applicable.
| Feature | Student result | Student history detail | Lecturer review page | Batch inspect dialog | Queue |
|---|---|---|---|---|---|
| Awarded/proposed mark and maximum | ✔ | ✔ | ✔ (decision panel) | ✔ | ✔ table |
| Criterion marks, rubric level and evidence (written) | ✔ | ✔ | ✔ | ✔ | — (opens review page) |
| Per-criterion explanation | ✔ | ✔ | ✔ | ✔ | — |
| Concept diagnosis D/P/M (written) | ✔ | ✔ | ✔ | ✔ | — |
| Feedback (written) | ✔ | ✔ | ✔ | ✔ | — |
| Concept map with relationships (written) | ✔ | ✔ | ✔ | ✔ | — |
| MCQ: outcome, marks, feedback | ✔ (no key) | ✔ (no key) | ✔ + answer-key match table | ✔ + answer-key match | — |
| MCQ: concept diagnosis / map | N/P (note) | N/P (note) | N/P (note) | N/P (note) | — |
| Submitted answer next to the analysis | ✔ | ✔ | ✔ | ✔ (was missing) | snippet |
| Proposed vs lecturer/final mark | status card | status card (+ override reason) | two-panel with reason | two-panel | automatic + final columns |
| Review/finalization status | ✔ pill | ✔ pill | ✔ pill | ✔ pill | ✔ pill |
| Analysis not saved | explicit notice | explicit notice | explicit notice | explicit notice | — |

### 14.3 Changes
- **One analysis renderer.** `pages/c3/analysis.js` (`normaliseEvaluation`, pure) classifies the saved evaluation (`subjective | mcq | none`), maps both feedback shapes to the same sections and gives every missing part a reason; `AssessmentResult` renders it for the student page, review page and batch dialog (props `showMarkCard`, `showContext`). New `Unavailable` component. `CriterionCard` hides sentence evidence for MCQ. No duplicate concept/feedback/map code.
- **Review page and batch dialog:** submitted answer, decision panel, notes, feedback, criteria with evidence/explanation, concept diagnosis, concept map (or explicit unavailable notes). The batch table action is now **"View analysis"**; the dialog contains the same analysis plus the question and submitted answer. Override/finalize behaviour is untouched.
- **MCQ for lecturers:** "Answer key match" table (selected vs correct, result) and the stored feedback; concept diagnosis and map replaced by "Not produced for multiple-choice questions" (no more "concept B" / "Key: B" map).
- **Backend redaction** (`services/redaction.js`): for `role === 'student'` the MCQ evaluation is rebuilt from the outcome only (correct / not correct / unanswered, marks); `correct_option_ids`, `correct_labels`, descriptor/explanation/feedback text, concept names and map are removed (`analysis`/`mindmap` = null, `redacted: true`). Applied to the `/assess` response and `GET /submissions/:id` for students; **the stored record is unchanged**; lecturers and admins receive the full evaluation; subjective results are untouched; no permission was changed.
- **"Assessments unavailable — We could not find that item."** Traced to HTTP **404** on `GET /api/v1/c3/assessments`. The backend process you are running (PID 26292, `npm start` → `node src/server.js`, started 10/20 10:15, no watch mode) was started **before** that route existed (`routes/index.js` changed 10/21 19:15), so the request fell through to Express' 404. Root cause: stale backend process, not data. **Action needed from you: restart the backend (`npm run dev` in `backend/`).** In the UI a 404 on this list now says the server probably runs an older version and to restart it, never shows an empty list as success, and "Try again" really re-requests (the list is cleared to the loading state and the endpoint is called again; verified in the browser by failing the first calls with 404 and then allowing the retry).
- Small UI fixes: duplicate "Concept map" heading removed when unavailable; punctuation in the review panel text.

### 14.4 Data-flow trace (actual field names)
`POST /c3/assess` (written) → Python response: `marking.criteria_results[{criterion_id, awarded_mark, max_marks, selected_level_*, rubric_descriptor, evidence_sentence_ids, explanation, warnings}]`, `analysis.{sentences, concept_matches[{concept,status,overlap_score,evidence_sentence_ids}]}`, `feedback.{criteria_feedback[], overall_feedback.{overall_summary, overall_strengths, overall_missing_concepts, overall_improvement_suggestions, overall_next_level_improvements}}`, `mindmap.{nodes, relationships, root_node_id}`; stored whole as `c3_results.ai_evaluation`; `getSubmissionDetail` returns it (normalising legacy `ai_result`), with student redaction. MCQ (Node `mcqMarkingService`): `marking.criteria_results` (one criterion), `analysis` (option ids as "concepts"), `feedback.{summary, strengths, missing_concepts, misconceptions, actionable_guidance, rubric_alignment}`, `mindmap.{nodes, edges}`, plus `correct_option_ids/labels`.

### 14.5 Tests added (real captured responses)
- **Backend** (`c3_audit.test.js`): MCQ key absent from the student's live response and history for a correct and an incorrect attempt (key phrases and fields); stored evaluation and lecturer view still complete; subjective results unchanged by redaction. Backend suite: **99 tests, 97 pass, 0 fail, 2 todo** (AUDIT-B9).
- **Frontend component tests** (`frontend/tests/analysis.test.mjs`, run with `npm test` in `frontend/`; esbuild + `react-dom/server`, no new dependency) on responses **captured from the running C3 service** (`frontend/tests/fixtures/*.json`): written answer in lecturer/inspect mode (answer, criteria evidence, every concept status, feedback, map), MCQ lecturer view, MCQ student live/history redaction (raw JSON and rendered text), null / `{}` / empty analysis, partial analysis (no feedback/map, empty concept list), proposed vs reviewed vs finalized labelling. **7 of 7 pass.**
- **Browser** (Chrome via playwright-core, local MongoDB, real C3 service): new steps S17, S19, L22–L24, L26, L27 plus all earlier steps re-run.

### 14.6 Other results after the fixes
C3 Python tests **334 passed, 13 xfailed, 0 failed** (no Python change); `vite build` succeeds; backend lint 15 errors (all pre-existing, none in changed files).

### 14.7 New browser run (separate from the historical 72/72): 79 checks, 79 passed, 0 failed
Rendered results inspected from screenshots: written-answer review page and batch inspect dialog (all sections), MCQ review page for a lecturer (answer-key match, MCQ feedback, not-produced notes), student MCQ result (no key, not-produced notes), no-analysis fixture, 375 px review page (`ui_screenshots/lecturer_15…19`, `student_09`, `student_11`).
New workflows verified: queue → open subjective submission → submitted answer + criteria/evidence + concepts + feedback + map (L23); batch results → "View analysis" → same sections including submitted answer, marks and status (L22); MCQ in review page and dialog (L14, L24); a submission inserted **without** `ai_evaluation` shows "No analysis available … No analysis was saved for this submission" plus the submitted answer, no fabricated map, no page error (L26); 375 px review page has no horizontal overflow, the map scrolls inside its container and the list fallback exists (L27); student MCQ live result and history contain none of the key phrases and no map (S17); assessments 404 → explicit message → Try again → list (S19). Override bounds/reason, single and bulk finalize confirmation, role/URL redirection and the API permission matrix were re-run unchanged and pass.

### 14.8 Remaining gaps
- **Not produced by the model:** concept diagnosis and concept map for multiple-choice questions (the engine only knows option ids); concept-to-concept relationships for written answers (the map is a star); feedback wording is the service's templated text.
- After an MCQ attempt a student still learns **whether** the option was correct (and can repeat demo assessments); only the correct option itself is withheld. There is no configurable reveal policy yet.
- The raw proxy endpoints `/c3/analysis|marking|feedback|mindmap` (unused by the UI) still return unredacted MCQ results to any authenticated user.
- Not tested: automated accessibility scan, screen readers, other browsers or real devices, C3→C1 sync from the browser, legacy documents in the shared Atlas database (the "no analysis" case was tested with a local fixture document only), very large concept maps (more than about 30 nodes).
- Your running backend must be restarted to pick up `/c3/assessments`, `/c3/examples` and the redaction.

---

## 15. Third pass: security hardening, finalize policy and re-run (2026-10-21, later still)

**The 79/79 result in section 14.7 is historical.** The latest run is `ui_tests/browser_results.json`: **106 checks, 106 passed, 0 failed** in the latest verified run (2026-10-22; it includes the 35-check API permission matrix, three standalone API checks, steps S20, L28, L28b, L29 from reports 18 and 19, and S1b and S21 for the no-preselection behaviour). The 103-check run before it and the 99-check run reported here earlier are kept, unmodified, as `ui_tests/browser_results_historical_103.json` and `browser_results_historical_99.json`. It was produced on an isolated local MongoDB, a local backend and the real C3 Python service. An earlier attempt (run12) was cut off before writing results and is not counted.

What changed for users and what was verified in the browser:
- **Lecturer batch results.** The bulk button is now **"Finalize reviewed"**. Its confirmation says that only reviewed results become final and unreviewed ones stay pending. With nothing reviewed it shows the server message "No reviewed results to finalize: n results are still waiting for review" (step L11b); after the lecturer accepts the remaining results in the dialog, it finalizes them and every row shows *Finalized* (L12). Previously this button finalized unreviewed results as accepted.
- **Student view.** Unchanged in layout. The history detail no longer contains the keys `reference_answer`, `expected_concepts`, `correct_options` or `rubric` at all (they used to be present as null); MCQ results still carry no correct-option information (S17).
- **Assessment picker.** The "Assessments unavailable — We could not find that item." case was re-verified: a 404 shows the explicit "restart the backend" message and "Try again" re-requests the list (S19). The cause remains a stale backend process; restart it with `npm run dev` in `backend/`.
- **Permissions (API matrix, new rows):** the four raw analysis endpoints answer 403 for student and admin, 401 anonymous, 400 for a lecturer reaching validation; an unknown C3 path answers a JSON 404; students cannot call `finalize-all`.
- Not covered by the browser: rate limiting and oversize payloads (verified at API level, see report 14), accessibility scanners, screen readers, other browsers.
