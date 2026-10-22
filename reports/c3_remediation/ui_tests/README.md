# C3 browser and API tests (playwright-core + system Chrome)

Not part of the app build. They drove the verification in `../13_c3_frontend_ux_audit.md` and `../18`/`19`.
These scripts **write** to the database behind the backend they drive (accounts' submissions, batches, reviews). They refuse to run unless an isolated local test database is configured explicitly (see "Safety guard").

## Prerequisites (all local)
- A disposable local MongoDB (for example `docker start mongodb`) and a database name such as `adaptivelearnse_c3_ui`; seed the test accounts into it with `backend/seed_users.js` (run with `MONGO_URI` and `MONGO_DB` set to the local values, because the seeder also reads `backend/.env` for anything you leave unset) and set `diagnostic_completed: true` in `mastery_state` for the test student.
- The C3 Python service on :8003 and a backend started with **`MONGO_URI` and `MONGO_DB` set to the same local database** (for example `MONGO_URI=mongodb://127.0.0.1:27017 MONGO_DB=adaptivelearnse_c3_ui PORT=3100 C3_AI_URL=http://127.0.0.1:8003 node src/server.js` in `backend/`). Started without those variables the backend reads `backend/.env`, which points to the shared database; the guard detects that and aborts.
- A Vite dev server on :5174 proxying `/api` to :3100 (use a temporary config outside the shared `vite.config.js`).
- `npm i playwright-core` in a scratch folder next to a copy of these scripts (the repository has no Playwright dependency), and Chrome (`C3_CHROME_PATH` overrides the default Windows path).

## Required environment variables (no defaults)
| Variable | Rule |
|---|---|
| `C3_TEST_DB` | must match `^adaptivelearnse_c3_[a-z0-9_]{2,40}$`; names such as `adaptivelearnse_dev` are refused |
| `C3_TEST_MONGO_URI` | `mongodb://` with loopback hosts only (`127.0.0.1`, `localhost`), no credentials; `mongodb+srv://` is refused |
| `C3_API_BASE` | loopback `http://` URL, for example `http://localhost:3100/api/v1` |
| `C3_WEB_BASE` | loopback `http://` URL, for example `http://localhost:5174` (required by `e2e.mjs`) |
| `C3_TEST_PASSWORD` | password of the seeded test accounts; never printed |
Optional: `C3_BACKEND_DIR` (folder with `backend/package.json`, only needed when the scripts are copied out of the repository, used to load the `mongodb` driver), `C3_CHROME_PATH`.

## Safety guard (`guard.mjs`)
Imported first by `e2e.mjs`, `functional.mjs`, `capture.mjs` and `ui.mjs`. Failure exits with **code 2** and a message naming the failed check; nothing falls back to `backend/.env` or any shared database, and nothing is dropped or reset.
1. *Environment checks* (no network, no database): a variable is missing, the database name or URI breaks the rules above, or a base URL is not loopback `http://`.
2. *Isolation proof* (before the first test write), `verifyIsolation()`: the local database must already contain the seeded test student; a uniquely named **canary student** with a random password is inserted into that database only, the guard logs in as that canary through the backend, and removes it again. A backend that is unreachable, or is connected to another database, does not know the canary, so the login fails and the run aborts with nothing executed. The real test credentials are never sent to a backend whose database is not yet proven.
Remaining limitation: the guard cannot see how the backend was started. A backend started without explicit local `MONGO_URI`/`MONGO_DB` falls back to `backend/.env` (the shared database); the guard then refuses to run, but that backend is already connected to the shared database, and the guard's single failed canary lookup reaches it (a read of a non-existent random id, no real account). Always start the backend with explicit local `MONGO_URI` and `MONGO_DB`; do not rely on the guard to catch a wrongly started backend.
`guard.test.mjs` tests the environment checks without any service: `node --test guard.test.mjs` (9 tests).

## Running
`node e2e.mjs <output-dir>` writes `results.json`, `api_matrix.json` and screenshots. `functional.mjs`: `node functional.mjs phase1 out.json`, restart the backend, `node functional.mjs phase2 out2.json out.json`. `capture.mjs <dir>` captures live responses used as `frontend/tests/fixtures`.

## Files
`e2e.mjs` (browser + API permission checks; 106 checks in the latest verified run, 2026-10-22; 105 and 103 in the runs before it), `functional.mjs` (API-level requirements run, controlled fixtures, results in `functional_phase*.json`), `ui.mjs` (launch/login helpers), `capture.mjs`, `guard.mjs`, `guard.test.mjs`, `browser_results.json` / `api_permission_matrix.json` (latest verified run), `*_historical*` (earlier runs of 72, 79, 99, 103 and 105 checks, kept unmodified).
