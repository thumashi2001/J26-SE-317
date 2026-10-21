# Demo checkpoint selection (ASSISTments research)

Selection uses **validation return only**. Final-test metrics are recorded for reporting and are **not** used to choose the demo model.

## Rule

1. Among `maskable_ppo` training seeds `{0, 1, 2}`, take the seed with the highest **mean validation episode return** (`comparison_val.json` → `seeds.<seed>.maskable_ppo.val.return.mean`).
2. On a tie, choose the **lowest seed**.
3. Do not retune or retrain after looking at final-test results.

## Applied to bundle `c4_maskable_ppo_research_bundle_20261012T062204868154Z`

| Seed | Mean validation return | Checkpoint SHA-256 |
|---|---|---|
| 0 | 11.939999509043984 | `97c3c2b610d4ac9b9e043e81b66c0aa38db35201f61838257d266f78cb5e25d5` |
| 1 | 11.687999557703728 | `83c1a635c484a02c839e56226f52ed93a17beeb61bc0c7a05a8624645ef390c4` |
| 2 | **11.967999500036232** | `7613e1e28375ca4a844fc064b130b8d8d38d38cf085adf1e52ab73322bd09fca` |

**Selected:** seed **2**  
**Relative path:** `models/seed_2/maskable_ppo_final.zip`  
**Model hash (SHA-256):** `7613e1e28375ca4a844fc064b130b8d8d38d38cf085adf1e52ab73322bd09fca`  
**Protocol:** `c4-env-eval-v1.1`  
**Source run:** `train_full_c4-env-eval-v1.1_20261012T051737.347320+0000`

Algorithm selected on validation (mean across seeds): `maskable_ppo` (11.865) vs `random_valid` (9.429), `recent_performance` (7.945), `weakest_mastery` (7.488), `dqn` (3.044), `ppo` (−36.839). See `MODEL_CARD.md`.
