# Component 4: Adaptive Learning (AI services)

Python service for C4 research and simulation inference, aligned with other
`ai-services/c*` components (`app/`, `services/`, `experiments/`, `tests/`).

## Layout

| Path | Role |
|---|---|
| `app/` | FastAPI inference (`/v1/research/*`, `/v1/se-simulation/*`, `/v1/se-supervised-simulation/*`) |
| `services/inference/` | Loaders (active paths → `runtime-artifacts/`) |
| `services/models/` | **Presentation copies** of full-run weights + metadata |
| `datasets/` | Local ASSISTments raw/processed placeholders |
| `experiments/notebooks/` | Executed Colab notebooks (saved outputs) |
| `experiments/results/` | Saved validation/final metrics (JSON/CSV) |
| `experiments/*.ipynb` | Unexecuted Colab templates |
| `tests/` | Inference and training smoke tests |
| `training/`, `training_se/`, `training_se_supervised/` | Training code (required for joblib classes and notebooks) |
| `scripts/` | Import, packaging, organization helpers |
| `docs/` | Protocols, model cards, evidence index |
| `runtime-artifacts/` | **Active** imported bundles for serving (gitignored binaries) |
| `local-colab-archive/` | Full Colab Drive backup mirror (gitignored bulk) |

## Run inference

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

## Evidence for viva

- [`docs/VIVA_EVIDENCE_INDEX.md`](docs/VIVA_EVIDENCE_INDEX.md)
- [`experiments/notebooks/README.md`](experiments/notebooks/README.md)
- [`experiments/results/README.md`](experiments/results/README.md)

## Requirements

- [`requirements.txt`](requirements.txt) — inference
- [`requirements-training.txt`](requirements-training.txt) — Colab / training stack

No Atlas connection from this component.
