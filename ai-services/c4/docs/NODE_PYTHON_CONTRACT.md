# Proposed Node ↔ Python contract (C4 research inference)

Status: **proposal for ASSISTments research demos**. Not wired into Express yet.
Coordinate `App.jsx`, `menus.js`, and shared backend config before any future edits.

## Ownership

| Concern | Owner |
|---|---|
| Login, JWT, roles (`docs/auth-roles.md`) | Node (`backend`) |
| Student identity resolution | Node (`resolveStudentId`) |
| MongoDB / Atlas access | Node only |
| MaskablePPO load + predict | Python (`ai-services/c4`, port **8004**) |
| Building SE observations / topic maps | **Not available** — see `SE_INTEGRATION_GAPS.md` |

Python must **not** connect to Atlas or validate JWTs for product traffic.
For local research demos, Node (or a script) may call Python on localhost after
authenticating the user on the Node side.

## Environment

```text
C4_AI_URL=http://127.0.0.1:8004
C4_BUNDLE_DIR=<optional override of runtime-artifacts/...bundle...>
C4_DEMO_SEED=2
```

## Endpoints (Python)

### `GET /health`

Liveness only (process up). Does not require model files.

```json
{ "status": "ok", "service": "c4-ai-research", "domain": "assistments_research" }
```

### `GET /ready`

Readiness: model + catalogue loaded. **503** if checkpoint/deps missing
(no fake ready state).

```json
{
  "ready": true,
  "algorithm": "maskable_ppo",
  "seed": 2,
  "protocol": "c4-env-eval-v1.1",
  "model_hash": "7613e1e28375ca4a844fc064b130b8d8d38d38cf085adf1e52ab73322bd09fca",
  "n_skills": 20,
  "obs_dim": 24,
  "skill_ids": ["311", "47", "..."],
  "domain": "assistments_research",
  "error": null
}
```

### `GET /v1/research/catalogue`

Exact ordered skill IDs and observation layout.

### `POST /v1/research/predict`

**Request**

```json
{
  "observation": [0.2, 0.3, "... 24 floats in [0,1] ..."],
  "action_mask": [true, true, "... 20 bools, ≥1 true ..."],
  "skill_ids": ["311", "47", "... optional exact catalogue check ..."],
  "protocol": "c4-env-eval-v1.1",
  "deterministic": true,
  "include_uncalibrated_probability": false
}
```

**Response 200**

```json
{
  "action_index": 3,
  "skill_id": "280",
  "algorithm": "maskable_ppo",
  "seed": 2,
  "protocol": "c4-env-eval-v1.1",
  "model_hash": "7613e1e28375ca4a844fc064b130b8d8d38d38cf085adf1e52ab73322bd09fca",
  "domain": "assistments_research",
  "note": "ASSISTments skill IDs only. Not calibrated confidence. Not SLIIT SE product behaviour."
}
```

Optional field when requested: `uncalibrated_action_probability` (raw policy mass —
**not** labelled confidence).

**Errors**

| Status | When |
|---|---|
| 400 | Bad shape, non-finite/out-of-bounds obs, catalogue mismatch, all-invalid mask, wrong protocol |
| 503 | Model not loaded / dependency missing |

## Suggested future Node proxy (not implemented)

```text
POST /api/v1/c4/research/predict
  requireRole / resolveStudentId on Node
  forward body to ${C4_AI_URL}/v1/research/predict
  never pass Mongo documents straight through without an explicit mapper
```

## Launch (local)

Verified pins / Python version: `docs/INFERENCE_ENVIRONMENT.md` and
`constraints-runtime.txt` (only the machine where the 11 inference tests passed
is verified until others re-run them).

```powershell
cd ai-services/c4
python -m pip install -c constraints-runtime.txt -r requirements.txt
# optional tests: also -r requirements-dev.txt
python scripts/import_research_bundle.py "C:\path\to\c4_maskable_ppo_research_bundle_....zip"
# if already extracted:
python scripts/import_research_bundle.py --verify-only runtime-artifacts\c4_maskable_ppo_research_bundle_20261012T062204868154Z
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

Smoke:

```powershell
curl http://127.0.0.1:8004/health
curl http://127.0.0.1:8004/ready
```
