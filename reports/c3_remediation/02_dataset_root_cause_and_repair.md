# 02 Dataset root cause and repair

## Preserved originals
Archive `datasets/archive/C3-Phase3-v5-FINAL_original/` (hash-verified by the validator) and `datasets/c3_phase3_v5_repaired/` are unchanged. Derived set: `datasets/c3_phase3_v5_repaired_v2/` created by `datasets/repair/derive_v2.py` (refuses to overwrite). Ledger: `v2_repair_ledger.csv` (18 rows), manifest with SHA256 of every file.

## Ratio-concentration (recomputed from `validation_spec.json`)
Definition: share of answers on the 7 most frequent normalised-mark ratios (3 d.p.), excluding 0 and 1; threshold 0.45, hard check.
| Dataset | inner labels | top-7 share | result |
|---|---|---|---|
| repaired (v1) | 380 | 0.7579 | FAIL |
| repaired v2 | 372 | 0.7661 | **FAIL** (threshold unchanged) |
Top-7 in v2: 0.8 ×160, 0.6 ×52, 0.85 ×24, 0.84 ×18, 0.667 ×12, 0.55 ×10, 0.9 ×9.

## Root cause (confirmed)
Marks are assigned by quality tier, not by independent assessment: FULL = 1.0 and IRRELEVANT = 0.0 for all questions; **MOSTLY_CORRECT, MISSING_CONCEPT and MISCONCEPTION receive the same mark in every question (≈0.8)** and PARTIAL ≈0.6. Three of six tiers (50 % of answers) therefore sit on one ratio. Fixing this would require new human marking of 336+ answers; no valid source evidence exists, and relabelling to pass the check would be fabrication. **The failure is not fixed and is disclosed.**

## Repairs actually applied in v2 (all quarantines, no relabelling, validation and test untouched)
| Question | Split | Reason (evidence) | Answers |
|---|---|---|---|
| PP-SE3080-099 | train | near-duplicate of test question PP-SE3080-107, TF-IDF cosine 0.903 > 0.8 (audit 03 §C); removing the train copy keeps the test set unchanged | 6 |
| PP-SE3080-102 | train | anomalous labels: PARTIAL = FULL, MOSTLY_CORRECT = 0, identical strings (`review_queue.csv`) | 6 |
| PP-SE3040-009 | train | code/diagram-dependent, cannot be assessed from text (scope review) | 6 |
Result: eligible 558 (was 576): train 402, validation 66, test 90; quarantine 373; controls 71.

## Validation of v2 (`validate_repaired.py datasets/c3_phase3_v5_repaired_v2`)
- Near-duplicate cross-split check: **pass** (max cosine 0.648, 0 pairs above 0.8).
- Ratio-concentration: **FAIL 0.7661** (unchanged cause).
- Length–mark Pearson: 0.832 (spec 0.4, report-only warning) — still a shortcut risk for learned models.
- Derivation-consistency checks fail by design because they compare against the v1 manifest: `schema_required_fields` (rows still carry dataset_version v1), `counts_reconcile`, `preserved_vs_original` (23 quarantine fields differ from original: the 18 moved rows' text fields), `repair_manifest_consistent`. These are artefacts of deriving v2 from v1, not data defects; no eligible answer text, mark or split differs from the original.
- Unresolved (inherited): 391/487 criterion ids undescribed, 9 cross-question duplicate answers, 96 constant IRRELEVANT sentence, no expert labels.

## Remaining limitation
The primary dataset is researcher-constructed and template-like; metrics on it show how well a method recovers *tiers*, not human marking agreement. Benchmarks (EngSAF etc.) remain the planned external check (DEC-06 vs proposal p.30).
