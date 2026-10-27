# 33 — Requirements audit, isolated E2E run, and C2/C4 integration specifications (2026-10-27)

Branch `feature/c3-stage1-dataset-integrity`; commits `f008d70`, `04fa007`, `2c34a79`, `dcfd3b8` preserved. Nothing pushed. The paraphrase benchmark (`7eaffc9`, `f9fdc90`) and the two earlier semantic experiments were not touched; all 82 benchmark items remain `draft_unreviewed`, no human annotation exists, and no benchmark metric is used anywhere below.

## 1. Sources read and conflicts (not silently reconciled)
| Source | Used for |
|---|---|
| Proposal `IT23227118_EDIRISINGHE T P V K.pdf` (FR-C3-01..46, NFR-C3-01..30, SO1-6) | approved baseline; rows in the matrix keep its ids |
| `Day_6_Functional_Requirements_Component_3_AdaptiveLearnSE.pdf` | working baseline of **96** FRs (FR-C3-001..096, with Priority H/M); rows prefixed `D6-` |
| `Day_2_Component_3_Definition...pdf`, `TAF - SE_317.pdf`, Day 18 methodology | context (not re-extracted in full this session) |
| Reports 31 and 32, repository code and tests | implementation evidence |

| # | Conflict | Needs clarification from |
|---|---|---|
| 1 | Two numbering schemes: proposal FR-C3-01..46 vs Day 6 FR-C3-001..096 (different scope: Day 6 adds analytics, keywords, structure, relevance, uncertainty rules, admin config and monitoring) | Supervisor / C3 author: which set is the acceptance baseline |
| 2 | Day 6 FR-025 lists contradiction detection as **Medium priority, "where detectable"**, output "incorrect evidence". The proposal text has no contradiction requirement. Neither says contradiction must change marks | Supervisor |
| 3 | Day 6 pipeline places RAG inside the marking path; Day 6 section 12 and the proposal treat RAG as a research methodology to be measured (Should Have) | Supervisor |
| 4 | Day 6 FR-056 needs human marks as baselines; the dataset labels are tier-derived and no human marks exist | C3 author / markers |
| 5 | The proposal says weak-concept information "can" be provided to C4; Day 6 section 11 says C4 "can consume" C3 results. Neither defines a contract | C4 owner |

## 2. Requirements traceability matrix
File: `reports/c3_remediation/c3_requirements_traceability_matrix.csv` (178 rows). Columns: id, id scheme, basis, source, category, priority, requirement, implementation location, automated tests, status, verification level, remaining work and acceptance. All rows are **explicit** requirements from the two documents above; no inferred or suggested rows were added. The earlier `c3_functional_requirements_matrix.csv` (82 rows) is kept unchanged as history.

| Scheme | Implemented and tested | Implemented, not fully validated | Partial | Not implemented | Blocked | Unclear |
|---|---|---|---|---|---|---|
| Day 6 FRs (96) | 53 | 12 | 20 | 8 | 3 | 0 |
| Proposal FR/NFR/SO (82) | 55 | 1 | 17 | 0 | 6 | 3 |

"Implemented and tested" means a code path and an automated test exist; the matrix also records the verification level. Browser E2E evidence for a row is marked historical unless it appears in section 6.
**Not implemented (Day 6):** FR-017 keywords, 018 answer structure, 020 and 095 irrelevance flag, 033 rubric edit/deactivate, 081 and 082 class analytics, 089 admin configuration. **Blocked:** 049 RAG vs no-RAG, 051 multi-LLM run, 056 human baselines. **Partial includes:** semantic matching (021, 022), contradiction (025), relationships and hierarchy (069, 070, 073), RAG library (042-044), uncertainty rules (079, 093), MCQ penalty and total (010, 011), structured answers (003).

## 3. Contradiction flag and mind map — validation and one decision
- Contradiction detection is a **heuristic warning** (negation cues next to the concept's words). Accuracy is unmeasured. Tests cover negation, mixed affirmation and negation, a correct negated sentence flagged (false positive by design), and wrong statements without any negation word (not detected, asserted as a limitation).
- **Tension found and resolved by a switch.** Report 32's version withheld credit for a concept that is only ever negated. Your latest instruction says a warning must not change marks unless the requirements authorize it; the Day 6 text only asks for "incorrect evidence" and an earlier instruction asked that contradicted concepts not receive positive credit. I kept the earlier behaviour as the default and added `C3_CONTRADICTION_POLICY=warn_only`, which flags and warns but leaves status and marks unchanged. Both modes are tested (3 new tests); the mode is recorded in `analysis.contradiction_check` (`negation-cue-v1/withhold_credit` or `/warn_only`). **Decision for you or the supervisor:** which default is correct. Every result needs lecturer review before finalization either way.
- Relationship typing: tests confirm each type is assigned only under the cue rule (both concepts credited, one sentence, fixed phrase, no negation) and otherwise stays `co_mentioned`. The evidence text and the lecturer heading now say the relation is "as the student wrote it". Requirement fit: Day 6 FR-069 asks for relationships "where supported"; typed cue relations are an enhancement beyond the proposal's "where evidence exists". No human-annotated relation set exists to measure correctness.

## 4. C2 input — specification for the C2 owner (C2 has no route; nothing invented)
**Facts:** C2 code is in `ai-services/c2` (`question_repository.build_question_repository`), output fields `question_id, paper_id, module_code, module_name, calendar_year, semester, question_number, part_id, parent_id, question_text, context, marks, marks_status, topic (None), bloom_level (None), difficulty (None), source_*`. No HTTP route; `backend/src/modules/c2` is empty.
**Minimum C3 needs per assessable question** (from `MarkingRequest`): `question_id`, `question_text`, `answer_type`, a `rubric` (criteria with `criterion_id`, `max_marks`, scoring levels with `level_id`, `mark`, `required_concepts`/evidence rule), optional `expected_concepts`, optional `reference_answer`, optional `max_marks` (must equal the rubric total).
| Field | C2 can supply today | Source of the rest |
|---|---|---|
| question_id, question_text, context | yes | - |
| max_marks | yes when `marks_status` is extracted/calculated | - |
| answer_type | no | lecturer |
| rubric, expected_concepts, reference_answer | no | lecturer, or a future C2 marking-scheme parser (the contract README already states this as a pending decision) |
**C3 side done:** adapter and 422 validation (report 32). **Acceptance checklist for the C2 owner (REQUIRES C2 OWNER APPROVAL):** (1) agree transport and authentication (a backend route with a role-checked token, or a file/DB hand-off); (2) provide stable `question_id`s that stay unchanged across papers; (3) state who supplies rubric/reference/concepts; (4) deliver a sample payload that passes `tests/integration/test_c2_c3_contract.py` unchanged; (5) test the real route end to end. The real transport path was **not** tested because none exists.

## 5. C4 output — PROPOSED, REQUIRES C4 OWNER APPROVAL (not implemented)
No authoritative contract exists. `backend/src/modules/c4/services/c3CodingAdapter.js` only documents a future coding-exercise provider; C4 reads no C3 concept data. The existing concept-level export is C3 to **C1** (`learning_events`: provisional/finalized, demonstrated/partial/missing concept lists, scores) and was verified in the isolated run (section 6). That is a C1 output, not a C4 integration.
**Proposed minimum (option A, no new C3 code):** C4 reads C3 evidence from C1 `learning_events` where `type` is `c3_finalized_assessment`. **Option B:** a read endpoint `GET /api/v1/c3/learning-signals?student_id=...` returning, per finalized submission: `submission_id`, `question_id`, `topic`, `lifecycle_stage`, `final_score`, `total_possible`, `demonstrated_concepts`, `partial_concepts`, `missing_concepts`, `possibly_contradicted_concepts` (flag, heuristic), `finalized_at`, with student/self or C4-service authorization. **Questions for the C4 owner:** A or B; provisional results allowed or finalized only; pseudonymous student id; whether contradicted flags should be exported; transport and token. Acceptance tests once agreed: schema validation, finalized-only filter, student isolation, idempotent re-read, error behaviour for unknown student.

## 6. LLM and RAG experiments
Inspected `experiments/rag_vs_norag.py` (matched conditions, temperature 0, TRAIN-only corpus, refuses without `--run-live`), `multi_llm_comparison.py`, `rag_retrieval_eval.py`. Keys for Gemini and OpenAI exist in the git-ignored `.env` (not printed); Groq and OpenRouter keys are absent; Ollama is not running.
- **Executed (earlier):** 5-answer Gemini pilot on the validation split, two conditions, tier-derived labels. Exploratory, too small to compare conditions.
- **Smallest defensible comparison:** the existing harness on the 90-answer test split, two conditions = 180 calls. At about 20 requests per day per model on the free tier that is roughly 9 days for one model, or a paid quota. A smaller subset (for example 10 answers = 20 calls, one day) would run but could not support any claim, so it was **not run**.
- **NOT RUN:** no-RAG vs RAG, multi-LLM, GraphRAG, LLM-judged feedback quality. Command once quota exists: `python -m experiments.rag_vs_norag --out <dir> --provider gemini --run-live [--limit N]`.
- **Not used:** the paraphrase benchmark (no human labels). The semantic layer stays off by default.

## 7. Isolated end-to-end run (this session)
**Environment.** Docker Desktop would not start: it died on stale Unix-socket files that Windows could not delete (`...\Docker\run\dockerInference`, then `...\docker-secrets-engine\engine.sock`; error "The file cannot be accessed by the system"). Fix applied without deleting anything or resetting Docker: the folders containing the stale sockets were renamed (`Docker\run.stale-*`, `docker-secrets-engine.stale-*`), after which the engine started (29.5.2). Your own containers (`mongodb`, `adaptivelearnse-neo4j`) were not touched. A throwaway container `c3-e2e-mongo` on `127.0.0.1:27018` (no volume) held database `adaptivelearnse_c3_e2e`; the backend was started with explicit `MONGO_URI`, `MONGO_DB`, port 3100 and logged "MongoDB connected: adaptivelearnse_c3_e2e". Atlas was never contacted. The container was removed afterwards.
**Results.**
| Check | Result |
|---|---|
| `guard.test.mjs` | 9 of 9 pass |
| Browser E2E `e2e.mjs` (Chrome, Vite dev server on the current source) | **106 of 106 passed, 0 failed** (`experiments/e2e_2026-10-27/results.json`, `api_matrix.json`). The suite does not exercise contradiction or typed relationships |
| Live API scenarios through the real backend, Python service and isolated DB (student `demo_id`) | valid 4/4; partial 2/4; unrelated 0; **contradicted ("no high-level structure ... does not organize components ... no relationships") 0 with the flag set**; empty answer 0 (200 with warning); no demo/batch 400; inline rubric from a student 400; unauthenticated 401 |
| Lecturer path | lecturer sees the flag and warnings on the stored submission; override with reason 200; finalize 200 |
| Student path | browser check S16 confirms the student sees the lecturer's final mark; the API check confirmed the student response has no `review_history` and no `ai_estimate` (the exact final-mark field was not asserted in the API script) |
| Audit history | kept for the lecturer |
| C1 hand-off | `learning_events` has provisional and finalized records; the overridden event shows `final_score 2`, `provisional_score 0`, missing concepts listed, decision `overridden` |
| C2 to C3 and C3 to C4 transport | not exercised: no route exists (sections 4, 5) |

## 8. Test results (rerun after the last change)
| Suite | Result |
|---|---|
| C3 Python `pytest -q` | **702 passed, 9 deselected, 12 xfailed, 0 failed** (699 before; +3 policy tests) |
| Backend `npm test` (services stopped) | 118 tests: 113 pass, 0 fail, 3 skipped (live-service tests), 2 todo (AUDIT-B9) |
| Frontend `npm test` / `vite build` | 10 of 10 pass / build succeeds |
| Browser E2E | 106 of 106 (section 7) |

## 9. Limits and open items
Heuristic contradiction and relation typing are unmeasured; semantic layer unproven and off by default; benchmark unlabelled; C2 transport/authentication, C4 contract, rubric/reference supply, the choice of FR baseline, and the contradiction default are decisions for the people named above; LLM/RAG comparisons need quota.
