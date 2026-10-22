# Final read-only pre-commit review (2026-10-21)

Read-only audit. Nothing was staged, committed, pushed, reset, cleaned, stashed, reverted or overwritten; no source file, ignore rule, service or database was touched. The only file written is this report. No test was re-executed in this audit: evidence below is read from result files, scripts and hashes, and labelled accordingly.

## 1. Verified Git state
- Branch `feature/c3-pp1-experiments-20261020`, up to date with `origin/feature/c3-pp1-experiments-20261020`; HEAD `7f39867ee463b2ccc6768f1629f794e95f992dec`; **0 staged** files.
- **21 tracked modifications** (20 modified, 1 deleted: `presets.js`; `git diff --stat`: 1,990 insertions, 4,232 deletions) and **107 untracked files** (99 listed in report 17 + 8 added since: reports 17, 17-CSV, 18, 19, two new screenshots, `browser_results_historical_99.json`, `api_permission_matrix_historical_35.json`). This report makes 108. No inventory file has disappeared.
- Untracked by area: 41 screenshots, 27 under `reports/c3_remediation` (non-screenshot), 7 `frontend/tests`, 6 `frontend/src`, 5 `ai-services/c3`, 4 `backend/src`, 4 `frontend/public/evidence_*.html`, 10 under `scratch/`, 2 under `scripts/`, 1 `backend/seed_users.js`.
- No path under `modules/c1|c2|c4`, `integration/`, `ai-services/c1|c2|c4` is modified or untracked. `frontend/src/pages/auth.css`, `backend/src/app.js` and `middleware/auth.js` have no diff. `git diff --check` reports only LF→CRLF warnings (no whitespace errors).
- Backup `DEVELOPMENT/_git_backups/pre_security_audit_20261021_2209` present (7 files; its 60 archived files verified byte-identical earlier). Files created after the backup are not in it. 22 ignored research result files remain in `ai-services/c3/experiments/results/`.

## 2. Review of the three functional changes (diffs and code read, not re-run)
**Lecturer review dialog (`components/c3ui.jsx`, `Dialog`).** `closeRef.current = onClose` is assigned on every render; the keydown handler and the backdrop click call `closeRef.current`; the focus effect now has `[]` dependencies, so initial focus (`[data-autofocus]` or the first focusable) runs once per open and typing no longer re-triggers it. The save path (`LecturerReviewPage.saveOverride`) still validates the mark range and a non-empty reason, stores `decision: overridden`, `new_mark`, `override_reason`; draft state is page-level, so Escape/Cancel keep it. Concerns: (a) focus is set only at mount; a dialog whose content arrives later (the batch inspect dialog shows a spinner first) now focuses its first control at mount and is not re-focused when content loads, which is the same initial behaviour as before for dialogs without `data-autofocus`; (b) the effect captures the dialog node once, correct as long as the node is stable (it is).
**Sample badge.** `.c3-source-badge` is defined in `frontend/src/pages/c3/c3.css` (C3-owned) with `position: static` and no animation; the component never uses the global `.chip`. `auth.css` is unchanged, so the root cause remains in the shared file (a global `.chip { position:absolute; animation }`); any other page that uses `.chip` can still be affected. Overlap with the dialog is checked in browser step L29 (reason box not covered; badge static and in viewport at 1280/375; queue rows at 1280/768/375).
**Student assessment list.** `GET /c3/assessments` returns `integrations.c2 = { available: false, reason: 'No C2 assessment export is available yet' }` from a frozen constant in `assessmentConfig.js`; items keep `kind` `demo` or `batch`; the page groups and badges them from `kind` (Lecturer-created / Demo) and shows "C2 assessments are not available yet. The assessments currently shown are demo or lecturer-created assessments." whenever the server does not report `available: true`. The wording says C2 is not available and does not imply live integration. **Preselection:** `setSelectedId(cur || first batch || first item)` only sets UI state; nothing is submitted until the student presses Submit, and the server still resolves the configuration and authorization on every `/assess` call. Concern: because of the open finding AUDIT-B10 (every student sees every active batch of any lecturer, newest first, limit 50), the preselected card can now be an arbitrary lecturer's newest batch instead of a demo assessment; this changes the established default and increases the chance of answering the wrong assessment. Recommendation: keep it only if you accept that, or revert to "first demo" (or no preselection) until a trusted eligibility source exists. No change was made.

## 3. Test evidence
| Evidence | Status | Verification in this audit |
|---|---|---|
| Backend `npm test`: 115 tests, 112 pass, 0 fail, 3 todo (AUDIT-B9a, B9b, B10) | executed in the previous round; **not re-run now** | test file read: B10 todo retained, new assessments test present |
| Frontend `node --test tests/*.test.mjs`: 10/10; `vite build` ok | executed previous round; not re-run now | `analysis.test.mjs` read |
| Browser suite 103/103 | executed previous round (run18) on isolated infrastructure | `browser_results.json`: 103 entries, 103 Passed, 0 Failed; its SHA-256 equals the saved run18 `results.json` |
| API permission matrix 35/35 | same run | `api_permission_matrix.json`: 35 rows, 35 ok, identical hash to run18; `browser_results.json` shows 38 `API-*` rows = 35 matrix rows + 3 standalone API checks (key leak, redaction, JSON 404) |
| `browser_results_historical_99.json` | the 99-check run (run13) | 99/99; SHA-256 identical to the original run13 results; separate from the current file; older 79/72 files also present and untouched |
| C3 Python 342 passed, 13 xfailed | **historical** (earlier this session, before the last UI/backend changes; Python unchanged since) | not re-run now or in the previous round |
| `functional.mjs` 43 records; C4 73/73 with `AUTH_SECRET` | **historical** | not re-run |
Isolation: `e2e.mjs`, `functional.mjs` and `capture.mjs` target `localhost`/`127.0.0.1` only and no script references Atlas; the Mongo fixtures helper connects to `mongodb://127.0.0.1:27017` and takes the database name from `C3_TEST_DB`. The **backend under test, however, takes its database from its own environment**: started without `MONGO_URI`/`MONGO_DB` overrides it would read `backend/.env` (the shared database). The previous run started it with local overrides; the scripts cannot enforce this, so reproduction instructions must say so (risk, section 6).
Not weakened: existing assertions were only changed where behaviour was deliberately changed and documented: finalize-all policy (L11/L11b/L12), student→lecturer tokens on the raw endpoints (`c3.test.js`), `null` → absent keys for protected student fields. S5 and S10 gained an explicit "choose the first demo written card" click because of the new preselection; no assertion was removed. New steps S20, L28, L28b, L29 and component/static tests were added. Browser L28 uses real keystrokes; the component test for `Dialog` is a static guard only (server rendering cannot run effects) and says so. No result is claimed to prove an untested feature: C2 integration, student eligibility, accessibility scanners, other browsers are not covered.
Documentation inconsistency to fix before committing (needs authorization, not done): `ui_tests/README.md` and reports 13–15 still cite the 99-check run as the latest; 103 supersedes it.

## 4. Proposed change groups (file manifest; nothing staged)
Limit: the latest fixes were made on top of the earlier uncommitted redesign and hardening, in the same files. Without `git add -p` (not permitted) commits can only be split **by file**, so groups A and B cannot be committed apart from the frontend base, and B's backend part sits in the same files as the security work. Honest file-level grouping:

**C: Backend (C3-owned, contains B's API flag).** Dependencies: committed `middleware/auth.js` (needs `AUTH_SECRET`).
| File | State | Why |
|---|---|---|
| `backend/src/modules/c3/controllers/c3Controller.js` | modified | guards, limits, timing, safe errors, `integrations.c2` |
| `…/routes/index.js` | modified | lecturer-only raw endpoints, limiter, 404/error middleware |
| `…/services/assessmentConfig.js` | modified | server-side config, public list, `C2_INTEGRATION` |
| `…/services/batchMarkingService.js` | modified | reviewed-only finalize-all, limits, timing, history |
| `…/services/submissionService.js` | modified | student redaction, review history |
| `…/services/limits.js`, `redaction.js` | untracked | imported by the above |
| `…/middleware/rateLimit.js`, `errorHandling.js` | untracked | imported by `routes/index.js` |
| `…/tests/c3.test.js`, `c3_audit.test.js` | modified | regression tests (incl. AUDIT-B10 todo) |

**A + B (+ redesign base): Frontend (C3-owned).** Depends on group C only for the optional `integrations` field (the page tolerates its absence).
| File | State | Group content |
|---|---|---|
| `frontend/src/pages/c3/components/c3ui.jsx` | untracked | A: Dialog fix, `SourceBadge`; base components |
| `…/LecturerReviewPage.jsx`, `LecturerQueuePage.jsx` | modified | A: badge use; base redesign |
| `…/AssessmentPage.jsx` | modified | B: grouping, badges, notice, preselection; base |
| `…/c3.css` | modified | A+B: `.c3-source-badge` rules; base |
| `…/LecturerBatchMarkingPage.jsx`, `ConceptDiagnosis.jsx`, `CriterionCard.jsx`, `MindMapGraph.jsx` | modified | base redesign |
| `…/analysis.js`, `samples.js`, `batch/Panels.jsx`, `batch/SetupForm.jsx`, `components/AssessmentResult.jsx` | untracked | base redesign (imported by the pages) |
| `frontend/src/pages/c3/presets.js` | deleted | removed keys/rubrics from the bundle |
| `frontend/src/services/c3Api.js` | modified | API wrapper; JSDoc |
| `frontend/tests/analysis.test.mjs` | untracked | 10 component/static tests |
| `frontend/tests/fixtures/{mcq_lecturer_detail,subjective_lecturer_detail,mcq_student_live,mcq_student_detail}.json` | untracked | used by the tests |

**D: Browser tests (optional, only if reproducible).** `reports/c3_remediation/ui_tests/{e2e.mjs,functional.mjs,ui.mjs,capture.mjs,README.md}` (untracked, C3-owned). Reproducible with a local stack, `C3_TEST_PASSWORD` and `C3_TEST_DB`; e2e.mjs contains one absolute machine path (loads the `mongodb` driver). Result JSONs (`browser_results*.json`, `api_permission_matrix*.json`, `functional_phase*.json`) and `security_evidence/*.txt`: optional evidence, commit only if approved.

**E: Semantic experiment (independent).** `ai-services/c3/experiments/semantic_matching/{__init__.py,fixtures.json,run_eval.py,frozen_config.json}`, `ai-services/c3/tests/unit/test_semantic_matching_experiment.py`, `reports/c3_remediation/experiments/semantic_matching_results.json`, `16_c3_semantic_marking_and_architecture_review.md` (all untracked, C3-only). Exploratory; unused by the app.

**F: Reports/requirements.** `reports/c3_remediation/{13,14,15,17_c3_precommit_untracked_inventory,18,19,20}*.md`, `17_untracked_inventory.csv`, `c3_functional_requirements_matrix.csv`, `proposed_shared_app_patch.md` (untracked, C3-only). Update the stale 99-check citations first.

## 5. Must stay out of every commit
Shared tracked modifications: `CLAUDE.md`, `frontend/package.json`, `frontend/src/config/menus.js`, `frontend/src/pages/lecturer/LecturerHome.jsx` (disposition unchanged). Never: `backend/seed_users.js` (demo password), `.claude/`, `scratch/` (10), the four `frontend/public/evidence_*.html` and two `scripts/` files (ownership unclear, shared folders), 41 screenshots (local evidence), the two unused subjective student fixtures (`subjective_student_live.json`, `subjective_student_detail.json`), caches, temporary configs, test databases. `auth.css`, `app.js`, `auth.js` must not be modified by C3.

## 6. Risks, dependencies, blockers
1. Preselected batch may be another lecturer's (section 2); decision needed.
2. File-level commits only; hunk-level separation of A/B/C from the base would require `git add -p` authorization.
3. Reproduction risk: the backend must be launched with local `MONGO_URI`/`MONGO_DB` overrides; otherwise it uses `backend/.env`. Add this warning to the README.
4. Shared `auth.css` `.chip` rule remains; scoping it is the owner's decision.
5. Student eligibility (AUDIT-B10) and the C2 export contract remain **BLOCKED**; C2 integration is not complete and no text in the product claims it.
6. Python suite, functional suite and C4 check are historical; re-run before the final commit if desired.
7. Commit messages: your rule is no Claude co-author trailer and `Vk-Viman` as author; the session's default attribution reminder is overridden by that rule.
8. Line endings: LF→CRLF warnings on many files; `git diff --check` shows no whitespace errors.

## 7. Recommended commit order (after authorization; nothing done)
1. **E** semantic experiment (independent, no app dependency). 2. **C** backend with tests. 3. **Frontend (A+B+base)**. 4. **D** test scripts (+ approved result JSONs). 5. **F** reports, after correcting the 99→103 citations. Push only after a final re-run of backend, frontend, Python and browser suites.
