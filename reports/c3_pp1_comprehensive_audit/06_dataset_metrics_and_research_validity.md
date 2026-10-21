# 06 Dataset, metrics, model comparison and research validity

Builds on `reports/read_only_audit/` (verified again at `8fdbdbd`). Nothing was run beyond the offline tests and a read-only recomputation already audited.

## 1. Dataset facts (V)
| Item | Value |
|---|---|
| Original (archived, byte-exact) | `datasets/archive/C3-Phase3-v5-FINAL_original/` — 167 questions / 1,002 answers, 6 quality variants each |
| Repaired primary set | `datasets/c3_phase3_v5_repaired/` — 96 questions / 576 eligible answers: train 420, val 66, test 90 |
| Quarantined / controls | 355 quarantined with reasons; 71 repaired IRRELEVANT controls kept outside primary set; 576 + 355 + 71 = 1,002 |
| Defects found | literal "nan" (252 answers), flat 10-mark labels (426), wrong rubric keys, template-like text |
| Repair properties | deterministic, SHA256-verified, nothing generated or reworded, no splits moved |
| Open failures | ratio-concentration 0.758 > 0.45 (val 1.0, test 0.917); length–mark Pearson 0.8107; near-duplicate PP-SE3080-099 (train) / 107 (test) cosine 0.903; 391/487 criterion ids undescribed; PP-SE3040-009 not scope-flagged; PP-SE3080-102 labels anomalous; MOSTLY/MISSING/MISCONCEPTION share marks in 96/96 questions |
| Labels | researcher-constructed from quality tiers; no expert annotation or inter-rater agreement |

## 2. Metrics reproduced (V; repaired test n = 90, 15 questions; MAE in marks)
| Method | Test MAE | Val MAE | Note |
|---|---|---|---|
| Lexical token-recall baseline | **1.939** | 3.099 | set recall × max marks |
| Condition E (binary rubric adapter) | 3.544 | 10.955 | emits only 0 or full marks |
Legacy figures: E 4.640 / 7.220 / 0.7243 reproduces only with 15 failed calls scored 0; baseline 5.609 does not reproduce (5.369); "17.3 % reduction" does not reproduce. Absolute MAE is dominated by 100-mark questions → normalised MAE should be the primary figure.

## 3. Candidate-model inventory (original plan vs reality)
| # | Candidate | Task | Source | Code location | Model type | Training | Execution | Eval data | Results | Limitations | Compliance with plan |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | TF-IDF + Ridge (L0) | answer→mark | Day 23 L0 | git `f21dba4` `train_semantic_model.py` (deleted at HEAD) | trained classical | yes, synthetic train 702 | executed | synthetic test 150 (defective labels) | saved only in joblib; Ridge not reported | wrong data, not reproducible | PARTIAL |
| 2 | TF-IDF + GradientBoosting v1 | answer→mark | same | same | trained | yes | executed | same | MAE 0.017, r 1.0, tolerance 100 % | length/leakage artefact (word_count 68–87 % importance) | invalid |
| 3 | TF-IDF + GBR v2 ("corrected") | answer→mark | DEC-08 | git `c57e553` | trained | yes | executed | same | MAE 5.994, RMSE 9.547, r 0.282, tol≤2 53.3 % | train MAE 7.256 > test (unit mismatch); never re-run on repaired data | PARTIAL |
| 4 | RoBERTa-base (L1) | classify/score | Day 23 | none | — | no | no | — | — | — | NOT IMPLEMENTED |
| 5 | BERT, cross-encoder | optional | Day 22/23 | none | — | no | no | — | — | — | NOT IMPLEMENTED (optional) |
| 6 | SBERT (L2) | similarity/evidence | Day 23 | none (old `all-MiniLM` path removed) | pretrained | no | no | — | — | needs scoring layer | NOT IMPLEMENTED |
| 7 | GPT/Llama (L3) | evidence + feedback | Day 23 | `services/llm/{openai,gemini,local}_provider.py` | pretrained API/open | none | **never run on dataset** | — | — | quota (Gemini ≈20 req/day, OpenAI no credit) | PARTIAL / BLOCKED |
| 8 | Mock "GPT-4o/Claude/Llama" exp1–5 | — | earlier phase | deleted (`8cad340`) | **MOCK** heuristic | — | executed (0.04 s) | synthetic 150 | MAE 4.5–5.1 | not models; hard-coded keyword detector | INVALID as evidence |
| 9 | Lexical baseline | answer→mark | extra | `evaluate_repaired.py:88` | deterministic | — | executed | repaired splits | test MAE 1.939 | two inconsistent definitions in repo | extra |
| 10 | Condition E | rubric marking | proposal "integrated" | `services/marking/*` | deterministic | — | executed | repaired splits | test MAE 3.544 | binary here (M4) | PARTIAL (L4 core) |
| 11 | Conditions A–D, F | LLM/RAG/GraphRAG/fusion | Day 18/Day 23 | `experiments/conditions.py` | planned framework | — | **never run** | — | — | loader incompatible with repaired manifest; no scoring levels; F defined 3 ways | NOT DEMONSTRATED |
Same-data comparison: rows 1–3 and 8 shared the original 150 test rows but used defective labels and different denominators; after repair only rows 9–10 were re-evaluated. **No valid like-for-like comparison of more than two candidates exists.**

## 4. Supervisor multi-model instruction — compliance
Status: **NOT DEMONSTRATED** (infrastructure PARTIAL). Required task: answer→correctness/mark prediction and concept-evidence detection. Written basis: Day 22/23/25, proposal §3.3/§3.5/Table 4, SO6; "2–3" is your report (R). No documented best-model selection; E is the PP1 baseline because of COM-07/DEC-07, not because it won. Required for PP1? Documents defer LLM/RAG to Phase 4; no signed decision. Ask the supervisor to confirm in writing.

## 5. Next experiment — plan only (nothing executed; approvals needed for installs/downloads/compute)
**Goal:** satisfy the planned comparison with real data and report honestly.
1. **Data:** EngSAF primary (`Data sets\engsaf`: train ≈12,612, val ≈1,438, unseen-answer test ≈3,419, unseen-question test ≈3,168 (from file line counts); labels 0/1/2; reference answers; feedback). Keep source splits. Secondary: repaired synthetic set (domain check). Optional ASAP-SAS, Mohler, ASAG2024.
2. **Candidates (2–3 + optional):** C1 TF-IDF + logistic/ridge (reference); C2 SBERT embedding of (answer, reference) + classifier; C3 RoBERTa-base fine-tuned (GPU needed, else frozen features); C4 optional LLM judge only if quota exists.
3. **Protocol:** identical preprocessing/labels/splits; pre-registered selection rule (Macro-F1 on validation, ties → QWK); no test-set tuning; unseen-answer and unseen-question tests evaluated once; report Accuracy, Precision, Recall, Macro-F1, confusion matrix, QWK/MAE where ordinal; paired bootstrap over questions; fixed seeds; record library versions, checkpoints, hashes; cost/latency table.
4. **Integration:** use the winner's similarity/score as extra concept-evidence signal while marks still come from rubric levels (preserves explainability); keep E as transparent baseline.
5. **Risks:** domain mismatch (EngSAF is engineering questions, not SE rubrics), compute, licensing, privacy for API LLMs; the synthetic set cannot validate generalisation.
6. **Evidence pack for the supervisor:** result tables, predictions CSV, commit hash, environment lockfile, one-page decision memo "why model X".

## 6. Research-validity risks (for the viva)
Synthetic template-like data; label noise; ratio-concentration failure; length shortcut; leakage pair; tiny test set (n = 90); no expert gold standard; baseline beats E; QWK missing; DEC-06 vs proposal p.30; undocumented/unsigned decisions; mock-era results still lying in `docs/pp1/evidence/results/` and ignored `experiments/results/` — never cite them.
