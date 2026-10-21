# 03 Requirements and workflow traceability

Status: IMPLEMENTED / PARTIAL / MOCKED / PLANNED / BLOCKED / NOT IMPLEMENTED. Evidence labels V/I. Full row-level data: `requirements_traceability.csv`.

## 1. Functional requirements by group (proposal FR-C3-01..46)
| Group (proposal Table) | FR ids | Status | Implementation | Test evidence | Gap |
|---|---|---|---|---|---|
| Answer processing (T8) | 01–07 | IMPLEMENTED (04: short-answer scope) | `services/preprocessing`, Node `/c3/assess` | `test_preprocessing`, `test_text_and_semantic_edge_cases`, `test_analysis_api` | no stemming/stop-words; no size limits |
| Automated marking (T9) | 08–15 | PARTIAL | `criterion_evaluator`, `marking_engine`; 09 "semantic, not only keywords" **not met** (lexical) | `test_criterion_evaluator*`, `test_marking_*` | FR-09 semantic comparison; FR-15 record method/config partial |
| LLM and RAG (T10) | 16–20 | PARTIAL code / NOT RUN | `services/llm`, `services/rag`, `experiments/` | `test_llm_*`, `test_cckg_and_rag` (stubs) | no real run; FR-19/20 not demonstrated |
| Explainable analysis (T11) | 21–26 | IMPLEMENTED | `semantic/analyzer`, `criterion_evaluator` explanation | `test_feedback_*`, `test_criterion_evaluator` | explanation templated; single-word hits |
| Feedback (T12) | 27–31 | IMPLEMENTED (templated) | `services/feedback` | `test_feedback_generator` (419 lines) | not generative; no quality evaluation |
| Mind map (T13) | 32–35 | PARTIAL | `services/mindmap` (star) | `test_mindmap_*` | FR-33 relationships absent |
| Lecturer support (T14) | 36–41 | IMPLEMENTED with defects | `LecturerQueue/Review/BatchMarking` pages, `submissionService` | `c3.test.js`, `c3_audit.test.js` | AUDIT-B2/B3/B5; no history |
| Integration and records (T15) | 42–46 | PARTIAL | C1 bridge (direct DB write); records in Mongo | `c3.test.js` bridge tests | FR-42 C2→C3, FR-44 C4 NOT IMPLEMENTED |

## 2. Non-functional requirements (proposal NFR-C3-01..30)
| Group | Status | Note |
|---|---|---|
| Quality/consistency (01–04) | PARTIAL | deterministic pipeline gives repeatable results (V); agreement measurement exists for baseline/E only |
| Explainability (05–07) | IMPLEMENTED | proposed vs lecturer mark kept separate (`automated_mark` vs `final_mark`) |
| Performance (08–10) | PARTIAL | no per-response timing record; no threshold (policy "do not invent a number") |
| Security/privacy (11–15) | PARTIAL | roles, scrypt, JWT; secret fallback, open CORS, no rate limit, client-supplied answer key |
| Reliability (16–19) | PARTIAL | invalid input mapped to 400/422 except cross-field rubric errors → 500; persistence failure masked |
| Auditability (20–23) | PARTIAL | original mark kept; no history array, no finalized_by |
| Scalability/maintainability (24–26) | PARTIAL | provider ABC and module auto-mount good; duplicated helpers |
| Usability (27–30) | PARTIAL | UI exists; no usability evaluation; god components |

## 3. Workflow trace (stage → code → test → class)
| Stage | Code | Test | Class |
|---|---|---|---|
| Submit | `c3Controller.assessAnswer` 59–100 | `c3.test.js`, live microservice tests | IMPL (client-trusted inputs) |
| Auth | `middleware/auth.js` | `auth.test.js` | IMPL (secret fallback) |
| Call Python | `aiClient.callAi` 7–43 | 502/504/400 mapping tests | IMPL |
| Process → analyse → mark → feedback → map | `orchestrator.assess_answer` | `test_assessment_api`, `test_api_audit` | IMPL (lexical) |
| Persist | `createSubmissionWithResult` | c3 tests | IMPL (masked failure) |
| Lecturer queue/review | `listSubmissions`, `reviewSubmission` | c3 tests | IMPL |
| Finalise | `finalizeSubmission` | c3 tests | IMPL (non-atomic) |
| C1 events | `integration/c3-c1` | bridge tests | IMPL (direct DB write) |
| Batch | `batchMarkingService` | 8 batch subtests | IMPL (no ownership) |
| MCQ | `mcqMarkingService` (Node only) | 10 subtests | IMPL (second engine) |
| OCR | `c3Controller` | 2 tests | NOT IMPL (400) |
| LLM/RAG/CCKG | `services/llm|rag|cckg` | provider/stub tests | not on live path |

## 4. Two key functions for PP1 (defined in the team execution doc §7.3)
- **Guaranteed 1 — Answer Processing + Semantic Analysis:** input answer + expected concepts → tokens, sentences, concept status with evidence ids. Demonstrable (V). Honest label: lexical.
- **Guaranteed 2 — Rubric-Aware Marking + Evidence:** rubric + analysis → criterion levels, marks, explanation. Demonstrable (V): 4/4, 2/4, 0/4.

## 5. Highest-risk untested or weakly tested areas
`orchestrator.assess_answer` (only via HTTP), `/health` for provider=local, Neo4j live path (deselected by default), tests/evaluation (empty), frontend (no tests), real-Mongo behaviour (fake DB only), provider contract parity, MCQ result rendering.
