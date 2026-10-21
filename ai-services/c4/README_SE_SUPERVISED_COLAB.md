# SE supervised simulation Colab (`se-supervised-sim-v0`)

Explicitly **synthetic** prototypes for:

| Target | Type | Candidates |
|---|---|---|
| A. Next-attempt correctness | Classification | constant train prevalence, logistic regression, HistGradientBoostingClassifier |
| B. Mock-exam score | Regression | train-mean, ridge, HistGradientBoostingRegressor |
| B-optional. Pass (`score ≥ 0.55`) | Classification | same as A, **only if** train has ≥8 positives and ≥8 negatives |

Pass threshold **0.55** (fraction correct) is declared in `training_se_supervised/contract.py` **before** fitting.

Marks on all outputs: `domain=se_simulation`, `synthetic=true`, `simulation_only=true`, `real_exam_validation=false`.

Does **not** need ASSISTments CSV. Does **not** retrain MaskablePPO. Does **not** auto-wire into `se-path-sim-v0`.

## Data decision

If authorized SE attempt/exam exports appear under `datasets/raw` or `datasets/authorized_se`, `inventory_local_se_exports()` will list them. Otherwise the pipeline uses the frozen synthetic generator only (no silent ASSISTments relabeling, no unrelated downloads).

## First Colab steps

1. Build the source ZIP locally:

```powershell
cd ai-services\c4
python experiments\_generate_se_supervised_notebook.py
python scripts\package_se_supervised_colab_zip.py
```

2. Open `experiments/06_se_supervised_simulation.ipynb` in Colab.
3. Run cell 1 (deps) → cell 2 upload **`c4-se-supervised-source-colab.zip`** → cell 3 mount Drive.
4. Drive artifacts root: `MyDrive/AdaptiveLearnSE/c4_runs/se_supervised_sim_v0/`
5. Run smoke cells (contract → generate → leakage → validation selection).
6. Leave `RUN_FULL_TRAINING = False` and `RUN_FINAL_EVALUATION = False` until you intentionally run them.
7. Full training and final-test each create/use **timestamped** run folders and refuse overwrite. Final-test **loads** `frozen_contract.json` + `SELECTION_FROZEN.json` (no default fallback).

## Local software smoke (not full training)

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
pytest tests\test_se_supervised_sim.py -q
```

Local smoke ≠ Colab full training. Do not treat smoke metrics as the final study.

## Remaining training runs (on Colab)

1. Smoke (optional redo on Colab GPU/CPU for Drive artifacts).
2. Full generation + training (`RUN_FULL_TRAINING=True`) — all three scenarios generated; selection on `baseline` validation.
3. Final-test once (`RUN_FINAL_EVALUATION=True`) after selection freeze — one-shot, no retuning.
4. Download `export_bundle/` (models, cards, manifest checksums).

## Leakage protections (enforced in code + tests)

- Learner-disjoint train/val/test (same learner’s practice + exam stay together).
- Response features use only history **before** the target attempt.
- Exam features use only practice at/before prediction cutoff; exam starts after.
- Latents (`latent_ability`, `true_p_correct`, …) live under `audit/` only.
- Identifiers are never predictive features.
- Scalers / models fitted on **train** only; validation for selection; test gated.

## Out of scope

Exam assembly, UI, production wiring, and connecting this response model into the completed SE RL simulator (would need a new versioned experiment).
