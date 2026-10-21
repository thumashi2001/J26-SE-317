# C4 v1 import inventory

- **Source ZIP:** `C:\Users\Deshan\Documents\GitHub\Softedge\Suwani_Research\C4_v1_exports\C4_v1_07_08_complete_20261014T004739324637Z.zip`
- **ZIP SHA-256:** `0ea4991b6eb945e75595c527cfdad7eb9ae1844a5f1e73da092bcfc1068d782f` (77 091 828 bytes)
- **BACKUP_MANIFEST:** 333/333 files verified (SHA-256 + byte size); 0 missing; 0 unexpected
- **Export bundle checksums:** path **38**/38; supervised **25**/25
- **First import:** wrote=539; conflicts=0
- **Idempotent re-import:** wrote=0; skipped_identical=539; conflicts=0

## Source runs (from manifest)

| Alias in ZIP | Drive / expected run name |
|---|---|
| `runs/07_se_path_simulation_v1/` | `train_full_se-path-sim-v1_20261013T181643.681Z` |
| `runs/08_se_supervised_simulation_v1/` | `train_full_se-supervised-sim-v1_20261014T002241.664Z` |

Both expected completed runs are present in **one** archive (no mixing). Original ZIP unchanged.

## Destination mapping

| Source | Destination |
|---|---|
| Path full run | `local-colab-archive/v1/train_full_se-path-sim-v1_20261013T181643.681Z/` |
| Supervised full run | `local-colab-archive/v1/train_full_se-supervised-sim-v1_20261014T002241.664Z/` |
| Path export_bundle | `runtime-artifacts/se_path_sim_v1/train_full_se-path-sim-v1_20261013T181643.681Z/export_bundle/` |
| Supervised export_bundle | `runtime-artifacts/se_supervised_sim_v1/train_full_se-supervised-sim-v1_20261014T002241.664Z/export_bundle/` |
| Executed notebooks | `experiments/notebooks/v1/07_…_executed.ipynb`, `08_…_executed.ipynb` |
| Presentation (JSON/CSV/MD only) | `experiments/results/se_*_simulation_v1/<run>/` (97 path + 44 supervised files) |

## Models / checkpoints imported

**Path (MaskablePPO)** — training seeds **0, 1, 2**:

- Archive finals: `…/seed_{0,1,2}/maskable_ppo/maskable_ppo_final.zip`
- Export finals: `…/export_bundle/models/seed_{0,1,2}/maskable_ppo_final.zip`
- Intermediate step checkpoints retained under archive only
- **No deployment checkpoint chosen** from final-test returns

**Supervised (selected on validation):**

- `response_selected.joblib` ← `hist_gradient_boosting_classifier`
- `exam_score_selected.joblib` ← `ridge_regression`
- `pass_selected.joblib` ← `logistic_regression`

## Contract verification (saved vs local v1)

| Check | Result |
|---|---|
| Path protocol `se-path-sim-v1` | pass |
| Supervised protocol `se-supervised-sim-v1` | pass |
| Catalogue 46 / Y3S1=28 / Y3S2=18 | pass |
| Catalogue SHA-256 `95aaba520a28a494…1622` | pass |
| Obs dim 96 / actions 46 | pass |
| Response feats 54 / exam feats 98 | pass |

## Saved metrics (source of truth; not edited)

**Path final-test** (`final_simulator_test/test_summary.csv`):

- MaskablePPO Y3S1 `return_mean` = `11.157332906126973`
- MaskablePPO Y3S2 `return_mean` = `11.082666223744546`

**Supervised final-test** (`final_test/final_test_metrics.json`):

- Response accuracy = `0.6562632098069607`
- Exam-score MAE = `0.06862722330047728`
- Pass accuracy = `0.7966666666666666`

Markers: `domain=se_simulation`, `synthetic=true`, `simulation_only=true`,
`real_exam_validation=false`. Validation selection remains separate
(`SELECTION_FROZEN.json` / `selection_val.json`).

## Notebooks

| File | Code cells | With outputs | Errors | Secret-pattern hits |
|---|---|---|---|---|
| `07_se_path_simulation_v1_executed.ipynb` | 15 | 14 | 0 | 0 |
| `08_se_supervised_simulation_v1_executed.ipynb` | 12 | 10 | 0 | 0 |

Original notebook bytes preserved; not re-executed.

## Git hygiene

| Path class | Status |
|---|---|
| `local-colab-archive/v1/**` | ignored |
| `runtime-artifacts/se_*_sim_v1/**` | ignored |
| `experiments/notebooks/v1/*.ipynb` | eligible |
| `experiments/results/se_*_simulation_v1/**/*.{json,csv,md}` | eligible |
| `c4-se-*-v1-source-colab.zip`, `C4_v1_07_08_complete_*.zip` | ignored (c4 `.gitignore`) |
| Active inference loaders | still v0 / ASSISTments (unchanged) |

## Exact repo files touched by this import task

- `ai-services/c4/.gitignore`
- `ai-services/c4/docs/VIVA_EVIDENCE_INDEX.md`
- `ai-services/c4/docs/C4_V1_IMPORT_INVENTORY.md`
- `ai-services/c4/docs/C4_V1_IMPORT_REPORT.json`
- `ai-services/c4/experiments/notebooks/README.md`
- `ai-services/c4/experiments/notebooks/v1/*_executed.ipynb`
- `ai-services/c4/experiments/results/se_path_simulation_v1/**`
- `ai-services/c4/experiments/results/se_supervised_simulation_v1/**`
- `ai-services/c4/scripts/import_c4_v1_complete_backup.py`
- plus gitignored bulk under `local-colab-archive/v1/` and `runtime-artifacts/se_*_sim_v1/`

## Non-claims / blockers

- Import + evidence organization only — **not** model serving or student integration
- No supervised→RL wiring
- Blockers: **none**

Machine-readable detail: [`C4_V1_IMPORT_REPORT.json`](C4_V1_IMPORT_REPORT.json).
