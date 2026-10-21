# 04 Metric reproduction (offline; no model calls; nothing tuned)

Method: predictions are produced by the repository engines (`services.marking.marking_engine.mark_answer`, the token-overlap baseline in `datasets/repair/evaluate_repaired.py::lexical_baseline`); **all metrics below are computed with my own numpy code** (scratchpad `audit/independent.py`, `independent3.py`), not with `evaluate_repaired.metrics()`. Machine-readable: `metric_reproduction.json`.

## 1. Repaired eligible TEST split (primary population; file `controlled_answers_test.csv`, 90 answers, 15 questions)
Same 90 answer ids for both methods (V). max marks = question marks. Rubric = `build_legacy_rubric` from the single question-level rubric row (all 90 `rubric_file`).
| Metric | Reported | Reproduced | |Δ| | Label |
|---|---|---|---|---|
| Baseline MAE / RMSE / r | 1.939 / 2.616 / 0.974 | 1.9387 / 2.6159 / 0.9740 | < 0.001 | V |
| Baseline within ±2 marks / within 10 % of max | 62.2 % / 51.1 % | 62.22 % / 51.11 % | 0 | V |
| Condition E MAE / RMSE / r | 3.544 / 5.885 / 0.801 | 3.5444 / 5.8850 / 0.8010 | < 0.001 | V |
| Condition E within ±2 / within 10 % | 57.8 % / 33.3 % | 57.78 % / 33.33 % | 0 | V |
Failure policy: 0 failed, 0 not evaluable, 0 zero-substituted (V).

**Condition E on this set is a binary 0-or-full-marks predictor (V):** all 90 predictions are exactly 0 or the question's max marks (distinct values 0, 10, 12, 25, 30). `build_legacy_rubric` turns the question-level rubric row into two levels (L0 = 0, L1 = full) requiring the first two expected concepts. It therefore cannot award partial credit and is not a test of rubric-aware partial-credit marking (I: strong). Per-tier MAE: E has 0.0 on FULL and IRRELEVANT and 7.2–7.7 on PARTIAL/MOSTLY_CORRECT.

**The "lexical baseline" is not cosine similarity** (V): `|answer tokens ∩ reference tokens| / |reference tokens| × max_marks`, against question-bank references that are generic templates listing the concepts. The docs/`conditions.py` describe cosine. The two definitions are different functions; results are not comparable with a future `run_experiments` baseline.

Why the baseline beats E here (I): marks are tier-structured and track answer length (§03 B); token recall against a concept-list template tracks both.

## 2. Original TEST split (150 answers) – legacy vs like-for-like
| Quantity | Reported | Reproduced | Δ | Notes | Label |
|---|---|---|---|---|---|
| E legacy MAE / RMSE / r / within2 | 4.640 / 7.220 / 0.7243 / 84 of 150 | 4.6400 / 7.2203 / 0.7243 / 84 of 150 | 0 | max = `answers.marks` column, fallback rubric, **failed calls scored 0** | V |
| Failed marking calls (legacy) | 15 | 15, all `RubricValidationError`, **all IRRELEVANT answers with `marks` = 0 ⇒ `max_marks` 0**; gold of all 15 is 0.0 | 0 | scored 0 = gold ⇒ flatters E | V |
| E legacy, failures **excluded** (n = 135) | – | MAE 5.1556, RMSE 7.6109, r 0.7321, within2 69/135 | – | sensitivity | V |
| E like-for-like (max = question marks) | 5.993 / 7.710 / 0.685 | 5.9933 / 7.7102 / 0.6847 | 0 | 0 failures, 12 answers on fallback rubric | V |
| Baseline legacy MAE (documented) | 5.609 | **5.3694** (recomputed 5.369; 37/150 within 2) | **0.240** | **NOT reproduced**; no definition tried gives 5.609 (cosine×answers.marks 4.628; cosine×question marks 4.805; recall×question marks 4.637) | V |
| Baseline like-for-like | 4.637 / r 0.759 | 4.6374 / 0.7587 | 0 | | V |
| `experiments/results/raw_predictions_test_split.csv` (local, git-ignored, untracked) | 2.547 (E) | `predicted_mark` MAE 2.5467 vs its own `ground_truth_mark` | 0 | matches neither the docs nor the archive ⇒ stale artefact from another data state (I) | V/I |

The documented "17.3 % MAE reduction" (E 4.640 vs baseline 5.609) cannot be supported: the baseline figure is not reproducible, and like-for-like E (5.993) is worse than the baseline (4.637).

## 3. Other checks
- No parameter is fitted on test anywhere in `evaluate_repaired.py`; seed 20261021 for bootstrap only (V by reading). Condition F's fusion fit (`experiments/conditions.py`) uses validation only, but F has never run (V).
- Sensitivity to 100-mark questions (I): the repaired-validation E MAE of 10.95 is driven by the 100-mark `PP-SE3040-001/002` (flagged); absolute MAE and "within ±2 marks" are not scale-free over max marks 10–100, so normalised MAE should be primary.
- Pearson undefined cases: IRRELEVANT tier (gold constant 0) → `None`, reported as undefined (V).
- Every reported number above traces to `metrics_report.json` / my scripts; commands: `python datasets/validate_repaired.py <dir>`, `python -m datasets.repair.evaluate_repaired <dir>` (writes into the dataset dir: **not run** during this audit), and the scratchpad scripts.
