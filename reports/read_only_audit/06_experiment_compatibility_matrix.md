# 06 Experiment compatibility matrix (code read; nothing executed beyond offline tests)

Evidence from a delegated read-only audit (agent C) with the key claims re-checked by me (the loader/manifest incompatibility, schema columns, rubric shape). Labels: V/R/I/B.

## Repaired schema vs what the code expects
- Repaired set (V): `01_question_bank.csv`, `02_controlled_answers_eligible.csv`, `03_rubric_criteria.csv`, split files, `manifest.json` whose `files` map is name → **plain sha256 string**, no `expert_validation` key. Rubric = one question-level criterion per question (104 single, 63 two-criterion generic rows); **no scoring levels anywhere**.
- Loader expects (V): files `questions.csv`/`rubrics.csv`/`answers.csv`, JSON columns `concept_graph`, `concept_status`, `gold_mindmap`, `scoring_levels`, `normalized_mark`, `word_count`, `needs_review`, `tier`; manifest `files[name]["sha256"]`; default dir `c3_synthetic_v6` (removed). `datasets/loader.py:125-138`, `experiments/conditions.py:50-58`, `framework.py:148-153,209-227`, `run_experiments.py:131`. **`load_release` fails on the repaired set at the first hash check (`TypeError`: string indices).**

## Per condition
| Cond | Method (code) | Runnable on the repaired set today? | Real inference ever executed? | Provider/retrieval/graph type |
|---|---|---|---|---|
| Lexical baseline | `conditions.py`: cosine × max; **`evaluate_repaired.py`: token-recall × max** (different formula) | only via `evaluate_repaired.py` (offline) | local computation, V | none |
| A zero-shot LLM | total-mark JSON | needs loader adapter only | **No** (no result dirs, no llm cache; R: "not run – quota") | real Gemini/OpenAI HTTP if keys; not mock (V: no mock code in `services/`) |
| B rubric LLM | choose a level per criterion | **No** – needs `scoring_levels` | No | as above |
| C B + dense RAG over train references | `CurriculumVectorStore(..., embedding_backend="dense")` | No (levels); corpus would be generic template references | No | dense Gemini/OpenAI embeddings by default (`C3_VECTOR_BACKEND=dense`); TF-IDF only when forced (tests/conftest force `tfidf`) |
| D B + GraphRAG | `CCKGGraphAdapter(strict=True)` | No (levels); only ~5 of 541 eligible concept strings match the ontology (I) | No | live Neo4j required in D; elsewhere silent in-memory fallback unless `C3_CCKG_STRICT=1`; Neo4j container is up and its 5 live tests pass (V) |
| E deterministic | `mark_answer` + rubric levels | **Yes, only via `evaluate_repaired.py`** with a mechanically built binary rubric | local computation, V | no network/LLM/embeddings |
| F fusion | validation-fit weights of E + B + embedding similarity | No (needs B and embeddings) | No | real embeddings if run |

- **Condition E is the only condition (with the baseline) that runs on the repaired set** (V). Mock-era results (`mock-gpt4o` etc.) still sit in `docs/pp1/evidence/results/` and in the ignored `experiments/results/`; the mock provider was removed (V). No mock output is presented as real in current code.
- Documentation vs code for F: docs describe a supervised gradient-boosted regressor (`CLAIM_EVIDENCE_DECISION_LOG.md:79`, `EXPERIMENT_A_TO_F_TRACEABILITY.md:34`); the code is a grid-searched weighted fusion; the GBR training script is not tracked (V). Contradiction.

## Adapter plan (plan only – not implemented; needs approval)
1. Add `datasets/adapter_repaired.py` returning the existing `Release` view of the 576 eligible answers only (never quarantine/controls), with a hash verifier for plain-string manifests; fix `loader.py:22` default.
2. Column map: `answer_quality→tier`, `review_status!='ok'→needs_review`, `marks→max_marks`, derive `normalized_mark`, `word_count`, `concept_status`; `concept_graph`/`gold_mindmap` unavailable → disable mind-map/GraphRAG evaluation.
3. Rubric levels (the blocking decision) – options: **O1** binary L0/L1 (mechanical, E-compatible, but B–F collapse to all-or-nothing, as E already does); **O2** levels from tier marks – *invalid* (leaks the answer key); **O3** use answer `criterion_marks` as criteria – not viable (391/487 ids undescribed); **O4** lecturer/researcher-authored levels for 96 questions – the only valid route to meaningful B–F, several days of human work; **O5** holistic total-mark prompt for B–D – schema-honest but a different method (must be disclosed). Recommended: O1 for E parity + A; O4 for B–F.
4. Report normalised MAE as primary (mark scales 10–100); fix the baseline definition once and reuse it.
5. Effort: adapter + tests ≈ 0.5–1 day; A-only run ≈ 0.5 day; O4 authoring 2–5 days; D also needs a populated CCKG.
