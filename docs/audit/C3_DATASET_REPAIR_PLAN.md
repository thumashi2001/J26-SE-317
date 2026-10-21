# C3 dataset repair — proposed plan (Phase 2) — awaiting approval

Principle: **start from the original `C3-Phase3-v5-FINAL`** (not from the earlier in-place repair); apply a repair only when the source data, rubric or a documented rule proves the correct value; otherwise quarantine with a reason. No new questions, no new answer variants, no generic filler, no split changes, no mark inferred from a tier name. Output goes to a new versioned directory `ai-services/c3/datasets/c3_phase3_v5_repaired/` (version string `C3-Phase3-v5-REPAIRED-r2`); the original stays untouched in `datasets/archive/`.

## Proposed actions (per finding in `C3_DATASET_REPAIR_PHASE1_BASELINE.md`)

| Finding | Action | Status label in manifest | Records |
|---|---|---|---|
| F1 literal `nan` answers (252, block A) | **Quarantine** — text unrecoverable. Row kept in `quarantine.csv` with original values. | `quarantined: unrecoverable_nan` | 252 |
| F2 IRRELEVANT with flat 10.0 (71) | **Repair** `expected_mark` → 0 and `criterion_marks` → zeros, justified by the documented IRRELEVANT=0 policy + answer text stating off-topic. Keep the original in the manifest. | `repaired: documented_label_policy` | 71 |
| F2 other tiers with flat 10.0 on replacement questions (MISCONCEPTION ×71 and the 8-question block's FULL/MOSTLY/PARTIAL/MISSING ×32) | **Quarantine** — no evidence supports any specific mark. | `quarantined: unsupported_flat_mark` | 103 (+ the 252 above are already counted in F1) |
| F3 rubric id mismatch (8 rubric rows) | **Repair** by re-keying to `SYN-REPL-<id>` using `source_replaced_question_id`. | `repaired: id_mapping_from_source_field` | 8 |
| F4 criterion-id naming | **Repair** where `R-<id>` maps to an existing rubric row (92 ids); **document** the rest as `rubric_incomplete` (no descriptions invented). | `repaired` / `limitation` | 92 / 395 ids |
| F5 `nan` list elements | **Repair**: remove the empty element, keep original value in the manifest. | `repaired: removed_empty_element` | 29 cells |
| F6 identical text within a question | **Review queue** (proposed: keep, flag `duplicate_text_review`; no rewrite). | `needs_review` | 4 |
| F7 constant template strings | **Keep**, flag `template_negative_control`; never moved/removed; counted in the card as a limitation. | `flagged` | 167 IRRELEVANT + 71 MISCONCEPTION |
| F8 ordering | **No change**; informational statistics only. | — | — |
| F9 overloaded `marks` | **Add** derived column `max_marks` (= question bank marks); `marks` untouched. | `schema_addition` | 1,002 |
| F10–F11 placeholders / empty references | **Flag only**. | `limitation` | 95 / 576 |
| F12 code/diagram scope | **Flag** `scope_review` (initially the two confirmed items); the human decides exclusion. | `needs_review` | 2+ questions |
| F13 QA claims | Regenerate `05_FINAL_QA_RESULTS` from real checks; set `qa` in the manifest to the real result. | — | — |

## Resulting eligible set (projection, before F6/F12 decisions)
Metric-eligible answers: **576 canonical** (96 q) + **71 repaired IRRELEVANT controls** = 647 of 1,002 (64.6%); quarantined 355 (252 nan + 103 unsupported flat marks).
Per split (answers): train 420 + 47 = **467**, validation 66 + 14 = **80**, test 90 + 10 = **100** (canonical + repaired IRRELEVANT controls; splits unchanged). Quarantine: 252 (`nan`) + 63 MISCONCEPTION (block A) + 40 non-IRRELEVANT (block B) = 355. Policy basis: `datasets/README.md` line 57 (“IRRELEVANT … 0 marks (0.0)”) and the dataset card (“IRRELEVANT … 0%”); the MISCONCEPTION policy (“0 marks on the *affected criterion*”) cannot be applied to replacement questions because their generic two-criterion rubrics do not identify the affected criterion. The script will recompute and verify these totals.
**Effect on comparability:** the held-out test split falls from 150 to 90 canonical answers (+10 IRRELEVANT controls); the 71 replacement questions retain only a negative-control row, so per-question variant counts become uneven (96 questions × 6, 71 questions × 1). Metrics must be recomputed and reported as *new*, not comparable to any earlier figure.

## Phases
- **Phase 3 (sample):** apply the actions to 3 canonical + 2 block-A + 1 block-B questions only; write the repair manifest, quarantine, review queue; no bulk changes.
- **Phase 4:** run the validator on the sample; show before/after diffs per record.
- **Phase 5:** stop for your review. **Phase 6:** bulk repair, full validation, documentation.

## Validation I will run (without weakening any check)
Schema/required fields; counts; mark ranges; label values; rubric associations; literal-`nan` and empty scan; duplicates (exact/normalised/cross-split); leakage (question-disjoint splits, near-duplicate question text); per-question coverage; label distribution; ratio-concentration with the existing definition and 0.45 threshold. **Expected honest outcome:** ratio-concentration will probably still exceed 0.45 on the canonical labels (0.758 before any repair); if so I report it and ask for a decision rather than change the threshold or the labels.

## Decisions needed from you
1. Quarantine the 252 unrecoverable `nan` answers and the 103 unsupported flat-mark answers (355 total)? — alternative: also quarantine the 71 IRRELEVANT controls so the replacement block disappears entirely.
2. Keep the template negative controls (IRRELEVANT/MISCONCEPTION constants) as flagged controls?
3. Add the derived `max_marks` column (additive schema change)?
4. F12: which past-paper items go to the scope review queue (I can only confirm 2 by evidence).
