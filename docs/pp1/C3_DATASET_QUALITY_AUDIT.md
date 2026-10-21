# C3 dataset quality audit and repair report (2026-10-21)

Supersedes the earlier audit. Evidence labels: **[executed]** computed by a script in this repository on 2026-10-21; **[doc]** reported by older documentation and not recomputed.
Detail: `docs/audit/C3_DATASET_REPAIR_PHASE1_BASELINE.md` (findings), `docs/audit/C3_DATASET_REPAIR_PLAN.md` (plan and decisions), `docs/audit/C3_DATASET_REPAIR_SAMPLE_DIFF.md` (six-question sample), `ai-services/c3/datasets/c3_phase3_v5_repaired/` (repair_manifest.csv, quarantine.csv, review_queue.csv, validation_report.json, metrics_report.json).

## 1. What was done
The **existing** dataset `C3-Phase3-v5-FINAL` (167 questions / 1,002 answers, original preserved byte-exact in `ai-services/c3/datasets/archive/`) was repaired in a new versioned directory (`C3-Phase3-v5-REPAIRED-r2`). Nothing was generated or reworded; question/answer ids, labels and split assignments were preserved. A value was repaired only when the data, the rubric or a documented policy proves it; everything else was quarantined or flagged.

## 2. Counts [executed]
| | original | repaired |
|---|---|---|
| questions | 167 | 96 eligible + 71 ineligible |
| answers | 1,002 | 576 eligible + 355 quarantined + 71 repaired ineligible controls (= 1,002; asserted by code and test) |
| eligible per split (answers) | train 702 / val 150 / test 150 | train 420 / val 66 / test 90 |
| rubric rows | 230 | 230 (8 re-keyed) |

Quarantined 355: 252 `unrecoverable_nan` (the answer text was literally `nan` or contained `nan` in place of a concept name; no source holds the lost text) + 103 `unsupported_flat_mark` (flat 10.0 marks with no rubric/answer evidence for any specific mark). Repaired 71: replacement-question IRRELEVANT answers 10.0 → 0.0 (documented policy `datasets/README.md` "IRRELEVANT … 0 marks"; canonical precedent 96/96 already 0.0); kept outside the primary set because the dataset's own rule is 6 variants per question and keeping one-row questions would inflate the IRRELEVANT share (16.7% → 25–31%) and make a trivial cue rule (precision 0.994, recall 1.0).

## 3. Exclusion report
All 71 replacement questions are ineligible (question-level reason `question_has_only_one_valid_variant`); 96 canonical questions (47 past-paper + 49 native synthetic) remain eligible. Ledger: 1,023 rows (`repair_manifest.csv`): flagged 411, repaired 253, quarantined 355, needs_review 4. The held-out **test split falls from 150 to 90 answers (25 → 15 questions)**; all test records were retained or documented (none silently dropped).

## 4. Validation [executed] (`validation_report.json`; no check was weakened)
Hard checks passing: files/schema, counts reconcile, id uniqueness, split files consistent, score range, label values, IRRELEVANT marks zero, rubric association and sums (eligible), no literal `nan`/`None` in eligible data, no duplicate rows or question text, question-disjoint splits, 96/96 eligible questions have exactly 6 variants, criterion marks sum to expected mark, quarantine fidelity.
**Hard check FAILING: ratio-concentration = 0.758 (threshold 0.45)** — unchanged from the original (0.758). It is inherited from the canonical labels (marks cluster on 0.8/0.6/0.85/…); the threshold and labels were not changed. A decision is needed (see §6).
Warnings (report-only): 4 unflagged duplicate strings shared across questions/splits (9 answers); one question pair across splits with TF-IDF cosine 0.903 (> 0.8: PP-SE3080-099 / PP-SE3080-107); criterion-id map 96 resolved / 391 unresolved; 63 literal `nan` cells remain inside the ineligible controls file; answer-length vs mark Pearson **0.81** on the eligible set (spec limit 0.4; the original's 0.089 was an artefact of the flat-mark block — canonical-only original is also 0.81).

## 5. Recomputed metrics [executed, offline, nothing tuned] — not comparable to older figures
| set | method | n | MAE | RMSE | r | within ±2 marks | MAE 95% CI |
|---|---|---|---|---|---|---|---|
| repaired test | lexical baseline | 90 | 1.939 | 2.616 | 0.974 | 62.2% | [1.58, 2.31] |
| repaired test | Condition E | 90 | 3.544 | 5.885 | 0.801 | 57.8% | [2.63, 4.58] |
| original test (like-for-like, failures excluded) | lexical baseline | 150 | 4.637 | 6.050 | 0.759 | 40.0% | [4.03, 5.29] |
| original test (like-for-like) | Condition E | 150 | 5.993 | 7.710 | 0.685 | 36.0% | [5.22, 6.76] |

Documentation vs recomputation: Condition E MAE 4.640 / RMSE 7.220 / r 0.7243 **reproduce exactly** with the legacy settings (which scored 15 of 150 failed calls as 0.0 — equal to their IRRELEVANT label — flattering Condition E; like-for-like MAE is 5.993). The documented lexical MAE 5.609 **did not reproduce** (5.369). On the repaired test split the lexical baseline beats Condition E on MAE, RMSE and r; Condition E scores MISCONCEPTION and MISSING_CONCEPT identically (their canonical marks are identical per question) and is poor on PARTIAL/MOSTLY_CORRECT. LLM conditions A–D/F were **not run** (free-tier quota; OpenAI has no credits).

## 6. Remaining limitations / decisions needed
- Ratio-concentration fails (inherited). Options: accept as a documented limitation of researcher-constructed labels, redefine the metric (needs approval), or re-label (not done: no evidence supports new marks).
- Rubrics: criterion descriptions for the 487 answer criterion ids are unrecoverable (391 unresolved); canonical reference answers are empty/generic; question-bank concept lists have comma-split artefacts.
- All 96 canonical IRRELEVANT answers are one constant sentence (learnable cue); canonical MOSTLY/MISSING/MISCONCEPTION marks coincide within a question.
- Scope: PP-SE3040-001/002 flagged `scope_review` (need code); other past-paper items unverified.
- Ground truth is researcher-constructed; **no expert validation**.
- The experiment framework (`experiments/`, `datasets/loader.py`) targets the removed v6 schema and needs an adapter before LLM conditions can run on the repaired set.
