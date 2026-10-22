# C3 engineering and security audit (2026-10-21)

Scope: Component 3 only (`backend/src/modules/c3/**`, `frontend/src/pages/c3/**`, `frontend/src/services/c3Api.js`, `ai-services/c3/**`, C3 tests and reports). C1, C2, C4 and shared files were not modified in this pass (shared files modified in earlier tasks are listed in section 9 and await a decision).

This is an evidence-based review of one prototype. It is **not** an OWASP, SOLID, accessibility or production-readiness certification. Every "fixed" item names its test; every claim about behaviour was demonstrated over real HTTP against an isolated local stack before the fix, and again after.

Status vocabulary: FIXED AND TESTED / FIXED BUT NOT FULLY TESTED / OPEN / DEFERRED / BLOCKED / NOT TESTED.

## 1. Executive summary
Before the fixes, a student could call the four raw analysis endpoints; `POST /c3/marking` with a self-supplied key graded an MCQ and returned the correct options; `finalize-all` finalized results nobody had reviewed; there was no rate limit and no answer-length limit; unknown C3 paths returned HTML; 5xx messages carried the internal AI-service URL. All of these were reproduced first (`security_evidence/before_fix_http_probe.txt`) and are now fixed and covered by tests (`security_evidence/after_fix_http_probe.txt`). Remaining high-priority gaps are in shared code (open CORS, no global body limit, HTML for malformed JSON, no login rate limit) and are BLOCKED pending approval.

## 2. Endpoint × role matrix (direct API calls; permitted and denied)
Verified by `c3.test.js`, `c3_audit.test.js`, `ui_tests/e2e.mjs` (35 API checks) and `functional.mjs`.
| Endpoint | Anonymous | Student | Lecturer | Admin |
|---|---|---|---|---|
| `POST /c3/analysis`, `/marking`, `/feedback`, `/mindmap` | 401 | **403** (was 200) | 200 (400 without `student_id`) | 403 (shared `resolveStudentId` refuses admins) |
| `POST /c3/assess` | 401 | 200 (server-held assessment only; own config/key rejected 400) | 200 with `student_id` | 403 |
| `GET /c3/assessments` | 401 | 200 (no keys/rubrics) | 200 | 200 |
| `GET /c3/examples` | 401 | 403 | 200 | allowed by route guard (not separately executed) |
| `GET /c3/submissions` | 401 | own only | all | all |
| `GET /c3/submissions/:id` | 401 | own only (other → 403/404), redacted | 200 full | 200 full |
| `POST /c3/submissions/:id/review`, `/finalize` | 401 | 403 | 200 | 200 |
| `POST /c3/batch/*`, `finalize-all` | 401 | 403 | owner only (other lecturer 403/404) | all |
| unknown `/c3/*` | 401 | JSON 404 | JSON 404 | JSON 404 |

## 3. Findings
| # | Finding | Evidence before | Fix | Test | Status |
|---|---|---|---|---|---|
| S1 | Raw analysis endpoints open to students; MCQ marking with a self-supplied key = self-grading oracle (no persistence) | probe: student 200, `correct_labels` returned | `requireRole('lecturer')` on the four routes | student 403 on all four incl. MCQ-key payload, no AI call made; anonymous 401; lecturer 200; admin 403 | FIXED AND TESTED |
| S2 | Student MCQ responses must not reveal the key | historical finding, re-verified | student view is an explicit allowlist built from the outcome (`redaction.js`); protected keys are now **absent** (not null) in `GET /submissions/:id` | exact field-set contract tests for `/assess`, list and detail; value checks (no key letters, labels, rubric, reference) | FIXED AND TESTED |
| S3 | `finalize-all` finalized unreviewed results (decision defaulted to accepted) | probe: 2 finalized, reviewed=0 | only `reviewed` results are finalized; 409 when none; `{finalized_count, skipped_unreviewed_count, already_finalized_count}`; conditional update per result; `finalized_by` recorded; UI text updated | none reviewed, mixed, repeated, concurrent, admin, student; browser L11b/L12 | FIXED AND TESTED |
| S4 | No rate limit on model-triggering routes | probe: 60 rapid calls, 0 × 429 | per-user fixed-window limiter in `modules/c3/middleware/rateLimit.js`, `C3_RATE_LIMIT_PER_MIN` (default 60, 0 disables), 429 + `Retry-After` | unit test + HTTP probe (10 × 200, then 429) | FIXED AND TESTED (per-process memory: not shared across instances) |
| S5 | No input size limits | probe: 81 000-char answer accepted | `services/limits.js`: answer 20 000 chars, batch 500 rows, options 20, criteria 20, concepts 50, title 200, question 5 000 → 413 (long batch row → invalid row) | unit tests + probe (413) | FIXED AND TESTED |
| S6 | Unknown C3 paths returned HTML; 5xx errors exposed internal AI URL; unexpected errors returned raw messages | probe | C3 JSON 404 fallback and error middleware; URLs masked, status-less errors generic | unit tests (no `127.0.0.1` in error) | FIXED AND TESTED |
| S7 | Cross-student and bad-id access | hypothesis | none needed (already denied) | other student 403/404, empty history, `xyz`, zero id, traversal and JSON-operator ids → 4xx, never 500 | VERIFIED, no defect (note: `/c3/submissions/../../etc/passwd` is normalised before the router and returns the shared HTML 404) |
| S8 | MCQ attempts/reveal policy | demo assessments repeatable without limit; correctness (boolean) shown | **no approved policy exists in the proposal, AGENTS.md or contracts, so none was invented** | – | OPEN (product decision). Smallest follow-up: per-assessment `max_attempts` and `reveal_policy` on batch setups |
| S9 | Malformed JSON → HTML 400 page; unknown non-C3 paths → HTML 404 | probe | needs a global handler in shared `app.js` | AUDIT-B9a/b stay `todo` | BLOCKED (shared file) |
| S10 | `cors()` open, default 100 kB body limit only, no helmet, no login rate limit | `app.js` read | shared `app.js` / auth module | – | BLOCKED (shared file) |
| S11 | No review history | functional run F-C7 | append-only `review_history` ($push) on review/finalize/finalize-all; staff only | unit test; F-C7, F-H2 after restart | FIXED AND TESTED |
| S12 | Processing time not recorded (NFR-C3-08) | functional run F-B9 | `processing_time_ms` | unit test; F-B9 | FIXED AND TESTED |
| S13 | Frontend dependency advisories | `npm audit --omit=dev` (frontend): 2 moderate (react-router-dom/react-router). Backend: 0 | shared dependency, not touched | – | OPEN (shared) |
| S14 | Secrets | scan of `frontend/dist`, the diff and C3 files for key/URI/private-key patterns: no match; env var **names** used by C3 backend: `AUTH_SECRET`, `C3_AI_URL`, `C3_AI_TIMEOUT_MS`, `C3_RATE_LIMIT_PER_MIN` | – | – | VERIFIED (pattern scan only) |
| S15 | Logging of student data | `console.*` in C3 backend logs only `err.message` strings (4 places), no answer text | – | – | VERIFIED |

## 4. Behaviour decision for `finalize-all`
Sources checked: proposal FR-C3-40/41 and the human-in-the-loop principle ("the lecturer retains authority over the final verified assessment result"), `AGENTS.md`, `C3_API_AND_INTEGRATION_CONTRACTS.md`, and single `finalize` (already requires a prior review). Policy implemented: bulk finalization may only apply decisions the lecturer already made. Behaviour change for users: the button is now "Finalize reviewed"; unreviewed results stay pending and are reported.

## 5. SOLID and architecture (observations, not a compliance claim)
- **SRP.** `c3Controller.assessAnswer` resolves configuration, runs marking, persists and projects for the role in one function; `submissionService` mixes persistence and DTO shaping. Risk: moderate (policy lives in several places). **DEFERRED**: the proposed `assessmentWorkflow` service and single `projectForRole` policy were not implemented in this pass; the security fixes were kept minimal and covered by tests first. The role projection is at least centralised for evaluations in `redaction.js`.
- **OCP.** MCQ vs subjective is decided by `isMcqPayload`/`isMcqEvaluation`; adding a type means touching several `if`s. Not changed.
- **LSP/ISP.** Not applicable to this plain-function code.
- **DIP.** `getDb()` and `fetch`-based `aiClient` are used directly; tests substitute a fake DB and an HTTP stub, which works but is not an injected interface.
- **Python.** Duplicate request-building helpers remain recorded in `reports/c3_pp1_comprehensive_audit/solid_findings.csv`; not changed (no coverage-justified refactor in this pass).

## 6. AI / RAG safety
RAG is a library and offline harness, not on the `/assess` path; its corpus is TRAIN-only and marking output stays `pending_review`. Marks come from explicit rubric levels. No live LLM is used by the API (providers REAL only; live comparison BLOCKED by credentials/quota). Prompt-injection into an LLM marker is therefore not exercised; answer text is only tokenised by the lexical engine. HTML in answers is stored as typed; React escapes it on display (no script execution observed).

## 7. Frontend, accessibility, performance (evidence limits)
Verified in Chrome: keyboard operation (Tab, Escape, dialog focus), role redirects, dark theme, 375/768 px, no horizontal overflow. Not done: automated accessibility scan, screen-reader test, other browsers. Bundle: `vite build` ok (JS 449 kB, 129 kB gzip). Backend list endpoints are capped (queue 100); `listSubmissions` does two queries (no N+1); c3 collections have no explicit indexes (OPEN, low, until volume grows). Informal latency median 24 ms (n=20, lexical path).

## 8. Test results (latest verified 2026-10-21 unless marked historical)
| Suite | Command | Result |
|---|---|---|
| Backend | `npm test` | 115 tests: 112 pass, 0 fail, 3 todo (AUDIT-B9a, B9b, B10); this report was first written at 113 / 111 / 2 todo |
| Frontend components | `node --test tests/*.test.mjs` (frontend) | 10/10 (7/7 when first written) |
| Frontend build | `npx vite build` | ok |
| C3 Python | `pytest -q -p no:cacheprovider` | **historical**: 334 passed, 13 xfailed, 0 failed when first written; 342 passed, 13 xfailed after the experiment tests were added; not re-run in the latest audit |
| Browser | `e2e.mjs` | 106/106 (35-check API matrix plus 3 standalone API checks included); 103/103 in the run before it and 99/99 when first written, kept as `browser_results_historical_103.json` and `browser_results_historical_99.json` |
| Lint | `npm run lint` | **historical**: 15 errors (unchanged count; pre-existing, none introduced); not re-run since |
| C4 compatibility | `node --test src/modules/c4/tests/*.test.js` | **historical**: 72/73 without `AUTH_SECRET`; 73/73 with it; not re-run since |

The 106/106 browser result replaces (does not extend) the earlier 105/105, 103/103, 99/99 and 79/79 runs; older result files are kept as `*_historical_*.json`.

## 9. Shared files (outside C3 ownership)
Modified in **earlier tasks** and still uncommitted, preserved unchanged by this pass; each needs an explicit keep/revert decision:
| File | Diff | Purpose | Impact on C1/C2/C4 |
|---|---|---|---|
| `frontend/package.json` | adds `"test": "node --test tests/*.test.mjs"` | runs the C3 component tests | none at runtime; `npm test` in `frontend/` only runs `tests/*.test.mjs` (C3 tests today) |
| `frontend/src/config/menus.js` | lecturer menu `end: true` on "Marking review"; card text for C3 changed | stops "Marking review" staying active on `/lecturer/c3/batch`; clearer text | `end` only affects the C3 entry; text change is on the C3 card |
| `frontend/src/pages/lecturer/LecturerHome.jsx` | removes `<span className="chip">{s.owner}</span>` | no "Component N" labels in user-facing screens | **visible for C1, C2, C4 cards too** (their owner chip disappears) |
| `CLAUDE.md` | +2 lines of project notes | guidance for future sessions | none at runtime |
Already committed earlier with approval: `backend/src/middleware/auth.js` (AUTH_SECRET mandatory — see the C4 test effect in section 8), `.gitignore`.

BLOCKED shared changes (for approval): global CORS allow-list, `express.json({limit})`, JSON 404/error handlers in `app.js`, login rate limit, helmet. Proposed patch for `app.js` (not applied): `app.use(express.json({ limit: '200kb' }))`, a final 404 handler returning `{error}`, and an error handler mapping `entity.parse.failed` to 400 JSON. Affected: all components (any module's HTML error pages become JSON).

Proposed `CLAUDE.md` note (not applied): finalize-all policy, raw endpoints lecturer-only, `C3_RATE_LIMIT_PER_MIN`, `processing_time_ms` and `review_history`.

## 10. Remaining risks
1. Shared-app gaps in S9/S10. 2. MCQ attempt/reveal policy undecided (S8). 3. Rate limiter is per process. 4. No human-validated marking accuracy; semantic marking is lexical (FR-C3-09 FAIL). 5. C4 test depends on `AUTH_SECRET` being set (section 8). 6. No automated accessibility scan.

## 11. Proposed commit groups (nothing has been committed or pushed)
Only C3-owned files; shared files are listed separately above.
1. **fix(c3-backend): lecturer-only raw endpoints, reviewed-only finalize-all, limits, rate limit, audit trail**
   `backend/src/modules/c3/controllers/c3Controller.js`, `routes/index.js`, `services/{assessmentConfig,batchMarkingService,submissionService}.js`, new `services/{limits,redaction}.js`, new `middleware/{errorHandling,rateLimit}.js`, `tests/{c3.test.js,c3_audit.test.js}`.
2. **feat(c3-frontend): redesigned C3 pages, shared analysis renderer, component tests**
   `frontend/src/pages/c3/{AssessmentPage,LecturerBatchMarkingPage,LecturerQueuePage,LecturerReviewPage}.jsx`, `c3.css`, `analysis.js`, `samples.js`, `batch/{Panels,SetupForm}.jsx`, `components/{AssessmentResult,ConceptDiagnosis,CriterionCard,MindMapGraph,c3ui}.jsx`, deleted `presets.js`, `frontend/src/services/c3Api.js`, `frontend/tests/analysis.test.mjs`, `frontend/tests/fixtures/*.json` (6 files).
3. **docs(c3): audit reports and reproducible test scripts**
   `reports/c3_remediation/{13_c3_frontend_ux_audit.md,14_c3_engineering_security_audit.md,15_c3_functional_requirements_audit.md,c3_functional_requirements_matrix.csv}`, `reports/c3_remediation/ui_tests/{README.md,e2e.mjs,functional.mjs,ui.mjs,capture.mjs}`. Optional (needs approval): result JSONs under `ui_tests/` and `security_evidence/*.txt`. Not proposed: `ui_screenshots/`.
Excluded: `.claude/settings.local.json`, `scratch/`, `backend/seed_users.js` (contains a demo password), `frontend/public/evidence_*.html`, `scripts/generate_evidence_screenshots.py`, `scripts/sync_verified_screenshots.py`, `frontend/vite.uitest.config.js` (temporary, to be deleted).

---

## 12. Final pre-commit review (2026-10-21): findings only, nothing implemented or committed

### 12.1 FR-C3-09 paraphrase marking: reproduced (real C3 service, rubric `arch-full`)
Rubric: criterion C1, max 4; L0 none, L2 at least one of three required concepts, L4 all three. Expected marks for E1–E3 follow only from that text.
| Fixture | Answer (short) | Expected | Actual | Concepts |
|---|---|---|---|---|
| E1 | exact phrases for all three | 4 | **4** | 3 demonstrated |
| E2 | "The system is made of components." | 2 | **2** | components only |
| E3 | irrelevant | 0 | **0** | none |
| P1 | "…overall organisation of a system: its parts and how they connect to each other." | exploratory (a reader would credit all three ideas) | **0** | none |
| P2 | "A system is built from several parts." | exploratory | **0** | none |
| P3 | "It is the big-picture layout of the whole system." | exploratory | **0** | none |

**Cause (code):** `services/semantic/analyzer.py::_match_concepts` uses `token_overlap_score(concept, answer_tokens)` (`services/semantic/baseline.py`): the share of the concept's own tokens found in the answer. A paraphrase shares no token, so every concept is `not_demonstrated`. `reference_similarity` is computed (0.32 for P1 vs 0.19 for the irrelevant answer) but never used for marking.

**Proposal (not implemented): lecturer-authored concept aliases.** A new optional field `concept_aliases: {concept: [alias, ...]}` next to `expected_concepts` (concept names stay plain strings, so rubric `required_concepts`, the marking engine and existing tests are unchanged). Overlap becomes the maximum over the concept text and its aliases; evidence sentences use the same rule; the result records which alias matched. No aliases means identical behaviour.
- Expected behaviour: P2 with aliases `components: ["parts","modules"]` gives components demonstrated and mark 2 (rubric L2); E1–E3 unchanged; P1 would need aliases for all three concepts to reach 4.
- Limitations: these are lecturer-declared synonyms, **not** semantic understanding; coverage depends on the aliases supplied; broad aliases (e.g. "system") can over-credit; wording nobody anticipated still scores 0. Embedding-based matching remains the research follow-up (threshold chosen on the validation split only, one report on test; the earlier model comparison showed a length-only model beating TF-IDF/SBERT).
- Affected C3-owned files: `ai-services/c3/app/schemas/analysis.py` (and the marking/assessment request schemas that carry `expected_concepts`), `services/semantic/analyzer.py`, `services/assessment/orchestrator.py` and `services/marking/marking_engine.py` (pass the field through), `backend/src/modules/c3/services/batchMarkingService.js` (validate/persist), optionally `frontend/src/pages/c3/batch/SetupForm.jsx`, plus Python and backend tests. FR-C3-09 stays FAIL until implemented and tested.

### 12.2 FR-C3-33 relationships: feasibility
`services/mindmap/relationship_builder.py` creates only root-to-concept `child` links ("Deterministic baseline structural attachment"; its comment says co-occurrence was deliberately not used). Available inputs: concept status, overlap score, per-concept `evidence_sentence_ids`. Rubrics and setups contain no relationship data, so prerequisite or part-of relations cannot be derived without inventing them.

Evidence-backed co-occurrence is feasible, checked on the real service: the answer "Software architecture defines the high-level structure of a system. It is made of components and the relationships between them." gives evidence high-level structure [1], components [2], relationships [2] (components and relationships share sentence 2); the answer "Components exist. Relationships also matter. The high-level structure is key." gives [3], [1], [2] (no shared sentence, so no link).

**Proposal (not implemented):** a `co_mentioned` link between two demonstrated/partial concepts only when they share an evidence sentence, with the sentence id and text as evidence, labelled in the UI as "mentioned together", not as a semantic relation; no shared sentence means no link. Limitation: it says nothing about how the concepts relate. Lecturer-authored `concept_relations` or LLM-derived relations are the next options (the latter blocked). FR-C3-33 stays FAIL and FR-C3-34 PARTIAL until a change is approved, implemented and tested.

### 12.3 C4 test and `AUTH_SECRET` (C4 code untouched)
| Configuration | Command | Result |
|---|---|---|
| none | `env -u AUTH_SECRET node --test src/modules/c4/tests/*.test.js` | 73 tests, 72 pass, 1 fail (`simProxy.test.js:306`, "AUTH_SECRET is not set") |
| test-only value | `AUTH_SECRET=<throwaway> node --test ...` | 73/73 |
| supported `.env` path | `node --env-file=.env --test ...` (`backend/.env` defines the variable; value not shown) | 73/73 |
| C3 + middleware under a test value | `AUTH_SECRET=<throwaway> npm test` | historical (earlier run): 113 tests, 111 pass, 0 fail, 2 todo; the later 115-test count above is the latest |

`backend/.env.example` already lists `AUTH_SECRET=`. The failure is a configuration requirement of the earlier approved `auth.js` change; the supported ways to run the C4 tests are an environment variable or `--env-file`. No C4 file was changed.

### 12.4 File-by-file review of the proposed commits
Checks: ownership, necessity, secret patterns (key, URI, private key, hard-coded password), absolute paths, debug output. No secret or credential pattern was found in any proposed file (`backend/seed_users.js`, which contains a demo password, is excluded). `console.*` in the C3 backend only logs `err.message`.

**Group 1, backend (all under `backend/src/modules/c3`, C3-owned):** `controllers/c3Controller.js` (guards, limits, timing, safe errors), `routes/index.js` (role guards, limiter, 404/error middleware), `services/assessmentConfig.js` (server-side config, public list, examples), `services/batchMarkingService.js` (finalize policy, limits, timing, history), `services/submissionService.js` (student redaction, history), new `services/limits.js`, `services/redaction.js`, `middleware/rateLimit.js`, `middleware/errorHandling.js`, `tests/c3.test.js`, `tests/c3_audit.test.js`. All necessary; verdict: include.

**Group 2, frontend (C3-owned):** `pages/c3/{AssessmentPage,LecturerBatchMarkingPage,LecturerQueuePage,LecturerReviewPage}.jsx`, `c3.css`, `analysis.js`, `samples.js`, `batch/{Panels,SetupForm}.jsx`, `components/{AssessmentResult,ConceptDiagnosis,CriterionCard,MindMapGraph,c3ui}.jsx`, `services/c3Api.js`, `tests/analysis.test.mjs`, six fixtures, deleted `presets.js`.
- **`presets.js` deletion (342 lines):** no importer remains (grep over `frontend/src` and `backend/src`); it embedded answer keys, rubrics, reference answers and sample answers in the browser bundle (29 matching lines). The server-side bank `backend/.../data/demoAssessments.js` (answers removed) and `samples.js` (lecturer examples via the staff-only API) replaced it. Recoverable with `git show HEAD:frontend/src/pages/c3/presets.js`.
- **The six fixtures are new files, not deletions.** Used by `analysis.test.mjs`: `mcq_lecturer_detail`, `subjective_lecturer_detail`, `mcq_student_live`, `mcq_student_detail`. **Not used by any test:** `subjective_student_live.json`, `subjective_student_detail.json` (optional: drop, or add a test). **Stale:** `mcq_student_detail.json` was captured before the allowlist change and still has null-valued `reference_answer`, `expected_concepts`, `correct_options` and `rubric` keys; the test still passes (no key leak) but the fixture no longer matches the current contract. Recapture with `ui_tests/capture.mjs` on the isolated stack before committing. All fixtures contain only the test account id `IT10000001` and no credentials.

**Group 3, docs/scripts:** `reports/c3_remediation/{13,14,15}*.md`, `c3_functional_requirements_matrix.csv`, `proposed_shared_app_patch.md`, `ui_tests/{README.md,e2e.mjs,functional.mjs,ui.mjs,capture.mjs}`. Scripts read the password from `C3_TEST_PASSWORD` only; they contain `localhost`/`127.0.0.1` test URLs and one absolute path to the backend `package.json` (used to load the `mongodb` driver), which is acceptable but machine-specific. **Optional (need approval):** `ui_tests/*.json` result files, `*_historical_*.json`, `security_evidence/*.txt`. **Not proposed:** `ui_screenshots/`, `scratch/`, `frontend/public/evidence_*.html`, the two `scripts/` evidence files, `backend/seed_users.js`, `.claude/settings.local.json`.

### 12.5 Status
Nothing in section 12 changes a matrix row. FR-C3-09 FAIL and FR-C3-33 FAIL remain; the alias and co-occurrence changes are **proposed**, not implemented.
