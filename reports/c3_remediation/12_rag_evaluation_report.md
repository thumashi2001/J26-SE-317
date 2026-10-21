# 12 RAG evaluation report

Four things are kept separate: **(a) implementation, (b) offline testing, (c) retrieval evaluation, (d) actual LLM marking evaluation.**

| Layer | Status | Evidence |
|---|---|---|
| (a) Implementation | done | `services/rag/{corpus,rag_marking}.py`, local embedding provider, experiment scripts (11) |
| (b) Offline testing | done, 10 tests pass | `tests/unit/test_rag_pipeline.py` (stub embedder/LLM; proves code paths only) |
| (c) Retrieval evaluation | executed | `experiments/rag_retrieval_eval.json` (below) |
| (d) LLM marking: no-RAG vs RAG | **BLOCKED / pending — not executed, no results** | `experiments/rag_vs_norag_status.json` |

## (c) Retrieval evaluation (executed 2026-10-21)
- Corpus: 133 train-only documents (67 eligible train questions) of dataset v2, provenance and source hash in the JSON.
- Queries: the 26 eligible validation + test questions (question + reference answer). No human relevance labels exist, so relevance is **proxied by "retrieved document comes from the same module"** — a coarse measure.
- Embedding: `sentence-transformers/all-MiniLM-L6-v2`, local, CPU. Controls: TF-IDF index and random retrieval (200 trials/query).

| Index | k=1 hit rate | k=3 | k=5 | mean top-1 cosine | empty | near-duplicate top-1 (≥0.9) |
|---|---|---|---|---|---|---|
| dense local SBERT | **0.769** | 0.962 | 0.962 | 0.590 | 0 % | 0 % |
| TF-IDF | 0.538 | 0.654 | 0.731 | 0.580 | 0 % (3.8 % at threshold 0.3) | 0 % |
| random control | 0.113 | 0.306 | 0.462 | – | – | – |

Reading: dense retrieval finds same-module material far above chance and above TF-IDF, and no held-out question is a near-duplicate of a training document (max top-1 below 0.9). This says nothing about whether retrieved context improves **marking**; with only 26 queries and a module-level proxy, treat it as a sanity check, not a result.

## (d) LLM marking — design and why it did not run
Design (implemented in `rag_vs_norag.py`): Condition A = LLM marks with the prompt but no evidence; Condition B = identical model, rubric, scale, temperature 0 and answers plus the retrieved EVIDENCE block. Same 90 held-out test answers; retrieval only from the train-only corpus; outputs validated against the rubric; per-answer predictions, retrieved citations, latency, tokens and model id written to CSV; metrics nMAE, QWK, correlation, within-tolerance, bootstrap by question.
Blocker (exact): the harness refuses live calls without `--run-live`; free-tier Gemini quota (≈20 requests/day/model) cannot cover 2 × 90 calls; OpenAI credit was reported exhausted earlier in the project (not re-probed in this session); no local LLM runtime (Ollama) installed. COM-07 also keeps uncalibrated LLM numbers out of PP1. **No claim about RAG improving or worsening marking is made.** The dataset also has no scoring levels, so the harness uses one holistic criterion per question.

## Offline experiments executed this session (not LLM)
- **Condition F-lite** (`hybrid_f_lite.json`): NNLS stack of E, A1, B1, C fit on validation only → weights E 0.026, A1 0.050, B1 0.000, C 0.924; validation nMAE 0.0353, test nMAE 0.0375 vs RoBERTa alone 0.0382. Difference is within noise (RoBERTa test CI 0.030–0.047): **no evidence the ensemble helps**. Not the proposal's Condition F.
- Earlier: TF-IDF, SBERT, RoBERTa, baselines (03).

## Validity limits (unchanged)
Dataset ratio-concentration check FAILS (0.766 > 0.45); labels are researcher tiers (three tiers share one mark); length-only model (nMAE 0.067) beats TF-IDF/SBERT; RoBERTa and F-lite are single-seed; 90 test answers from 15 questions; validation 66 answers from 11 questions; no human-marker agreement has been measured.
