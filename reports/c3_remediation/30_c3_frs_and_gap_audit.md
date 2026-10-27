# 30 — C3 Functional Requirements Specification and gap audit (2026-10-27)

Read-only audit: no source file was changed to produce this report. Smoke tests were run because they were requested (section 12).
Evidence rule: a status below is backed by an executed test or a file read in this repo. Anything else is marked **Not verified**.

## 1. Executive summary
C3 turns a student answer into a *proposed* mark with evidence: lexical/semantic analysis -> rubric-level marking -> concept diagnosis
-> feedback -> answer-derived mind map -> lecturer review/override -> stored record. Marks come only from explicit rubric levels.
**Working and tested:** input handling, preprocessing, rubric marking with partial credit, concept classes, templated explainable
feedback, mind-map graph + UI, lecturer review/override/finalize with audit history, student redaction, role-based access, C1 hand-off.
**Not achieved:** true semantic matching (paraphrases still fail), typed concept relationships, live LLM/RAG comparison (no credentials),
human-marked ground truth, C2 input and C4 output. The research claim is therefore "an explainable rubric engine with an advisory
fine-tuned estimate", not "semantic AI marking validated against human markers".

## 2. Source inventory
| Source | Status |
|---|---|
| C3 proposal PDF `Desktop\Reserach\Proposal\IT23227118_EDIRISINGHE T P V K.pdf` (FR-C3-01..46, NFR-C3-01..30, SO1-6) | Read earlier in this project; numbering below is that document's |
| Repo `ADAPTIVE_LEARN_SE` (backend, frontend, ai-services/c3, datasets, experiments, reports 01-29) | Inspected |
| `c3_functional_requirements_matrix.csv` (82 rows), `experiment_status_matrix.csv`, report 15 | Read this session |
| Earlier conversation in this project (supervisor-style decisions, PP1 notes) | Only this project's transcript is accessible |
| C1 and C2 proposals, other groups' repos, supervisor/TAF documents beyond what earlier work quoted | **Not re-inspected in this session; not claimed** |
| Live Neo4j / Atlas / LLM provider calls | Not available this session |

## 3. Source-of-truth and conflict log
| # | Conflict | Sources | Impact | Recommended resolution |
|---|---|---|---|---|
| 1 | "Semantic analysis" required vs lexical engine live | Proposal FR-C3-09 vs `services/semantic/baseline.py` | Core objective SO1 only partly met | Keep optional MiniLM layer off by default; decide with supervisor whether a human paraphrase benchmark is required before enabling |
| 2 | Earlier semantic experiment (`experiments/semantic_matching`, report 16, author-labelled fixtures, 21 test answers, chose hybrid M3b) vs my `semantic_concept_eval.py` (tier-labelled dataset, no measured gain) | reports 16 and 28 | Two datasets, two methods, neither human-validated; they do not contradict, they measure different things | Cite both with their labels; do not claim a gain from either |
| 3 | Proposal FR-C3-08 uses reference similarity; the engine computes it but does not use it for marks | proposal vs `matrix` | Intentional: marks must stay rubric-based | Keep as evidence only; record as a decision |
| 4 | Ground truth: proposal says human/reference marks; dataset labels are tier-derived | dataset card, reports 24-25 | Agreement figures are not human agreement | Human validation (report 25) is a prerequisite for any accuracy claim |
| 5 | RAG/multi-LLM are "Should Have" yet drawn in the pipeline | proposal prioritisation vs code | Must not be a dependency | Keep optional; status BLOCKED, not failed |
| 6 | Old matrix marks FR-C3-09 FAIL; optional layer now exists | matrix vs report 28 | Matrix is stale for that row | Keep FAIL for the default path; add note |
| 7 | CLAUDE.md says "93 tests"; current counts are 603 py / 118 backend | CLAUDE.md | Doc drift | Update when next editing CLAUDE.md |

## 4. Functional requirements catalogue (grouped by the 12 areas requested)
Status key: **IMPL+TEST** executed test exists; **PART** partial; **MISSING**; **BLOCKED** needs an outside dependency.
Test IDs refer to the matrix (`FR-C3-nn` rows), `ui_tests/e2e.mjs`, `ui_tests/functional.mjs`, `backend/src/modules/c3/tests`, `ai-services/c3/tests`.

### A. Assessment input and preprocessing (FR-01; FR-C3-01..05, 07)
- *The system shall* accept question, answer, reference, rubric, max marks; validate them; reject malformed input with a clear error; keep the question-answer-rubric-record link.
- Actors: lecturer (setup, batch), student (answer + `demo_id`/`batch_id` only). UI `/lecturer/c3/batch`, `/c3`; API `POST /c3/batch/setup`, `POST /c3/assess`. Priority: Must.
- Acceptance: invalid rubric -> 400, no mark; students cannot send inline rubric/key; empty/duplicate rows flagged.
- Status: **IMPL+TEST** (matrix PASS FR-C3-01,02,03,04,05,07). Gap: HTML tags survive in `normalized_answer` (UI escapes; no script execution seen).

### B. Semantic answer analysis (FR-02; FR-C3-06, 08, 09)
- *Shall* find concepts, compare with reference and expected concepts, recognise equivalent wording, handle empty/short input, never invent evidence.
- Status: **PART**. Default path is token-overlap (lexical, `analysis_version baseline-v1`). Optional MiniLM layer (`C3_SEMANTIC_MATCH=local`, `semantic-v1`) exists, is tested with fakes, and is off by default.
- Smoke result today: the paraphrase "An architecture describes the overall organisation of a system: its parts and how they connect to each other." scores `components` 0.31 and `interactions` 0.19 against threshold 0.5, so **both stay not_demonstrated with the layer on or off**. This is a real limitation; I did not lower the threshold to fit one example.
- Open: human-written paraphrase benchmark; decision on using reference similarity.

### C. Rubric-aware marking (FR-03; FR-C3-10..15)
- *Shall* select a rubric level per criterion, allow partial credit, total the criterion marks, keep marks within max, show evidence per criterion, separate AI proposal from lecturer final mark.
- Status: **IMPL+TEST** (FR-C3-10..14 PASS; FR-C3-15 PASS but LLM/RAG settings are not recorded because they are not used on this path).
- Marks come only from rubric levels (`orchestrator._mark`, test `test_solid_structure.py` and marking unit tests). Confidence is not proof: the AI estimate is advisory and flagged `needs_review` at |difference| > 0.25.

### D. Objective questions (FR-04)
- Deterministic key comparison in `backend/.../mcqMarkingService.js`, kept separate from the written path; students never receive keys.
- Status: **IMPL+TEST** (B full, A zero, none zero, invalid 400; 11 MCQ subtests).

### E. LLM and RAG (FR-05; FR-C3-16..20)
| Approach | State |
|---|---|
| Deterministic MCQ | built and tested |
| Keyword/rule baseline | built, executed |
| Semantic model (SBERT, RoBERTa, TF-IDF heads) | executed on the frozen dataset; RoBERTa best but a length-only model is competitive -> no semantic-skill claim |
| LLM without RAG, with RAG, multi-LLM, GraphRAG | harness and real providers coded; **no results** (Gemini free tier 20 req/day; Groq/OpenRouter keys absent). Status BLOCKED/deferred, not failed |
- RAG library: TRAIN-only corpus, retrieved text kept separate from the student answer, output validated and always `pending_review`. It is **not** on the `/assess` path.
- Do not cite any LLM or RAG performance number; none exists.

### F. Concept diagnosis (FR-06; FR-C3-21..25)
- Classes demonstrated / partially / missing are produced and linked to criteria and evidence sentences (**IMPL+TEST**). "Partial" is a token-overlap rule. The incorrect/contradicted class is not a validated output (**MISSING**; negation probe passed 4/4 only as a manual probe).

### G. Explainable evidence and feedback (FR-07, FR-08; FR-C3-25..31)
- Per-criterion evidence, strengths, missing concepts, suggestions, all consistent with marks (**IMPL+TEST**). Wording is templated; no feedback-quality study exists (**Not verified** for educational quality).

### H. Mind map (FR-09; FR-C3-32..35)
- Machine-readable graph (**IMPL+TEST**) and rendered visualisation (**IMPL+TEST**, listed as separate capabilities). Nodes carry status; missing expected concepts are distinguished from answer concepts.
- **PART/FAIL:** relationships are all `child` with evidence "Deterministic baseline structural attachment" (a star graph). No typed relationships; FR-C3-33 FAIL, FR-C3-34 PART.

### I. Lecturer review (FR-10; FR-C3-36..41)
- Inspect answer, criteria, evidence, concepts, feedback, map; accept/override with reason; append-only `review_history`; `finalize-all` finalizes only reviewed results (**IMPL+TEST**, e2e 106/106 on 2026-10-22).
- A later AI result must not replace a verified one: covered by finalization tests; **re-run of this exact case in this session: Not verified**.

### J. Student results (FR-11)
- Own submissions only, redacted server-side (no AI estimate, no MCQ key, no staff history). Provisional vs finalized status shown (**IMPL+TEST**). Open policy: unlimited demo attempts and what a student may see about MCQ correctness.

### K. Records (FR-12; FR-C3-15, 45, 46)
- MongoDB `c3_*` collections store marks, concepts, evidence, feedback, map, `processing_time_ms`, statuses, history. Gaps: no explicit indexes, no retention period (unresolved, not invented), duplicate workflow tested for batches only.

### L. Integration (FR-13; FR-C3-42..44)
| Link | State |
|---|---|
| C2 -> C3 | **BLOCKED**: C2 has no routes; `integration/c2-c3` is a README |
| C3 -> C1 | **PART/PASS**: direct write to `learning_events`, provisional -> finalized, idempotent; no C1 API contract exists |
| C3 -> C4 | **BLOCKED**: contract only documented in C4 |
| CCKG (Neo4j) | adapter + 5 live tests passed earlier; seed graph has 8 demo concepts |
- No production endpoint is claimed.

### M. Security, errors, evaluation (FR-14, 15, 16)
- Auth/roles: `AUTH_SECRET` mandatory, roles student/lecturer/admin, 35-check permission matrix passed (earlier), batches owner-scoped (**IMPL+TEST**).
- Errors: failed model calls are excluded and counted, a failed save returns 503, no fabricated mark on failure (**IMPL+TEST**). Credentials not logged: **Not verified** by a dedicated log scan.
- Experiments: two-phase protocol with one-shot test scoring (refuses rerun); QWK/MAE/RMSE implemented; latency informal (median 24 ms, p95 37 ms over 20 requests). Human comparison **MISSING**; multi-seed **MISSING** (single seed, 90 test answers).

## 5. Roles and permissions
| Operation | Student | Lecturer | Admin |
|---|---|---|---|
| Submit answer (`demo_id`/`batch_id`) | own | - | - |
| View own result (redacted) | yes | - | - |
| Batch setup, mark, review, override, finalize | no | own batches | all |
| See AI estimate and review history | no | yes | yes |
| Inline rubric / answer key in a request | rejected | allowed | allowed |
Evidence: permission matrix and e2e (earlier runs); not re-run here.

## 6. Workflows
Lecturer: setup -> answers -> batch mark -> review evidence/concepts/map -> accept/override (reason) -> finalize -> history kept. **Implemented and e2e tested.**
Student: pick demo/batch -> answer -> see mark, feedback, concepts, map, status. **Implemented.**
Researcher: scripts under `experiments/` with frozen splits; reproducible by command, **not** by a UI. No UI for experiment selection (**MISSING by design**).

## 7. Integration requirements
Confirmed: backend auto-mounts `modules/<name>` at `/api/v1/<name>`; C3 service on :8003 (`C3_AI_URL`), `/health` makes no network calls. Needed but unconfirmed: shared identifiers with C1/C2/C4, C2 payload schema, C4 consumer. Requires confirmation from the other groups.

## 8. Data requirements
Input: question, student answer, reference (server-held), rubric criteria/levels/expected concepts, max marks. Record: ids, status, proposed vs final mark, criterion marks, concepts, evidence, feedback, map, `ai_estimate` (staff only), configuration/analysis version, timestamps, `review_history`. Dataset: `c3_phase3_v5_repaired_v2` (558 eligible answers; ratio-concentration check FAILS 0.766 because labels are tier-based).

## 9. Non-functional constraints
Latency: informal only; **no approved numeric target found -> Requires confirmation.** Accuracy targets: **Requires confirmation** (none invented). Reproducibility: dataset hashes, frozen splits, JSONL LLM cache. Accessibility: keyboard/dark/375 px checks only; no screen-reader scan. Usability study (NFR-C3-30), PII minimisation (NFR-C3-12), ethics (NFR-C3-15): **not tested**.

## 10. Prioritisation (proposal categories preserved)
- Must: A, B (partly), C, F, G, H, I, K, M-evaluation. Integration with C1/C2/C4 is Must in the proposal but 2 of 3 links are blocked by other components.
- Should: E (RAG, LLM comparison), OCR (not started), feedback-quality evaluation, usability study, extended relationships.
- Could: more datasets, extra LLMs, analytics, cross-dataset robustness.

## 11. Traceability (summary; full rows in the 82-row CSV)
Objective -> code -> test: SO1 -> `services/semantic/*` -> `test_semantic_matcher.py` (PART); SO2 -> `services/marking/*`, `orchestrator._mark` -> marking tests (PASS); SO3 -> concept matches -> unit + e2e (PASS); SO4 -> `services/feedback` -> unit + e2e (PASS); SO5 -> `services/mindmap` -> unit + e2e (PART); SO6 -> `experiments/*` -> reports 03, 27, 28 (PART).

## 12. Implementation gap analysis and smoke results
Run in this session:
| Suite | Result |
|---|---|
| C3 Python (`pytest -q`) | **603 passed, 13 xfailed, 9 deselected, 0 failed** (27 s) |
| Backend (`npm test`) | 118 tests: 113 pass, 0 fail, 3 skipped, 2 todo (known AUDIT-B9 items) |
| Frontend component tests | 10 of 10 pass |
| Paraphrase smoke (layer off / on) | still not demonstrated either way (see B) |
| Live service on :8003 and backend on :3000 | **not running at audit time**; no end-to-end browser run was done today (latest verified 2026-10-22: 106/106) |
Working: A, C, D, F (lexical), G, I, J, K, backend security. Incomplete: B (semantic), H (relationships), L (C1 contract). Missing: C2/C4 links, human ground truth, LLM/RAG results, OCR, usability study, retention policy. Unverified: educational quality of feedback, credential-free logs, today's browser e2e.

## 13. Research experiment requirements
Executed: lexical baseline, TF-IDF, SBERT, RoBERTa (+classical heads), Condition E, F-lite, semantic concept eval. Proposed only: LLM no-RAG, LLM+RAG, GraphRAG, multi-LLM, additional datasets. Needed before claims: human labels with two markers and agreement, multiple seeds, paraphrase benchmark, key-backed LLM runs. Metrics implemented: QWK, MAE, RMSE, P/R/F1, bootstrap CI by question, latency.

## 14. Acceptance test catalogue (existing -> where; gaps -> new)
Positive/negative/boundary/authz/regression are covered by the suites above. **Missing tests:** typed relationships, contradicted-concept class, C2 ingestion, C4 export, duplicate single submission, log scan for secrets, retention.

## 15. Unresolved questions for the supervisor/team
1. Is a human paraphrase benchmark required before the semantic layer is enabled?
2. Numeric targets for QWK/MAE/latency (none found).
3. C1 contract: direct DB write or API? C2 payload? C4 consumer?
4. Retention period and pseudonymisation rule.
5. Unlimited demo attempts and MCQ reveal policy.
6. Is the incorrect/contradicted class in scope?

## 16. Suggested sequence (not executed)
1. Human-marked gold set + agreement (unblocks every accuracy claim). 2. Paraphrase benchmark, then decide semantic layer default. 3. Typed relationships. 4. Provider keys -> LLM/RAG comparison. 5. C1/C2/C4 contracts with the other groups. 6. Usability/ethics, indexes, retention.

## 17. Final scope checklist
- [x] Input validation and association
- [~] Semantic analysis (lexical default; optional layer unproven)
- [x] Rubric marking and partial credit
- [x] Concept diagnosis (3 core classes)
- [x] Explainable feedback
- [~] Mind map (graph and UI yes, relationships untyped)
- [x] Lecturer verification and audit history
- [x] Student results
- [x] Stored records
- [~] C1 yes, C2/C4 blocked
- [~] Evaluation (baselines and models yes; human labels, LLM/RAG no)
- [x] Security and failure handling (credential-log scan not done)
