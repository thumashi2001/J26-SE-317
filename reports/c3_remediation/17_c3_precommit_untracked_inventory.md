# C3 pre-commit review: untracked-file inventory, semantic experiment, mind maps and architecture (2026-10-21)

Proposal only. Nothing was staged, committed, pushed, reset, cleaned, stashed or deleted; `.gitignore` was not changed; no shared, C1, C2 or C4 file was touched. Existing reports are unchanged.

## 1. Current state (verified now)
- Branch `feature/c3-pp1-experiments-20261020`, up to date with its remote; HEAD `7f39867` ("merge: bring Development into the C3 PP1 branch"); 0 staged files.
- 21 tracked-modified entries and **99 untracked files** (`git ls-files -o --exclude-standard`). No modified or untracked path lies under `modules/c1|c2|c4`, `integration/` or `ai-services/c1|c2|c4`.
- Backup `DEVELOPMENT/_git_backups/pre_security_audit_20261021_2209` still present (7 files). It predates this work: the 60 files it archived restore byte-identical (checked previous round); files created later are **not** in it.
- Services during this review: the existing `adaptivelearnse-neo4j` container was left running and untouched; the temporary MongoDB, backend, Vite and throwaway Neo4j used earlier were stopped/removed.

## 2. Classification counts (99 untracked files; per-file table in section 12 and `17_untracked_inventory.csv`)
| Classification | Files | Disposition |
|---|---|---|
| KEEP - C3 deliverable | 31 | proposed C3-only commit groups |
| KEEP - evidence/research | 40 | 39 screenshots + 1 experiment result; retain; screenshots local only |
| KEEP - evidence/research (optional) | 11 | result JSONs, probe outputs, two unused fixtures; need approval to commit |
| EXCLUDE FROM COMMIT - local artifact | 10 | `scratch/` (retain locally) |
| REVIEW REQUIRED | 6 | 4 evidence pages in shared `frontend/public`, 2 scripts in shared `scripts/` |
| SENSITIVE | 1 | `backend/seed_users.js` |
| OTHER COMPONENT/SHARED | 0 untracked (the shared files are tracked-modified: section 9) | |

## 3. Most important untracked files
- **Group 1 (backend):** `middleware/rateLimit.js`, `middleware/errorHandling.js`, `services/limits.js`, `services/redaction.js` (all under `backend/src/modules/c3`). Modified C3 files import them, so committing the modified files without these four breaks the module.
- **Group 2 (frontend):** `frontend/src/pages/c3/{analysis.js,samples.js,batch/*,components/AssessmentResult.jsx,components/c3ui.jsx}` are imported by the modified pages; `frontend/tests/analysis.test.mjs` plus four fixtures it reads.
- **Group 4 (experiment):** `ai-services/c3/experiments/semantic_matching/{fixtures.json,run_eval.py,frozen_config.json,__init__.py}`, the unit test, report 16 and the single results file.
- **Sensitive:** `backend/seed_users.js` holds a hard-coded demo password (value never printed here). Needed locally to seed test users; must not be committed. A local-only exclusion in `.git/info/exclude` (not `.gitignore`) would protect it without a shared-file change; this needs your approval.

## 4. Kept local, not committed
`reports/c3_remediation/ui_screenshots/` (39 PNG, regenerable evidence for report 13), `scratch/` (10 files incl. a 299 KB text extract of research documents and earlier prompts; may contain other members' proposal text, so never commit), `.claude/` (already ignored), the two unused subjective student fixtures, and `reports/c3_remediation/ui_tests/*.json` + `security_evidence/*.txt` unless you approve them as evidence.
**Already ignored but valuable:** `ai-services/c3/experiments/results/*` (exp1–exp5 summaries and raw predictions, pilot results; 22 files in the folder) are ignored, not untracked, so they exist only on this machine and are not in the Git backup. Decide whether they should be preserved (copied to a backup or force-added) before any clean-up elsewhere.

## 5. Files needing your decision (REVIEW REQUIRED)
`frontend/public/evidence_{feedback,integration,mcq_result,model_training}.html`: C3 PP1 evidence pages; two sibling pages (`evidence_evaluation_results.html`, `evidence_test_results.html`) are already tracked and `docs/pp1/*` references them, so they look like the owner's PP1 evidence, but `frontend/public` is a shared folder and Vite serves it publicly. `scripts/generate_evidence_screenshots.py` and `scripts/sync_verified_screenshots.py` generate PP1 screenshot evidence from those pages. They were not created by this audit, are not needed to run any C3 test, and are excluded pending your ownership decision.

## 6. Sensitive-data scan
Pattern scan (API-key shapes, connection strings with credentials, private keys, hard-coded password assignments) over all tracked-modified and untracked files except `scratch/` binaries and screenshots found nothing in the proposed groups. `ai-services/c3/.env` and `.claude/` are ignored. Test scripts take the password only from `C3_TEST_PASSWORD`. The fixtures contain only the test account id `IT10000001`.

## 7. Proposed `.gitignore` change: none required
Machine-local noise (`__pycache__`, `.coverage`, `.ruff_cache`, `.env`, `.claude/`) is already ignored, and nothing genuinely generated is currently untracked-and-unignored. Adding patterns for `reports/`, `*.json`, `scratch/` or fixtures would hide material that must be reviewed. If you want a guard against accidents, the narrow, optional candidates are: `frontend/vite.uitest*.config.js` (temporary test config; matches only that name) and a local `.git/info/exclude` entry for `backend/seed_users.js`. Neither is applied.

## 8. Semantic experiment review
Verified from the files, not from memory:
- **Protocol:** `run_eval select` calls `load_items(("dev","validation"))`; the unit test `test_select_never_loads_the_test_split` asserts it and that no test item reaches scoring. `evaluate` aborts if the fixtures hash differs from `frozen_config.json`. The committed frozen file matches the fixtures (test passes).
- **Disclosed deviation:** the pre-specified negation guard (M3) was found harmful on validation, and M3b (unguarded) was added after seeing validation results only; recorded in `frozen_config.json` (`design_note`) and report 16. No existing threshold or test was altered.
- **Limitations stated in report 16:** author-labelled by construction, no human marker, synthetic text, 21 test answers / 63 judgments with wide intervals, MiniLM accepts all keyword-stuffed and wrong-but-similar answers, the repo dataset quotes concept words verbatim and cannot test paraphrase, live `/assess` unchanged.
- **Recommendation:** retain as an **exploratory research artifact**, separate from production code (it lives under `experiments/`, is imported by nothing in the app). Do not quote its F1 as marking accuracy; the report says so. A human-marker study is the prerequisite for any accuracy claim.

## 9. Shared-file changes (tracked, modified, kept separate and uncommitted)
`CLAUDE.md`, `frontend/package.json`, `frontend/src/config/menus.js`, `frontend/src/pages/lecturer/LecturerHome.jsx` (diffs shown in the previous review; dispositions unchanged). Dependencies of the C3 groups on them: Group 2's tests run with `node --test frontend/tests/*.test.mjs` (8 pass) without the `package.json` script, but `npm test` needs it; the lecturer navigation fix (`end: true`) and the removed "Component N" chip are shared-file edits, so Group 2 works without them with only cosmetic differences.

## 10. MongoDB / Neo4j status verified from source
- Answer maps: `createSubmissionWithResult` stores the full AI response as `c3_results.ai_evaluation`; the map is `ai_evaluation.mindmap`. Collections used by C3: `c3_submissions`, `c3_results`, `c3_batch_setups`. No `mindMaps` collection exists.
- Neo4j: `backend/package.json` has no Neo4j dependency. Schema, two seed files (8 concepts in the live check), loader and `services/cckg/graph_adapter.py` exist. `ai-services/c3/app/main.py` imports the adapter for health/status; the assessment, marking and route modules do not import it, so `/assess` does not use Neo4j. GraphRAG appears only in experiment conditions (blocked: no approved populated CCKG, no LLM access). Live behaviour of the adapter was verified earlier against a throwaway container; not repeated now.

## 11. Mind-map "mentioned together" links: proposal (not implemented)
Defensible for the viva only if presented as evidence of co-occurrence, never as a semantic relation. Representation: `relationship_type: "co_mentioned"`, `source_node_id`/`target_node_id` for the two concepts, `evidence`: text "Both concepts appear in sentence N" plus new optional `evidence_sentence_ids: [N]`, `basis: "same_sentence"`, `is_semantic: false`; created only when both concepts are demonstrated/partial and share an evidence sentence; root→concept `child` links stay structural.
- **C3-owned files:** `ai-services/c3/services/mindmap/relationship_builder.py` (new builder), `services/mindmap/generator.py` (call it), `ai-services/c3/app/schemas/mindmap.py` (optional fields; `relationship_type` is already a free string), tests `tests/unit/test_relationship_builder.py` and `test_mindmap_generator.py`; frontend `pages/c3/components/MindMapGraph.jsx` (dashed edge + "mentioned together" legend and sentence in the evidence panel), `pages/c3/analysis.js`; a recaptured live fixture. Storage needs no change (embedded in `ai_evaluation`). MCQ maps are untouched.
- **Tests:** same sentence → one link with sentence id; different sentences → none; one concept not demonstrated → none; three concepts in one sentence → three pairwise links; deterministic ids; links never contain "prerequisite/causes/part of" wording; UI label test.
- **Limitations / misreadings:** co-occurrence can reflect list-like sentences; says nothing about direction or meaning; a student writing one long sentence gets more links. **Shared files needed: none. C1/C2/C4: none.** Waiting for your approval.

## 12. C3-only change groups and dependencies
1. **Backend (11 files):** modified `controllers/c3Controller.js`, `routes/index.js`, `services/{assessmentConfig,batchMarkingService,submissionService}.js`, `tests/{c3.test.js,c3_audit.test.js}` + 4 new files above. Reproducible with C3 files only plus the already-committed `middleware/auth.js` (needs `AUTH_SECRET` in the environment).
2. **Frontend:** modified pages/components/css, `services/c3Api.js`, deleted `presets.js`, new files above, `analysis.test.mjs` + `mcq_lecturer_detail`, `subjective_lecturer_detail`, `mcq_student_live`, `mcq_student_detail` fixtures. Needs no shared change to build and test.
3. **Docs/scripts:** reports 13–15, `c3_functional_requirements_matrix.csv`, `proposed_shared_app_patch.md`, this report and `17_untracked_inventory.csv`, `ui_tests/{README.md,e2e.mjs,functional.mjs,ui.mjs,capture.mjs}`. The scripts need a local stack and the seeded accounts (not part of the commit).
4. **Semantic experiment (7 files):** `semantic_matching/{__init__.py,fixtures.json,run_eval.py,frozen_config.json}`, `tests/unit/test_semantic_matching_experiment.py`, report 16, `experiments/semantic_matching_results.json`. Needs the cached MiniLM weights to re-run; the unit tests run offline.

## 13. Test evidence
Snapshot taken when this report was written; superseded by the current numbers in reports 18, 19 and 20 (backend 115 / 112 pass / 3 todo, frontend 10/10, browser 105/105 as of 2026-10-22).

| Command (working directory) | When | Result |
|---|---|---|
| `npm test` (`backend`) | snapshot at report 17 | 113 tests: 111 pass, 0 fail, 2 todo (AUDIT-B9) |
| `node --test tests/*.test.mjs` (`frontend`) | snapshot at report 17 | 8 pass, 0 fail |
| `pytest -q -p no:cacheprovider tests/unit/test_semantic_matching_experiment.py` (`ai-services/c3`) | snapshot at report 17 | 8 passed |
| `pytest -q -p no:cacheprovider` (`ai-services/c3`) | earlier this session, after the last code change | 342 passed, 9 deselected, 13 xfailed |
| Browser e2e `e2e.mjs`, API matrix, `functional.mjs` | **historical** (earlier this session; not re-run in this review) | 99/99, 35/35, 43 records (the browser suite has since been re-run: 105/105) |
| C4 suite with a test-only `AUTH_SECRET` | earlier this session | 73/73 (72/73 without it) |

## 14. Separate finding: where the student's assessment cards come from (investigation only)
- **Component:** `frontend/src/pages/c3/AssessmentPage.jsx` (section "Choose an assessment") → `listAssessments()` in `frontend/src/services/c3Api.js` → `GET /api/v1/c3/assessments` → `controllers/c3Controller.listAssessments` → `services/assessmentConfig.listPublicAssessments()`.
- **Actual source:** (a) **local presets**: the hard-coded server bank `backend/src/modules/c3/data/demoAssessments.js` (kind `demo`, 7 entries: 5 written, 2 MCQ), and (b) **MongoDB**: active lecturer setups in `c3_batch_setups` (kind `batch`, "Set by your lecturer"). **Nothing comes from C2.** The cards in the screenshot are the demo bank.
- **C2–C3 contract status:** documented (`backend/src/integration/c2-c3/README.md`, `docs/pp1/INTEGRATION_HANDOFFS.md`: "CONTRACT DEFINED; RUNTIME PENDING C2 UI"); the proposed C2 export endpoint `GET /api/v1/c2/questions/:id/export-c3` does **not** exist: `backend/src/modules/c2` has empty folders and no `routes/index.js`; `ai-services/c2` is an offline dataset toolkit with no HTTP API; the README states C2 does not yet extract rubric criteria. C4 reached the same conclusion (`c2ExamAdapter.js` returns `available: false` with the reason).
- **Gaps in the current list:** demo and lecturer cards are mixed in one grid and the UI does not say that the demo cards are demo data; any logged-in student sees every active batch (no cohort/eligibility model); batch setups have no `source_system`/`source_assessment_id` field to trace a future C2 origin; no message tells the student that C2 assessments are unavailable.
- **Smallest C3-only fix (proposed, not implemented):** (1) API returns `source` = `demo` | `lecturer_batch` | `c2` (reserved; none today) and a top-level `integrations.c2 = {available: false, reason}` using the same wording as C4's adapter; (2) the student page shows "Set by your lecturer" and "Demo assessments (practice examples, not from C2)" as separate labelled groups and one honest line "Assessments from C2 are not available yet"; (3) optional `source_system` / `source_assessment_id` stored on batch setups and copied to submissions so a future C2 handoff stays traceable (additive fields, no schema migration); (4) tests for labelling, absence of keys, and that no demo card is ever labelled C2. **C3-owned files:** `assessmentConfig.js`, `c3Controller.js`, `AssessmentPage.jsx`, `c3.css`, backend/frontend tests. No shared change.
- **BLOCKED (needs the C2 owner):** an authorised C2 export (HTTP or a documented read-only collection) with publication status, rubric breakdown and answer-key isolation; student eligibility (module/cohort enrolment) from a shared source. Until then C2-origin assessments cannot be listed, and none will be faked.

## 15. Blockers and missing approvals
Ownership decision for the four evidence pages and two scripts; approval to commit optional evidence files; approval to implement the assessment-list labelling, the "mentioned together" links, and any `.git/info/exclude` entry; C2 export contract and enrolment source; Neo4j driver, CCKG ontology approval and LLM access for GraphRAG; shared `app.js` hardening; decision on the preserved ignored `experiments/results/*`.

## 16. Complete untracked inventory (99 files; reasons and hashes in `17_untracked_inventory.csv`)
| Path | Bytes | Classification | Group | Referenced by (files) |
|---|---|---|---|---|
| `ai-services/c3/experiments/semantic_matching/__init__.py` | 0 | KEEP - C3 deliverable | G4 semantic experiment | 0 |
| `ai-services/c3/experiments/semantic_matching/fixtures.json` | 30097 | KEEP - C3 deliverable | G4 semantic experiment | 2 |
| `ai-services/c3/experiments/semantic_matching/frozen_config.json` | 9638 | KEEP - C3 deliverable | G4 semantic experiment | 2 |
| `ai-services/c3/experiments/semantic_matching/run_eval.py` | 16083 | KEEP - C3 deliverable | G4 semantic experiment | 0 |
| `ai-services/c3/tests/unit/test_semantic_matching_experiment.py` | 5057 | KEEP - C3 deliverable | G4 semantic experiment | 1 |
| `backend/seed_users.js` | 1966 | SENSITIVE | EXCLUDE | 11 |
| `backend/src/modules/c3/middleware/errorHandling.js` | 847 | KEEP - C3 deliverable | G1 backend | 2 |
| `backend/src/modules/c3/middleware/rateLimit.js` | 1550 | KEEP - C3 deliverable | G1 backend | 4 |
| `backend/src/modules/c3/services/limits.js` | 845 | KEEP - C3 deliverable | G1 backend | 3 |
| `backend/src/modules/c3/services/redaction.js` | 3531 | KEEP - C3 deliverable | G1 backend | 6 |
| `frontend/public/evidence_feedback.html` | 6113 | REVIEW REQUIRED | EXCLUDE pending decision | 2 |
| `frontend/public/evidence_integration.html` | 6197 | REVIEW REQUIRED | EXCLUDE pending decision | 3 |
| `frontend/public/evidence_mcq_result.html` | 6502 | REVIEW REQUIRED | EXCLUDE pending decision | 2 |
| `frontend/public/evidence_model_training.html` | 9384 | REVIEW REQUIRED | EXCLUDE pending decision | 4 |
| `frontend/src/pages/c3/analysis.js` | 4784 | KEEP - C3 deliverable | G2 frontend | 5 |
| `frontend/src/pages/c3/batch/Panels.jsx` | 16413 | KEEP - C3 deliverable | G2 frontend | 2 |
| `frontend/src/pages/c3/batch/SetupForm.jsx` | 8869 | KEEP - C3 deliverable | G2 frontend | 3 |
| `frontend/src/pages/c3/components/AssessmentResult.jsx` | 7610 | KEEP - C3 deliverable | G2 frontend | 5 |
| `frontend/src/pages/c3/components/c3ui.jsx` | 7207 | KEEP - C3 deliverable | G2 frontend | 8 |
| `frontend/src/pages/c3/samples.js` | 961 | KEEP - C3 deliverable | G2 frontend | 3 |
| `frontend/tests/analysis.test.mjs` | 9039 | KEEP - C3 deliverable | G2 frontend | 2 |
| `frontend/tests/fixtures/mcq_lecturer_detail.json` | 4450 | KEEP - C3 deliverable | G2 frontend | 0 |
| `frontend/tests/fixtures/mcq_student_detail.json` | 3165 | KEEP - C3 deliverable | G2 frontend | 1 |
| `frontend/tests/fixtures/mcq_student_live.json` | 1862 | KEEP - C3 deliverable | G2 frontend | 0 |
| `frontend/tests/fixtures/subjective_lecturer_detail.json` | 10115 | KEEP - C3 deliverable | G2 frontend | 0 |
| `frontend/tests/fixtures/subjective_student_detail.json` | 8556 | KEEP - evidence/research (optional) | LOCAL ONLY (excluded from proposed commit) | 1 |
| `frontend/tests/fixtures/subjective_student_live.json` | 7150 | KEEP - evidence/research (optional) | LOCAL ONLY (excluded from proposed commit) | 1 |
| `reports/c3_remediation/13_c3_frontend_ux_audit.md` | 31322 | KEEP - C3 deliverable | G3 docs/scripts | 3 |
| `reports/c3_remediation/14_c3_engineering_security_audit.md` | 22374 | KEEP - C3 deliverable | G3 docs/scripts | 0 |
| `reports/c3_remediation/15_c3_functional_requirements_audit.md` | 8404 | KEEP - C3 deliverable | G3 docs/scripts | 2 |
| `reports/c3_remediation/16_c3_semantic_marking_and_architecture_review.md` | 11728 | KEEP - C3 deliverable | G4 semantic experiment | 1 |
| `reports/c3_remediation/c3_functional_requirements_matrix.csv` | 28566 | KEEP - C3 deliverable | G3 docs/scripts | 2 |
| `reports/c3_remediation/experiments/semantic_matching_results.json` | 11735 | KEEP - evidence/research | G4 semantic experiment | 2 |
| `reports/c3_remediation/proposed_shared_app_patch.md` | 3534 | KEEP - C3 deliverable | G3 docs/scripts | 2 |
| `reports/c3_remediation/security_evidence/after_fix_http_probe.txt` | 1931 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 2 |
| `reports/c3_remediation/security_evidence/before_fix_http_probe.txt` | 2315 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 1 |
| `reports/c3_remediation/ui_screenshots/admin_01_landing.png` | 351241 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/admin_02_lecturers.png` | 66733 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/admin_03_direct_marking_review.png` | 1587497 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_01_overview.png` | 243230 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_02_batch_setup.png` | 176316 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_03_setup_errors.png` | 189530 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_04_check.png` | 115253 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_05_results.png` | 128211 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_06_dialog_override.png` | 141252 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_07_all_finalized.png` | 131041 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_08_past.png` | 142311 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_09_mcq_inspect.png` | 125103 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_10_queue.png` | 1596738 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_11_review_page.png` | 194671 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_12_review_finalized.png` | 199374 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_13_queue_dark.png` | 1632154 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_14_batch_dark.png` | 177966 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_15_batch_inspect_analysis.png` | 315793 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_16_review_analysis.png` | 310022 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_17_mcq_review_analysis.png` | 192331 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_18_no_analysis.png` | 104264 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_19_review_mobile.png` | 283409 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_resp_375_batch.png` | 180902 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_resp_375_c3.png` | 806054 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_resp_768_batch.png` | 183483 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/lecturer_resp_768_c3.png` | 1327068 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_01_landing.png` | 204633 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_02_empty_error.png` | 209033 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_03_result.png` | 446144 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_04_mcq_result.png` | 286303 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_05_history_detail.png` | 170897 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_06_api_error.png` | 232069 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_07_dark.png` | 205967 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_08_finalized_result.png` | 175844 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_09_mcq_result_redacted.png` | 286569 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_10_mcq_history_redacted.png` | 171020 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_11_assessments_404.png` | 88556 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_resp_375.png` | 199734 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_screenshots/student_resp_768.png` | 194736 | KEEP - evidence/research | LOCAL ONLY (excluded from proposed commit) | 0 |
| `reports/c3_remediation/ui_tests/README.md` | 1241 | KEEP - C3 deliverable | G3 docs/scripts | 36 |
| `reports/c3_remediation/ui_tests/api_permission_matrix.json` | 6172 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 2 |
| `reports/c3_remediation/ui_tests/api_permission_matrix_historical.json` | 3039 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 1 |
| `reports/c3_remediation/ui_tests/browser_results.json` | 18893 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 3 |
| `reports/c3_remediation/ui_tests/browser_results_historical_72.json` | 13408 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 1 |
| `reports/c3_remediation/ui_tests/browser_results_historical_79.json` | 14957 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 0 |
| `reports/c3_remediation/ui_tests/capture.mjs` | 1660 | KEEP - C3 deliverable | G3 docs/scripts | 2 |
| `reports/c3_remediation/ui_tests/e2e.mjs` | 43292 | KEEP - C3 deliverable | G3 docs/scripts | 5 |
| `reports/c3_remediation/ui_tests/functional.mjs` | 22073 | KEEP - C3 deliverable | G3 docs/scripts | 3 |
| `reports/c3_remediation/ui_tests/functional_phase1.json` | 13385 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 1 |
| `reports/c3_remediation/ui_tests/functional_phase2.json` | 996 | KEEP - evidence/research (optional) | OPTIONAL (needs approval) | 1 |
| `reports/c3_remediation/ui_tests/ui.mjs` | 1223 | KEEP - C3 deliverable | G3 docs/scripts | 4 |
| `scratch/debug_mock_regex.py` | 1688 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/extract_all_docs.py` | 3125 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/extract_research_plan.py` | 2644 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/extracted_research_corpus.txt` | 298866 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 2 |
| `scratch/print_proposal_pages.py` | 475 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/prompt8.txt` | 4184 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/prompt8_full.txt` | 12093 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/test_length_bias.py` | 1184 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/test_section_extractor.py` | 2258 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scratch/verify_metrics.py` | 3706 | EXCLUDE FROM COMMIT - local artifact | LOCAL ONLY (excluded from proposed commit) | 0 |
| `scripts/generate_evidence_screenshots.py` | 2213 | REVIEW REQUIRED | EXCLUDE pending decision | 3 |
| `scripts/sync_verified_screenshots.py` | 5570 | REVIEW REQUIRED | EXCLUDE pending decision | 3 |

"Referenced by" counts files that mention the file name; 0 for C3 source files such as `run_eval.py`, `__init__.py` and the fixtures means they are loaded by module path or without the extension (for example `fx('mcq_student_live')`), which was checked manually.
