# SE supervised simulation inference (`se-supervised-sim-v0`)

Isolated FastAPI demo for imported synthetic supervised models. Does **not**
retrain, does **not** alter historical metrics, and does **not** wire into
MaskablePPO / ASSISTments.

## Import

```powershell
cd ai-services\c4
python scripts\import_se_supervised_bundle.py runtime-artifacts\c4_se_supervised_bundle_20261012T131046728530Z.zip
```

Destination:

`runtime-artifacts/se_supervised_sim_v0/c4_se_supervised_bundle_20261012T131046728530Z/`

Verifies **61** SHA-256 entries in `export_bundle/manifest.json`. Rejects ZIP
slip and checksum failures. Does not overwrite ASSISTments or `se_path_sim_v0`.
`export_bundle/source/` is reference-only for joblib class provenance; live
`training_se_supervised/` is not auto-overwritten.

## Selected models (from SELECTION_FROZEN.json)

| Artifact | Selected name |
|---|---|
| `response_selected.joblib` | `hist_gradient_boosting_classifier` |
| `exam_score_selected.joblib` | `ridge_regression` |
| `pass_selected.joblib` | `logistic_regression` |

Pass threshold: **0.55** (synthetic mock-exam fraction-correct; not institutional).

## Endpoints

| Method | Path |
|---|---|
| GET | `/v1/se-supervised-simulation/ready` |
| POST | `/v1/se-supervised-simulation/response` |
| POST | `/v1/se-supervised-simulation/exam-score` |
| POST | `/v1/se-supervised-simulation/pass` |

Body: `{ "features": { ... }, "protocol": "se-supervised-sim-v0" }`  
Missing feature keys → 400 (no imputation). Ridge returns `exam_score_raw` plus
optional `exam_score_clipped_display` with `clipping_applied`.

## Startup

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 127.0.0.1 --port 8004
```
