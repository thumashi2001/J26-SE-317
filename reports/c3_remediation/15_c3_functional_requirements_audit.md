# C3 functional requirements audit (2026-10-21)

Scope: Component 3 only. Baseline = the proposal's FR-C3-01..46, NFR-C3-01..30 and specific objectives SO1–SO6 (`Desktop\Reserach\Proposal\IT23227118_EDIRISINGHE T P V K.pdf`, section 5.2–5.3; text re-extracted for this audit). Matrix: `c3_functional_requirements_matrix.csv` (82 rows, one per requirement/objective).

This report states what was **executed** and what was not. Code reading is not counted as execution evidence. Nothing here is a human-validated accuracy claim.

## 1. Result summary (from the matrix)
| Group | Rows | PASS | PARTIAL | FAIL | BLOCKED | NOT TESTED |
|---|---|---|---|---|---|---|
| Functional (FR) | 46 | 33 | 5 | 2 | 6 | 0 |
| Non-functional (NFR) | 30 | 19 | 8 | 0 | 0 | 3 |
| Objectives (SO) | 6 | 3 | 3 | 0 | 0 | 0 |
| **Total** | **82** | **55** | **16** | **2** | **6** | **3** |

A PASS means the behaviour was executed in this audit and matched the expectation stated in the row. It does not mean the research claim behind the requirement is proven.

### Failures (real defects or unmet requirements)
- **FR-C3-09 / SO1 semantic comparison.** A correct paraphrase ("An architecture describes the overall organisation of a system: its parts and how they connect to each other.") earned **0/4**; all three concepts were `not_demonstrated`. Marking is lexical (token overlap). This is the model's real limitation, consistent with the model-comparison report (a length-only model beat TF-IDF/SBERT). Exploratory case: no authoritative expected mark exists, so only the credit/no-credit observation is reported.
- **FR-C3-33 concept relationships.** Every relationship is `child` with the evidence text "Deterministic baseline structural attachment" (a star graph).
- Partial: FR-C3-05 (HTML tags survive in `normalized_answer`; the UI escapes output, no script execution seen), FR-C3-06 (lexical only), FR-C3-08 (reference similarity computed but not used for marks), FR-C3-17 (RAG is a library, not on the `/assess` path), FR-C3-34 (hierarchy is a two-level star).

### Fixed during this audit (each with a regression test)
| Requirement | Defect found by the run | Fix (C3 only) | Test |
|---|---|---|---|
| NFR-C3-08 | No processing time was stored | `processing_time_ms` recorded for `/assess` and batch marking | unit test + functional F-B9 |
| NFR-C3-22 / FR-C3-41 | Only the latest review values survived (no audit trail) | append-only `review_history` (review, finalize, finalize-all); staff-only in responses | unit test + F-C7, F-H2 |
| FR-C3-40 | `finalize-all` finalized unreviewed results silently | finalizes only `reviewed` results, 409 if none, reports `skipped_unreviewed_count`, records `finalized_by` | 5 new tests + browser L11b/L12 |

### Blocked / not implemented (not simulated)
FR-C3-16/19/20 live LLM and RAG-vs-no-RAG (no provider quota or credentials), FR-C3-18 (no RAG in the assessment path), FR-C3-42 C2→C3 (C2 has no routes; `integration/c2-c3` is a README), FR-C3-44 C3→C4 (C4 `c3CodingAdapter` only documents a future contract; no `/c3/exercises` endpoint exists).

### Not tested
NFR-C3-12 (PII minimisation), NFR-C3-15 (ethics/data governance), NFR-C3-30 (usability evaluation with predefined criteria): none can be shown by a software run.

## 2. Test environment and test types
- Isolated stack only: Docker MongoDB (local DB `adaptivelearnse_c3_sec`), backend on :3100, real C3 Python service on :8003, Vite test server on :5174 (temporary config, removed afterwards). The shared Atlas database was never contacted. Credentials were passed through environment variables only.
- Types are kept separate in the matrix: **e2e-api** (real HTTP + real Python + real MongoDB: `ui_tests/functional.mjs`), **browser e2e** (Chrome, `ui_tests/e2e.mjs`), **automated unit/integration** (fake DB, real middleware), **pytest** (offline). Fake-DB tests are not counted as end-to-end.
- Controlled fixtures: the server rubric `arch-full` (criterion C1, max 4: level L0 none, L2 at least one of three required concepts, L4 all three). Expected marks 4/2/0 follow from the rubric text for answers that contain, respectively, all three phrases, one, and none. Paraphrase and markup cases are labelled exploratory.

## 3. Executed runs (this session, real counts)
| Run | Command | Result |
|---|---|---|
| Backend unit/integration | `npm test` (backend) | latest verified 2026-10-21: 115 tests, 112 pass, 0 fail, 3 todo (AUDIT-B9a, B9b, B10); 113 / 111 / 2 todo when this report was written |
| Frontend component tests | `node --test tests/*.test.mjs` (frontend) | latest verified: 10 of 10 (7 of 7 when first written) |
| Frontend build | `npx vite build` | succeeds |
| C3 Python | `pytest -q -p no:cacheprovider` | **historical**: 334 passed, 13 xfailed, 9 deselected, 0 failed when written; 342 passed after the experiment tests were added; not re-run in the latest audit |
| Browser e2e | `ui_tests/e2e.mjs` (Chrome) | latest verified 2026-10-22: 106 checks, 106 passed, 0 failed (105 and 103 in the previous run). The functional-audit run itself was 99/99 (kept as `browser_results_historical_99.json`; an earlier attempt run12 produced no results file and is not counted) |
| API permission matrix (inside e2e) | 35 checks | 35 ok (the 105-check result set also holds three standalone API checks) |
| API functional run | `ui_tests/functional.mjs` phase1 + restart + phase2 | **historical** (not re-run since): 43 records: 38 PASS, 1 INFO (exploratory), 1 FAIL (relationships), 3 BLOCKED |
| Rate-limit probe (:3101, limit 10/min) | `security_evidence/after_fix_http_probe.txt` | 10 × 200 then 429 with `Retry-After: 60` |
| Backend lint | `npm run lint` | 15 errors, same count as before this work (none in files changed here) |
| C4 compatibility (not modified) | `node --test src/modules/c4/tests/*.test.js` | historical (not re-run since): 72 of 73 pass **without** `AUTH_SECRET` in the environment; 73 of 73 with it (see section 5) |

## 4. Workflow coverage (what was actually done)
Student: assessment list, retry on a 404 list, MCQ correct/wrong/unanswered/invalid, written controlled answers, history and detail, redaction of MCQ keys, foreign-submission denial, direct-URL protection, dark theme/375 px/keyboard checks. Lecturer: setup validation, answer check (duplicate/empty rows), batch marking, retry without duplicates, override validation, review, finalize, `finalize-all` (nothing reviewed, mixed, repeated, concurrent, admin, student), past batches, queue filters, review page, "no analysis saved" notice. Admin: oversight reads, denial of student actions, redirects. Integration: C1 `learning_events` provisional→finalized, idempotent on repeat. Persistence: stored results, override audit fields and history survive a backend restart.

## 5. Findings that need a decision
1. **Cross-component effect of the earlier `auth.js` change (already committed with approval).** `signToken` now throws without `AUTH_SECRET`. The C4 test `simProxy.test.js:306` ("auth token allows ready handler…") signs a token and therefore fails when `AUTH_SECRET` is not in the environment; C4 passes 73/73 when it is set. Not modified (C4 is out of scope). Options for the owner: set `AUTH_SECRET` for the C4 test run, or have the C4 test set it.
2. **FR-C3-09 semantic marking** needs a semantic layer; this is research work, not a patch.
3. **Product policy still open:** unlimited demo attempts and boolean correctness for MCQ (no approved reveal policy exists; none was invented).

## 6. Evidence files
`ui_tests/functional.mjs`, `ui_tests/functional_phase1.json`, `ui_tests/functional_phase2.json`, `ui_tests/browser_results.json` (106 in the latest verified run; 99 originally, kept as `browser_results_historical_99.json`), `ui_tests/api_permission_matrix.json` (35), `security_evidence/after_fix_http_probe.txt`, `c3_functional_requirements_matrix.csv`. Raw screenshots are under `ui_screenshots/` (not proposed for commit).

## 7. Limits of this audit
Single local user and database; lexical path only (no live LLM); informal latency (median 24 ms, p95 37 ms over 20 requests, no load test); no screen-reader or automated accessibility scan; no cross-browser or device testing; no human-validated marks; the earlier experiment metrics were not re-run here (only their unit tests).

## 8. Addendum (2026-10-21): follow-up review, no status changed
Report `16_c3_semantic_marking_and_architecture_review.md` adds an **exploratory** semantic-matching experiment (author-labelled fixtures, no human validation) and a verified MongoDB/Neo4j architecture review. Matrix statuses are unchanged: FR-C3-09 and FR-C3-33 remain FAIL, FR-C3-34 PARTIAL; only the `next_action` notes were extended and the changes are labelled as proposed, not implemented. Fresh results since the main run: C3 Python 342 passed, 13 xfailed (334 + 8 new experiment-integrity tests); frontend component tests were 8/8 at that point (10/10 in the latest verified run).
