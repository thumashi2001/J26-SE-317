# 03 Model training and comparison (executed 2026-10-21, CPU only)

Script: `ai-services/c3/experiments/model_comparison.py` (+ `aggregate_comparison.py`). Raw results: `experiments/results_{REF,A,B,C}.json` (config, hyper-parameters, per-answer predictions, histories), `experiments/comparison_table.{md,csv}`, `comparison_summary.json`, `diagnostics.json`, logs `log_B.txt`, `log_C.txt`, `experiments_requirements_lock.txt`.

## Protocol (as run)
- Data: frozen `c3_phase3_v5_repaired_v2` (SHA256 per file in `dataset_v2_hash_manifest.json`); train 402 / validation 66 / test 90 answers; question-disjoint splits, unchanged.
- Target: expected_mark / max_marks (0–1). Inputs: reference answer + student answer. No answer-length feature was supplied to any candidate.
- Selection: hyper-parameters and the RoBERTa epoch chosen on **validation nMAE only**; the test set was predicted once per candidate with the selected setting (RoBERTa test predictions come from the validation-best checkpoint). Each candidate script was run once; nothing was re-run after seeing test numbers.
- Seed 20261021; torch 2.14.1+cpu, transformers 5.20.2, sentence-transformers 6.1.0, scikit-learn 1.9.1, Python 3.14.7; no GPU. Public pretrained weights downloaded once (all-MiniLM-L6-v2, roberta-base); no API/LLM call.
- Metrics: normalised MAE (primary), MAE in marks, nRMSE, Pearson r, QWK (marks quantised to 11 ordinal bins), within 0.10 of max; 95 % CI by bootstrap over questions (only 15 test questions, so intervals are wide).

## Candidates
| Id | What | Training |
|---|---|---|
| A1 | TF-IDF (1–2 grams, 3000 features, fit on train) + cosine-to-reference → Ridge (alpha chosen on val) | trained |
| A2 | TF-IDF cosine + token recall → gradient boosting (depth/estimators chosen on val) | trained |
| B0 | all-MiniLM-L6-v2 cosine → isotonic calibration fitted on train (raw cosine is not used as a mark) | calibrated |
| B1 | SBERT cosine, \|u−v\|, u·v → Ridge | trained |
| C | roberta-base, (reference, answer) pair, CLS→linear→sigmoid, MSE, AdamW lr 2e-5, batch 8, max 6 epochs, validation-best epoch = 5 | fine-tuned (~33 min CPU) |
| R1 | lexical token-recall × max marks | none |
| R2 | Condition E (deterministic rubric engine, binary rubric adapter) | none |

## Results (sorted by validation nMAE)
| candidate | val nMAE | test nMAE [95 % CI, question bootstrap] | test MAE (marks) | test QWK | test r | within 0.10 | runtime s |
|---|---|---|---|---|---|---|---|
| C_roberta_base_finetuned | 0.0377 | 0.0382 [0.0303, 0.0466] | 0.706 | 0.980 | 0.984 | 0.900 | 1997 |
| A1_tfidf_ridge | 0.0839 | 0.0812 [0.0744, 0.0880] | 1.296 | 0.934 | 0.938 | 0.689 | 0.4 |
| B1_sbert_features_ridge | 0.0927 | 0.0840 [0.0769, 0.0917] | 1.406 | 0.935 | 0.936 | 0.689 | 33 |
| R1_lexical_token_recall_baseline | 0.1059 | 0.1117 [0.0997, 0.1256] | 1.939 | 0.879 | 0.951 | 0.511 | 0 |
| B0_sbert_cosine_isotonic | 0.1317 | 0.1354 [0.1213, 0.1524] | 2.267 | 0.764 | 0.854 | 0.478 | 33 |
| A2_tfidf_cosine_overlap_gbr | 0.2524 | 0.2478 [0.2355, 0.2583] | 4.156 | 0.000 | – | 0.167 | 0.4 |
| R2_condition_E_binary_rubric | 0.2953 | 0.2094 [0.1774, 0.2443] | 3.544 | 0.682 | 0.733 | 0.333 | 0 |

Diagnostic (not a candidate, trained on train only): length-only ridge → test nMAE 0.067, QWK 0.954.
Per-tier test error (diagnostics.json): RoBERTa is accurate on IRRELEVANT (0.002), MISSING (0.018), MISCONCEPTION (0.031), weaker on FULL (0.073); the SBERT-ridge model is poor on FULL (0.169) and PARTIAL (0.174).

## Reading the numbers honestly
1. **RoBERTa-base is the validation-selected candidate** with the lowest test error (nMAE 0.038, CI 0.030–0.047; QWK 0.98). Its interval does not overlap TF-IDF/SBERT (0.074–0.092), so on this dataset the gap is credible.
2. **A length-only model reaches test nMAE 0.067, better than TF-IDF (0.081), SBERT (0.084) and the lexical baseline (0.112).** The dataset has a word-count/mark correlation of 0.83, so TF-IDF and SBERT results do not demonstrate semantic skill; only RoBERTa clearly beats the length shortcut.
3. Marks are assigned per quality tier and three tiers share one mark (see 02), so every model is largely recognising **template tiers**. High scores say nothing about agreement with human markers.
4. Condition E scores nMAE 0.209 because the dataset has no multi-level rubric, so the engine returns 0 or full marks (AUDIT-M4). It is the explainable component, not a competitive scorer here. "Baseline beats E" still holds; learned models beat both.
5. Raw SBERT cosine, even calibrated (B0), is a weak mark predictor.
6. **Not run:** LLM conditions (proposal A–D/F) — no API credits/quota; RAG vs non-RAG; EngSAF/ASAP-SAS/Mohler/ASAG2024 (not attempted); RoBERTa hyper-parameter search beyond one configuration; multiple seeds (single seed).
7. Artifacts: predictions, histories and results are saved. **The fine-tuned RoBERTa checkpoint was not written to disk**; re-running reproduces it up to CPU nondeterminism. No trained model is wired into `/c3/assess`, which remains the deterministic Condition E pipeline.

## Decision
On the frozen v2 set RoBERTa-base is the preferred scorer; the integrated C3 contribution (rubric levels, evidence, concept status, mind map, lecturer review) remains the deterministic pipeline. Suggested use: RoBERTa as an extra score/confidence signal for lecturer review, after confirming on external data (EngSAF) and human-labelled marks. The conclusion is **provisional**: one seed, 90 test answers from 15 questions, template-like labels.

## Reproduce
`cd ai-services/c3; .venv_c3\Scripts\python.exe -m experiments.model_comparison --run all --out <dir>; python -m experiments.aggregate_comparison <dir>` (packages in `experiments_requirements_lock.txt`; ~35 min on CPU).
