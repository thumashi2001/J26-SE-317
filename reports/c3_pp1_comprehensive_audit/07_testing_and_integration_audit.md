# 07 Testing and integration audit

## 1. Counts re-run at `8fdbdbd` (V)
| Suite | Result |
|---|---|
| Python (`pytest -p no:cacheprovider`, offline) | 324 passed, 13 xfailed (strict), 9 deselected, 0 failed |
| Python neo4j live (`-m neo4j`, container up) | 5 passed |
| Node (`npm test`) | 90 = 75 pass + 15 todo (AUDIT-B1…B9, X1) |
| ruff (project config) | 111 findings: 101 E501, 8 E402, 2 W293 |
| ESLint (backend) | 13 errors (unused vars) |
| Frontend tests | none; no lint script |

## 2. What the tests really prove
- **Strong:** deterministic pipeline unit tests (criterion evaluator 283 lines, feedback generator 419, dataset repair 396); API contract tests (analysis, marking, feedback, mindmap, assessment); failure mapping Node↔Python (502/504/400); role guards; ownership for students; C1 provisional/finalised lifecycle and idempotency (against a fake DB).
- **Hermetic:** `conftest.py` blocks real HTTP and removes API keys, so no test ever hits Gemini/OpenAI; live tests are marked `live_llm`/`neo4j` and deselected.
- **Honest known-bug convention:** 13 strict xfails and 15 todos are named defects, so "all green" does not hide them.
- **Weak:** provider tests use stubs (no real LLM behaviour); thin `test_mindmap_api` (24 lines); `tests/evaluation` is empty (no regression test for metrics); no orchestrator unit test; Node tests use an in-memory fake DB — upsert races, unique indexes, `findOneAndUpdate` shape unverified against real Mongo; no UI or end-to-end test.

## 3. Requirement → evidence map (critical items)
| Requirement | Evidence | Gap |
|---|---|---|
| Partial credit | `test_criterion_evaluator`, demo `arch-partial` = 2/4 | M4 bug makes partial levels unreachable for legacy rubrics |
| Evidence per criterion | `test_criterion_evaluator`, explanation text | single-word hits (M5) |
| Concept status | `test_semantic_baseline`, edge-case tests | stop-words create "partial" |
| Lecturer override with reason | c3 tests (override persists, reason required, student 403) | upper bound (B3) |
| Original mark preserved | test "automated_mark preserved" | no history |
| Finalised cannot be edited | 409 test | reopen via batch re-post (B2) |
| Failure mapping | live microservice tests 4–5 | persistence failure masked (B6) |
| Dataset repair integrity | `test_dataset_repair.py`, validator injected-defect tests | validator hard check fails by design |
| Metric reproduction | manual recomputation (audit 04) | no automated test |

## 4. Integration status
| Link | Status | Evidence |
|---|---|---|
| Frontend ↔ Express | working | apiClient, pages |
| Express ↔ FastAPI | working (15 s timeout, no auth header) | `aiClient.js` |
| Express ↔ Mongo | working, no indexes | `getDb` usage; no `createIndex` |
| C3 → C1 | implemented via direct write to `learning_events`; several C1 readers do not filter provisional events (I); invented fields (`time_sec` = 60, topic by keyword guess) | `integration/c3-c1/index.js` |
| C2 → C3 | NOT IMPLEMENTED (README contract only) | `integration/c2-c3/README.md` |
| C3 → C4 | NOT IMPLEMENTED | `modules/c4` empty |
| CCKG / Neo4j | adapter + 5 live tests; not on the marking path; ontology covers ~5 of 541 eligible concept strings (I) | `graph_adapter.py` |

## 5. Gaps to close if time allows (not done — need approval)
1. Add `@app.exception_handler(RubricValidationError)` (fixes AUDIT-A1; main demo endpoint).
2. Server-side question/key bank (AUDIT-B8). 3. Real-Mongo integration test. 4. Golden-set regression test for baseline/E metrics. 5. Provider contract test. 6. MCQ-render test for the mind-map component.
