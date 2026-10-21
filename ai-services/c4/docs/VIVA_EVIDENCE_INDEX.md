# C4 viva evidence index

Paths are relative to `ai-services/c4/` unless noted. **Do not retrain** to
regenerate metrics. Active inference uses `runtime-artifacts/`; the Colab Drive
tree is mirrored under `local-colab-archive/AdaptiveLearnSE/` (gitignored bulk).

Backup root used for copy: parent of `BACKUP_INVENTORY.json`
(`Suwani_Research/`, because `C4_Colab_Backup/` was not present after extract).
Copy report: [`../local-colab-archive/COPY_REPORT.json`](../local-colab-archive/COPY_REPORT.json)
(ignored with archive contents; regenerate via `scripts/organize_colab_backup.py`).

---

## Notebook coverage (executed copies)

| Executed notebook | Stages actually present in saved outputs | Cells with outputs | Errors |
|---|---|---|---|
| [`experiments/notebooks/01_assistments_data_preparation_executed.ipynb`](../experiments/notebooks/01_assistments_data_preparation_executed.ipynb) | Config, deps, ZIP extract, Drive dirs, ASSISTments CSV acquire, data prep, quality peek | 15 / 20 code | none |
| [`experiments/notebooks/02_assistments_smoke_training_executed.ipynb`](../experiments/notebooks/02_assistments_smoke_training_executed.ipynb) | **Smoke-only** ASSISTments RL / pipeline cells (`/content` paths) | 6 / 6 code | none |
| [`experiments/notebooks/05_se_path_simulation_executed.ipynb`](../experiments/notebooks/05_se_path_simulation_executed.ipynb) | Deps, ZIP upload, Drive mount, contract, smoke train, comparison; source shows `RUN_FULL_TRAINING = True`; **final eval flag was False** in saved source | 15 / 17 code | none |
| [`experiments/notebooks/06_se_supervised_simulation_executed.ipynb`](../experiments/notebooks/06_se_supervised_simulation_executed.ipynb) | Smoke + gated full + final-test cells; **accuracy table 66.40% / 82.67%** in cell outputs | 13 / 16 code | none |
| [`experiments/notebooks/v1/07_se_path_simulation_v1_executed.ipynb`](../experiments/notebooks/v1/07_se_path_simulation_v1_executed.ipynb) | S1 path v1 full Colab run (`se-path-sim-v1`); smoke + full + final-eval evidence in outputs | 14 / 15 code | none |
| [`experiments/notebooks/v1/08_se_supervised_simulation_v1_executed.ipynb`](../experiments/notebooks/v1/08_se_supervised_simulation_v1_executed.ipynb) | S1 supervised v1 full Colab run (`se-supervised-sim-v1`); smoke + full + final-test | 10 / 12 code | none |

### Missing notebook evidence

- **No executed ASSISTments full-training / final-evaluation notebook** was in the
  backup (`Saved_Colab_Notebooks/` only has data prep + smoke training for
  ASSISTments). Full ASSISTments run folders and metrics exist on disk under
  `local-colab-archive/AdaptiveLearnSE/c4_runs/train_full_*` and the imported
  research bundle — cite those artifacts, not a missing notebook.

Template notebooks under `experiments/*.ipynb` remain **unexecuted** working
copies; do not treat their lack of outputs as Colab evidence.

---

## A. ASSISTments research

### Dataset / provenance / splits

| Item | Path |
|---|---|
| Raw corrected CSV (archive) | [`local-colab-archive/AdaptiveLearnSE/c4_data/raw/skill_builder_data_corrected.csv`](../local-colab-archive/AdaptiveLearnSE/c4_data/raw/skill_builder_data_corrected.csv) |
| Data-prep executed notebook | [`experiments/notebooks/01_assistments_data_preparation_executed.ipynb`](../experiments/notebooks/01_assistments_data_preparation_executed.ipynb) — heading **Step 5 — Run data preparation** |
| Saved metrics (presentation) | [`experiments/results/assistments/`](../experiments/results/assistments/) |
| Response metrics (incl. test accuracy) | [`local-colab-archive/AdaptiveLearnSE/c4_runs/artifacts/response_metrics.json`](../local-colab-archive/AdaptiveLearnSE/c4_runs/artifacts/response_metrics.json) and active [`runtime-artifacts/c4_maskable_ppo_research_bundle_20261012T062204868154Z/artifacts/response_metrics.json`](../runtime-artifacts/c4_maskable_ppo_research_bundle_20261012T062204868154Z/artifacts/response_metrics.json) |
| Response model | `runtime-artifacts/.../artifacts/response_model.joblib` (also archived under `c4_runs/artifacts/`) |
| Full RL run (protocol v1.1) | `local-colab-archive/AdaptiveLearnSE/c4_runs/train_full_c4-env-eval-v1.1_20261012T051737.347320+0000/` |
| Historical smoke runs | `train_smoke_*` under the same `c4_runs/` tree |
| Research export ZIP (archive) | `local-colab-archive/AdaptiveLearnSE/c4_runs/exports/c4_maskable_ppo_research_bundle_20261012T062204868154Z.zip` |
| Model card (repo) | [`MODEL_CARD.md`](../MODEL_CARD.md) |

### Classification accuracy (genuinely computed)

| Claim | Value | Trace |
|---|---|---|
| ASSISTments response **test accuracy** | **66.62%** (`0.6662353520074357`) | `response_metrics.json` → `test_held_out.accuracy` |

Do **not** call ROC-AUC (`~0.71` in the same file) “accuracy”.

### Inference

| Item | Path / docs |
|---|---|
| Endpoints | `GET /ready`, `GET /v1/research/catalogue`, `POST /v1/research/predict` — [`app/main.py`](../app/main.py) |
| Loader | [`services/inference/loader.py`](../services/inference/loader.py) |
| Demo checkpoint notes | [`docs/DEMO_CHECKPOINT_SELECTION.md`](DEMO_CHECKPOINT_SELECTION.md) |

---

## B. SE synthetic RL (`se-path-sim-v0`)

### Executed notebook

- [`experiments/notebooks/05_se_path_simulation_executed.ipynb`](../experiments/notebooks/05_se_path_simulation_executed.ipynb)
- [`experiments/results/se_path_simulation/`](../experiments/results/se_path_simulation/)
  - **§7 Smoke training + validation selection**
  - **§9 Full training (gated)** — saved source has `RUN_FULL_TRAINING = True`
  - **§10 Final simulator evaluation** — saved source has `RUN_FINAL_EVALUATION = False`
    (final-test artifacts below were produced in the Colab run tree; not claimed
    from this notebook’s final-eval cell output)

### Full run artifacts (archive; SHA match active import)

| Item | Path |
|---|---|
| Full run root | `local-colab-archive/AdaptiveLearnSE/c4_runs/se_path_sim_v0/train_full_se-path-sim-v0_20261012T083811.995Z/` |
| Validation selection | `.../selection_val.json` / `export_bundle/selection_val.json` |
| Final test summary | `.../export_bundle/final_simulator_test/test_summary.csv` |
| Model card | `.../export_bundle/MODEL_CARD_SE_SIM.md` and repo [`MODEL_CARD_SE_SIMULATION.md`](../MODEL_CARD_SE_SIMULATION.md) |
| Active import | `runtime-artifacts/se_path_sim_v0/c4_se_simulation_bundle_20261012T084659312700Z/` |
| Smoke run (historical) | `.../train_smoke_se-path-sim-v0_20261012T083335.645Z/` |

### Reward metric (not “accuracy”)

| Claim | Value | Trace |
|---|---|---|
| MaskablePPO mean final return | **≈ 8.7042** | `test_summary.csv` row `maskable_ppo`,`return_mean` = `8.704204247395198` |

Invalid-action rate in the same CSV is **0.0** — report as invalid-action rate, not accuracy.

### Inference

| Item | Docs |
|---|---|
| Endpoints | `GET /v1/se-simulation/ready`, `catalogue`, `POST .../predict` |
| Docs | [`docs/SE_SIMULATION_INFERENCE.md`](SE_SIMULATION_INFERENCE.md), [`docs/SE_DEMO_CHECKPOINT_SELECTION.md`](SE_DEMO_CHECKPOINT_SELECTION.md) |

---

## C. SE synthetic supervised models (`se-supervised-sim-v0`)

### Executed notebook

- [`experiments/notebooks/06_se_supervised_simulation_executed.ipynb`](../experiments/notebooks/06_se_supervised_simulation_executed.ipynb)
- [`experiments/results/se_supervised_simulation/`](../experiments/results/se_supervised_simulation/) incl. [`classification_accuracy_extracted_from_notebook.json`](../experiments/results/se_supervised_simulation/classification_accuracy_extracted_from_notebook.json)
  - **§6 Smoke** / **§7 Validation selection** / **§8 Full training** / **§9 Final-test**
  - **Accuracy table (threshold 0.5)** present in **code cell execution_count 17** outputs:
    - response: **9425 / 14194 → 66.40%**
    - pass: **248 / 300 → 82.67%**

### Full run artifacts

| Item | Path |
|---|---|
| Full run root | `local-colab-archive/AdaptiveLearnSE/c4_runs/se_supervised_sim_v0/train_full_se-supervised-sim-v0_20261012T130156.573Z/` |
| Frozen selection | `.../SELECTION_FROZEN.json` |
| Final-test JSON | `.../final_test/final_test_metrics.json` |
| Model cards | `.../model_cards/MODEL_CARD_{RESPONSE,EXAM_SCORE,PASS}.md` |
| Selected models | `.../models/{response,exam_score,pass}_selected.joblib` |
| Synthetic data | `.../synthetic_data/scenarios/{baseline,high_noise,easy_bank}/` |
| Splits | `.../split_ids.json` |
| Active import | `runtime-artifacts/se_supervised_sim_v0/c4_se_supervised_bundle_20261012T131046728530Z/` |
| Smoke run | `.../train_smoke_se-supervised-sim-v0_20261012T092837.258Z/` |

### Metrics — what is / is not in saved JSON

| Claim | Value | Saved evidence | Gap? |
|---|---|---|---|
| SE response **classification accuracy** @ 0.5 | **66.40%** (9425/14194) | Executed notebook 06 cell outputs | **Yes for JSON**: `final_test_metrics.json` stores log_loss / Brier / ROC-AUC / n=14194, **not** accuracy |
| SE pass **classification accuracy** @ 0.5 | **82.67%** (248/300) | Same notebook cell | **Yes for JSON**: `pass_test` has log_loss / Brier / ROC-AUC / n=300, **not** accuracy |
| SE exam score **MAE** | **7.64 percentage points** (`0.07643764690160464` on [0,1] score) | `final_test_metrics.json` → `exam_score_test.mae` | No |
| Response / pass **ROC-AUC** | ~0.725 / ~0.916 (final test) | same JSON | Report as ROC-AUC, **not** accuracy |

Primary selection metrics remain **log_loss** (response/pass) and **MAE** (exam score) in `SELECTION_FROZEN.json`.

### Inference

| Item | Docs |
|---|---|
| Endpoints | `GET /v1/se-supervised-simulation/ready`, `POST .../response`, `.../exam-score`, `.../pass` |
| Docs + sample requests | [`docs/SE_SUPERVISED_INFERENCE.md`](SE_SUPERVISED_INFERENCE.md) |
| Feature schemas | active bundle `export_bundle/feature_schema_{response,exam}.json` |

---

## D. SE synthetic RL v1 (`se-path-sim-v1`, S1 / 46 topics) — import only

**Not wired into active inference.** Student UI remains heuristic. Import report:
[`C4_V1_IMPORT_REPORT.json`](C4_V1_IMPORT_REPORT.json) /
[`C4_V1_IMPORT_INVENTORY.md`](C4_V1_IMPORT_INVENTORY.md).

| Item | Path |
|---|---|
| Source ZIP | `Suwani_Research/C4_v1_exports/C4_v1_07_08_complete_20261014T004739324637Z.zip` |
| Executed notebook | [`experiments/notebooks/v1/07_se_path_simulation_v1_executed.ipynb`](../experiments/notebooks/v1/07_se_path_simulation_v1_executed.ipynb) |
| Full run archive | `local-colab-archive/v1/train_full_se-path-sim-v1_20261013T181643.681Z/` |
| Export bundle (runtime tree) | `runtime-artifacts/se_path_sim_v1/train_full_se-path-sim-v1_20261013T181643.681Z/export_bundle/` |
| Presentation evidence | [`experiments/results/se_path_simulation_v1/train_full_se-path-sim-v1_20261013T181643.681Z/`](../experiments/results/se_path_simulation_v1/train_full_se-path-sim-v1_20261013T181643.681Z/) |
| Checkpoints (seeds 0/1/2) | `…/seed_{0,1,2}/maskable_ppo/maskable_ppo_final.zip` (+ intermediate checkpoints in archive) |
| Catalogue | 46 topics; Y3S1=28; Y3S2=18; SHA-256 `95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622` |
| Observation | dim **96**; actions **46** |

### Final-test returns (simulation-only; not for deployment checkpoint selection)

| Semester | Method | `return_mean` (saved CSV) |
|---|---|---|
| Y3S1 | MaskablePPO | **11.157333** (`11.157332906126973`) |
| Y3S2 | MaskablePPO | **11.082666** (`11.082666223744546`) |

Source: `…/final_simulator_test/test_summary.csv`. Validation selection remains in
`selection_val.json` / `SELECTION_FROZEN.json` (separate from final-test).

Labels retained: `domain=se_simulation`, `synthetic=true` (export manifest).

---

## E. SE synthetic supervised v1 (`se-supervised-sim-v1`, S1 / 46 topics) — import only

**Not wired into active inference.** Do **not** auto-connect response model into
the RL simulator. Same import report as §D.

| Item | Path |
|---|---|
| Executed notebook | [`experiments/notebooks/v1/08_se_supervised_simulation_v1_executed.ipynb`](../experiments/notebooks/v1/08_se_supervised_simulation_v1_executed.ipynb) |
| Full run archive | `local-colab-archive/v1/train_full_se-supervised-sim-v1_20261014T002241.664Z/` |
| Export bundle (runtime tree) | `runtime-artifacts/se_supervised_sim_v1/train_full_se-supervised-sim-v1_20261014T002241.664Z/export_bundle/` |
| Presentation evidence | [`experiments/results/se_supervised_simulation_v1/train_full_se-supervised-sim-v1_20261014T002241.664Z/`](../experiments/results/se_supervised_simulation_v1/train_full_se-supervised-sim-v1_20261014T002241.664Z/) |
| Selected models | response=`hist_gradient_boosting_classifier`; exam_score=`ridge_regression`; pass=`logistic_regression` |
| Feature dims | response **54**; exam **98** |

### Final-test metrics (saved JSON; comparison only)

| Target | Metric | Value |
|---|---|---|
| Response | accuracy @ 0.5 | **0.6562632098069607** |
| Exam score | MAE | **0.06862722330047728** |
| Pass | accuracy @ 0.5 | **0.7966666666666666** |

Source: `…/final_test/final_test_metrics.json`. Also stores log_loss / Brier /
ROC-AUC. Markers: `domain=se_simulation`, `synthetic=true`,
`simulation_only=true`, `real_exam_validation=false`.

Primary selection metrics remain validation **log_loss** / **MAE** in
`SELECTION_FROZEN.json` — keep separate from final-test.

---

## Active vs archive (SHA-256)

From `COPY_REPORT.json` (no automatic replace of active models):

- SE path sim **manifest + 3 MaskablePPO zips**: identical to archive full-run export.
- SE supervised **manifest + 3 joblib models**: identical to archive full-run export.
- ASSISTments research bundle remains under `runtime-artifacts/c4_maskable_ppo_research_bundle_.../` (unchanged by this organize step).

---

## Local reproducibility (no retrain required for viva)

### Dataset paths (prefer archive; do not duplicate)

```text
ASSISTments raw CSV:
  local-colab-archive/AdaptiveLearnSE/c4_data/raw/skill_builder_data_corrected.csv

SE supervised synthetic (full run):
  local-colab-archive/AdaptiveLearnSE/c4_runs/se_supervised_sim_v0/train_full_se-supervised-sim-v0_20261012T130156.573Z/synthetic_data/
```

Optional future training can point env/config at these paths; **do not** bulk-copy
into `datasets/` unless a loader requires it.

### Training runtime records (from bundles; do not replace local pins)

| Family | Record |
|---|---|
| SE supervised | `runtime-artifacts/.../export_bundle/runtime_versions.json` (Colab: sklearn 1.6.1, numpy 2.1.3, joblib 1.6.0, Python 3.13.16 Linux) |
| SE path sim | `docs/SE_SIMULATION_ENVIRONMENT.md` + bundle train metadata |
| ASSISTments | research bundle / `MODEL_CARD.md` |

### Colab notebooks are **not** drop-in local runners

Executed notebooks contain Colab-only pieces that need adaptation before local run:

- `google.colab.drive.mount` / `files.upload`
- `/content/...` extract and Drive paths (`MyDrive/AdaptiveLearnSE/c4_runs/...`)
- Upload widgets for source ZIPs

Moving files into `local-colab-archive/` does **not** make those cells runnable
locally without edits. Use unexecuted templates under `experiments/` + README
Colab guides if re-running later.

### Inference (existing, verified)

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 127.0.0.1 --port 8004
# /v1/research/*  /v1/se-simulation/*  /v1/se-supervised-simulation/*
```

### Optional future training (not required for viva)

```powershell
# SE supervised Colab package
python scripts\package_se_supervised_colab_zip.py
# SE path sim Colab package
python scripts\package_se_colab_zip.py
# Re-import only if a new export is produced (do not replace without checksum compare)
python scripts\import_se_supervised_bundle.py ...
python scripts\import_se_simulation_bundle.py ...
```

---

## Non-claims

- Synthetic SE metrics measure agreement with the generator / simulator only.
- Classification accuracies at threshold 0.5 are secondary to declared primary
  metrics (log_loss / MAE) unless explicitly presented as thresholded accuracy.
- No Atlas / production wiring is implied by this evidence pack.
