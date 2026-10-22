# Student assessment list: source clarity (2026-10-21)

> Superseded in part by report 22: the student page now lists demo assessments only (the lecturer-created group and badge described here were removed).

Scope: C3-owned files only. Nothing staged, committed or pushed; `.gitignore` and `.git/info/exclude` untouched; no C1, C2, C4 or shared file changed; mind-map relationships not implemented; the 22 ignored research results, the backup and all untracked files are preserved.

## 1. Starting state (verified)
Branch `feature/c3-pp1-experiments-20261020`, HEAD `7f39867`, 0 staged files, the 99 untracked files of report 17 plus the new files listed in section 8. The previous inventory (`17_c3_precommit_untracked_inventory.md`) was used as the baseline.

## 2. Where the cards come from (unchanged finding)
`AssessmentPage.jsx` → `listAssessments()` (`c3Api.js`) → `GET /api/v1/c3/assessments` → `listPublicAssessments()`: the server's built-in demo bank (`data/demoAssessments.js`, 7 entries) plus active lecturer setups from MongoDB `c3_batch_setups`. Nothing is read from C2: `backend/src/modules/c2` has no routes and the documented export endpoint does not exist (`backend/src/integration/c2-c3/README.md`, `docs/pp1/INTEGRATION_HANDOFFS.md`: contract defined, runtime pending C2).

## 3. What changed
Ownership check before editing: every file touched is under `backend/src/modules/c3/`, `frontend/src/pages/c3/` or the C3 tests/reports. No shared file was needed.

- **API (`GET /c3/assessments`)** now also returns `integrations: { c2: { available: false, reason: 'No C2 assessment export is available yet' } }`. The items keep their existing `kind` (`demo` or `batch`); no source fields, identifiers or enrolment data were invented.
- **Student page** shows, above the cards, the notice "C2 assessments are not available yet. The assessments currently shown are demo or lecturer-created assessments." (hidden only if the server ever reports `c2.available === true`). Cards are grouped under "Set by your lecturer" (badge **Lecturer-created**) and "Demo assessments (practice examples)" (badge **Demo**). A lecturer batch is never labelled C2. The first visible card is preselected.
- Selection, answer entry and submission code paths are unchanged (`choose`, `submit`, `{ batch_id }` / `{ demo_id }` request bodies).

Core hunks:
```diff
 // assessmentConfig.js
+export const C2_INTEGRATION = Object.freeze({ available: false, reason: 'No C2 assessment export is available yet' });
 // c3Controller.js
-export const listAssessments = handle(async () => ({ assessments: await listPublicAssessments() }));
+export const listAssessments = handle(async () => ({ assessments: await listPublicAssessments(), integrations: { c2: C2_INTEGRATION } }));
 // AssessmentPage.jsx (picker section)
+{!c2Available && (<Notice tone="info">C2 assessments are not available yet. The assessments currently shown are demo or lecturer-created assessments.</Notice>)}
+{[['batch','Set by your lecturer'],['demo','Demo assessments (practice examples)']].map(([kind, heading]) => ... group of .c3-pick cards with data-source and a c3-source-badge ...)}
```

## 4. Student authorization investigation
- The API returns **every active batch to every logged-in student** (`listPublicAssessments` queries `c3_batch_setups` with `status: 'active'` only), and `resolveStudentAssessment` accepts any active `batch_id` from any student.
- The server performs **no eligibility or enrolment check** because none can be made from trusted data: batch setups hold `module_id` (defaulting to SE3010), `lecturer_id`, title, question and marking configuration; the student record holds `semester` but no module or cohort; the shared class-insights page states lecturers are not linked to students yet; no enrolment collection exists in the backend.
- Exposure: a student can see only the question text, options, type, maximum marks and title of other lecturers' active batches, and can submit to them. Verified by test that no key, rubric, reference answer or expected concept is returned. No other student's answers or personal data are exposed through this endpoint.
- Decision: **BLOCKED**, not fixed. A safe C3-only fix would need a trusted enrolment/assignment source (for example a lecturer-selected student list or cohort on the batch setup, or a shared enrolment collection); inventing one is out of scope. Recorded as test `AUDIT-B10` (todo) in `c3_audit.test.js` so the gap stays visible.

## 5. Semantic experiment and research integrity (unchanged)
Retained as exploratory evidence only (author-labelled fixtures, small held-out set, similarity gives false credit to wrong answers, live `/assess` untouched, F1 not validated accuracy; see reports 16 and 17). No metrics were tuned or altered. No mind-map relationship code was written.

## 6. Verification (fresh in this session)
| Command (working dir) | Result |
|---|---|
| `npm test` (`backend`) | 115 tests: 112 pass, 0 fail, 3 todo (AUDIT-B9a, B9b, B10) |
| `node --test tests/*.test.mjs` (`frontend`) | 10 pass, 0 fail |
| `npx vite build` (`frontend`) | succeeds |
| Browser suite `ui_tests/e2e.mjs` (isolated local MongoDB, local backend, C3 service, Vite on a temporary config) | 103 checks, 103 passed, 0 failed; includes API matrix 35/35 |
Not re-run: C3 Python suite (no Python change; last result 342 passed, 13 xfailed), `functional.mjs`. Browser run history: run16 had 5 failures caused by my change of the preselected card (old steps assumed the first card was a demo) and run17 had 2 (a duplicate-title selector and the same assumption in S10); both test steps were corrected, no product behaviour was loosened, and run18 is the passing run.
New browser step **S20** checks: notice text, group headings, 7 demo cards badged Demo, the lecturer batch badged Lecturer-created, no card mentions C2, no protected term in the page text, selecting a lecturer batch and submitting still works and the result shows no key. Backend test "GET /assessments labels every item by its real source…" checks `integrations.c2.available === false`, kinds restricted to demo/batch, 7 demo items, batch listed as batch, no key fields, options reduced to `option_id/label/text`.

## 7. Remaining C2 dependency and blockers
- **C2 assessments cannot be listed**: needs an authorised C2 export with publication status, question, type, maximum marks, rubric breakdown and answer-key isolation, plus a stable assessment identifier. Smallest handoff: a read-only endpoint or documented collection returning the payload of `c2-c3/README.md` section 2.1; C3 would then store `source_system` and `source_assessment_id` on the setup and copy them to submissions.
- **Student eligibility** (module/cohort enrolment) needs a shared source (BLOCKED, section 4).

## 8. Files changed in this task (C3-owned)
Backend: `backend/src/modules/c3/services/assessmentConfig.js`, `controllers/c3Controller.js`, `tests/c3_audit.test.js`.
Frontend: `frontend/src/pages/c3/AssessmentPage.jsx`, `c3.css`, `components/c3ui.jsx`, `LecturerQueuePage.jsx`, `LecturerReviewPage.jsx`, `frontend/tests/analysis.test.mjs` (last four also carry the fixes in report 19).
Tests/evidence: `reports/c3_remediation/ui_tests/e2e.mjs` (S5/S10 select a demo card explicitly; new S20, L28, L28b, L29), `ui_tests/browser_results.json` (103), `browser_results_historical_99.json`, `api_permission_matrix_historical_35.json`, new screenshots (local only).
Reports: this file and `19_lecturer_review_dialog_and_sample_badge_fixes.md`.
