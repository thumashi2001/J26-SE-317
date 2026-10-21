# 02 Dataset reconciliation (all numbers recomputed from the CSV files by answer_id)

Sources: `ai-services/c3/datasets/c3_phase3_v5_repaired/*` and the byte-exact original `datasets/archive/C3-Phase3-v5-FINAL_original/` (all 16 SHA256SUMS entries verified OK). Scripts used: scratchpad `audit/independent.py` (Opus) and `audit/agentA/t1.py` (delegated, results cross-checked). Full check table: `reconciliation.csv`.

| Check | Expected | Actual | Result | Label |
|---|---|---|---|---|
| Original questions / answers / rubric rows | 167 / 1,002 / 230 | 167 / 1,002 / 230, ids unique | PASS | V |
| Eligible + quarantine + controls | 576 + 355 + 71 = 1,002 | 576 + 355 + 71 = 1,002 | PASS | V |
| Pairwise overlap by `answer_id` | 0 | eligible∩quarantine 0, eligible∩controls 0, quarantine∩controls 0 | PASS | V |
| Union == original id set | equal | missing 0, extra 0 | PASS | V |
| Eligible per split | train 420 / val 66 / test 90 | 420 / 66 / 90 | PASS | V |
| Original per split | 702 / 150 / 150 | 702 / 150 / 150 | PASS | V |
| Eligible rows unchanged vs original (split, label, mark, text) | 0 diffs | 0 diffs | PASS | V |
| Eligible questions with exactly 6 variants | 96 | 96 (all six tiers once) | PASS | V |
| Control questions with 1 variant | 71 | 71 | PASS | V |
| Question-id overlap across splits | 0 | 0 | PASS | V |
| `0 ≤ expected_mark ≤ max_marks`; `max_marks == question marks` | 0 violations | 0 | PASS | V |
| Literal `nan`/`None`/empty answer in eligible set | 0 | 0 `nan` cells, 0 empty answers | PASS | V |
| Every original answer has a ledger row | all | 546/1,002; the 456 without a row are the eligible answers with `repair_status=unchanged` (no change to record). All 355 quarantined and 71 controls have rows. | PASS (by design) | V |
| Duplicate question text | 0 | 0 exact | PASS | V |
| Tier mark ordering FULL ≥ MOSTLY ≥ PARTIAL ≥ MISSING ≥ MISCONCEPTION ≥ IRRELEVANT | informational | violated in 93 questions (see below) | INFO | V |
| Rubric marks == question marks (all 167) | 0 | 7 re-keyed rows on ineligible questions disagree | WARN | V |

## Provenance
- Every original answer is in exactly one of eligible / quarantine / controls (V). Quarantine and control rows keep the original values (V).
- 71 questions are ineligible: 63 block A + 8 block B (V). Each has 5 quarantined answers and 1 control (V).

## Label-structure findings (V)
- In **all 96** eligible questions, `MOSTLY_CORRECT`, `MISSING_CONCEPT` and `MISCONCEPTION` have **identical** marks (96/96).
- `PARTIAL` > `MOSTLY_CORRECT` in 10 questions.
- **`PP-SE3080-102`** (single criterion, 20 marks): FULL = 20, PARTIAL = 20 (identical text to FULL), MOSTLY_CORRECT = 0, MISSING = 0, MISCONCEPTION = 0. This is how the original labelled it (unchanged by the repair). The question is eligible and sits in the train split.
- Only 3 non-IRRELEVANT eligible answers have mark 0 (all in PP-SE3080-102).

## Duplicate answer strings (eligible, V)
- 96 answers share one IRRELEVANT sentence: intentional template control, flagged, spans all three splits.
- 13 further answers in 6 strings are shared across answers: 4 are flagged `needs_review` (same-question pairs); **9 answers in 4 strings are shared across different questions, 4 strings cross splits, and are not flagged** (accidental templating; they come from identical concept lists).

## Not verified
Whether any eligible answer is semantically wrong for its question (no expert review exists).
