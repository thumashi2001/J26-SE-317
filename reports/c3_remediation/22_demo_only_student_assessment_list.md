# Student assessment list: demo assessments only (2026-10-22)

C3-owned files only; nothing staged, committed or pushed; `.gitignore`, `.git/info/exclude`, C1/C2/C4 and shared files untouched; no lecturer data deleted. This supersedes the grouping described in reports 18 and 21 (lecturer-created group and badge), which are kept as dated records.

## Change
- **API** `GET /api/v1/c3/assessments` (`services/assessmentConfig.js::listPublicAssessments`): returns only the 7 built-in demo assessments from `data/demoAssessments.js` (`kind: 'demo'`, questions, options as `option_id/label/text`, maximum marks; no keys or rubrics). The query of active lecturer batches was removed. `integrations.c2.available: false` is unchanged. `controllers/c3Controller.js` needed no change.
- **Consumers inspected before changing the contract:** the only consumer is `frontend/src/pages/c3/AssessmentPage.jsx` (via `c3Api.listAssessments`). Lecturer batch pages use the separate `/c3/batch/*` endpoints, which are untouched.
- **Student page** (`AssessmentPage.jsx`, `c3.css`): one group "Demo assessments (practice examples)" with a **Demo** badge per card; the "Set by your lecturer" group, "Lecturer-created" badge and the `.c3-source-badge.lecturer` style are gone; the submit body is always `{ demo_id }`; nothing is preselected; "Choose an assessment to start." and the notice "C2 assessments are not available yet. The assessments currently shown are demo assessments." remain (the notice no longer mentions lecturer-created assessments). The empty-state text no longer mentions a lecturer.
- Questions, answer submission, marking, feedback and mind maps are unchanged. Lecturer batch data in MongoDB is untouched (a backend test checks the setup is still stored).

## Tests (fresh, this pass)
| Command (working directory) | Result |
|---|---|
| `npm test` (`backend`) | 115 tests: 112 pass, 0 fail, 3 todo (AUDIT-B9a, B9b, B10) |
| `node --test tests/*.test.mjs` (`frontend`) | 10 pass, 0 fail |
| `npx vite build` (`frontend`) | built |
| Browser suite `e2e.mjs` behind the isolation guard, disposable local database `adaptivelearnse_c3_demoonly` (dropped afterwards) | 105 checks, 105 passed, 0 failed; API matrix 35/35 |
Updated tests: backend "GET /assessments lists only the built-in demo assessments…" (7 demo items, no `batch` kind, an existing lecturer batch is not listed and stays stored, no key fields) and the older picker test (demo only); browser **S20** (a lecturer batch exists via the API yet no lecturer group/badge/title is shown; exactly one demo group of 7 Demo cards; nothing preselected; C2 notice; no protected text; a demo MCQ is selected, submitted, result without key) and **S21** (two different demo cards open their own questions); **S1b** unchanged. The previous run is kept as `ui_tests/browser_results_historical_105_before_demo_only.json`. Not re-run: C3 Python, functional suite, C4.

## Files changed (C3-owned)
`backend/src/modules/c3/services/assessmentConfig.js`, `backend/src/modules/c3/tests/c3_audit.test.js`, `frontend/src/pages/c3/AssessmentPage.jsx`, `frontend/src/pages/c3/c3.css`, `reports/c3_remediation/ui_tests/e2e.mjs`, result files `browser_results.json` / `api_permission_matrix.json` (now run20) plus the new historical copy and local screenshots, this report.

## Remaining limitations
- **Student submission to a batch is still possible by id.** `POST /c3/assess` still accepts `{ batch_id }` from any student for an active lecturer batch (that server path, used by existing tests, was not requested to change). The page no longer lists or offers batches, but a student who knows an id can submit. The eligibility problem (AUDIT-B10) is therefore reduced, not solved: the todo test now targets this submit path. Removing or restricting student `batch_id` submissions is a separate, small C3-only decision for you.
- C2 integration and an enrolment source are still missing (BLOCKED).
- Batch-based student flows (a lecturer sharing a batch with students) no longer exist in the UI; lecturers keep using the batch marking studio.
