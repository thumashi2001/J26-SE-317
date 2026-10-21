# 05 Security and regression test results (executed after the changes)

| Suite | Command | Result |
|---|---|---|
| Node backend | `npm test` (backend/) | **93 tests: 91 pass, 0 fail, 2 todo** (before: 90 = 75 pass + 15 todo). Todo left: AUDIT-B9a/b (shared-app 404/error middleware, out of scope) |
| Python C3 | `pytest -q -p no:cacheprovider` | **324 passed, 13 xfailed, 9 deselected, 0 failed** (unchanged; no Python service code was modified) |
| Frontend | `npx vite build` | builds; no frontend test suite exists |
| ESLint (backend) | `npm run lint` | 10 errors (was 13); none introduced |
| ruff (3 new Python files) | `ruff check` | 49 findings, mostly E501 line length; not fixed |
| Dataset v2 | `validate_repaired.py ...v2 --json` | ratio-concentration FAIL 0.766; near-duplicate check pass; derivation-consistency checks fail by design (see 02) |

## New or converted tests (`backend/src/modules/c3/tests`, `src/middleware/tests`)
- AUDIT-B1: unset `AUTH_SECRET` throws (todo removed) — passes.
- AUDIT-B2: re-posting a finalized batch submission is refused (409) — passes.
- AUDIT-B3 / X1: override above total or `"Infinity"` → 400 — pass.
- AUDIT-B4a/b/c: a non-owner lecturer cannot read, mark or finalize another lecturer's batch — pass.
- AUDIT-B5: two concurrent finalize calls → exactly one 200 and one 409 — passes.
- AUDIT-B6: database insert failure → 5xx, nothing persisted, no success body — passes.
- AUDIT-B7a/b/c: operator injection in `status`, `setup_id` → 400 — pass.
- AUDIT-B8 (5 tests): student-supplied key / rubric / max marks rejected (400); unknown demo (404); object `batch_id` (400); MCQ scored against the server key (0/2 and 2/2, `persisted: true`); student submission against a lecturer batch works, ghost batch 404.
- Live Express↔FastAPI test now uses an in-memory db (a failed save is no longer masked); with Python on :8003 all 5 live tests pass.
- Existing tests that posted a student-owned configuration were changed to act as a lecturer (trusted author) for a named student.
- Already covered and still passing: override requires a reason, original `automated_mark` preserved, student cannot read another student's result, students get 403 on review/finalize/batch routes, finalized results return 409 on edit.

## Not tested / limits
No real-MongoDB test (fake db only); no browser test of the student-page change (build only); admin-vs-lecturer batch policy only by code; raw proxy endpoints remain open to any authenticated user (non-persisting, unmetered); rate limiting, CORS, JSON error middleware not addressed.
