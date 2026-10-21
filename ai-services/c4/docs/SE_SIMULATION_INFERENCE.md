# SE simulation inference (isolated)

## Mask rule (preserved from training)

1. Prefer **available** topics with mastery **&lt; 0.8**.
2. If every **available** topic is already ≥ 0.8, **reopen** all available topics.
3. **Unavailable** topics are never allowed.
4. An **all-invalid** mask (no True) is rejected at the API (503/400) — no silent remap.

Clients should build masks with this rule (or pass an equivalent valid mask).
The server refuses predictions that select unavailable or masked-off actions.

## Import (PowerShell)

```powershell
cd ai-services\c4
python scripts\import_se_simulation_bundle.py `
  runtime-artifacts\c4_se_simulation_bundle_20261012T084659312700Z.zip

# re-verify:
python scripts\import_se_simulation_bundle.py --verify-only `
  runtime-artifacts\se_path_sim_v0\c4_se_simulation_bundle_20261012T084659312700Z
```

Extract path:
`runtime-artifacts/se_path_sim_v0/c4_se_simulation_bundle_20261012T084659312700Z/`  
(does **not** overwrite the ASSISTments research bundle).

## Startup

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
# optional: $env:C4_SE_BUNDLE_DIR = "...\se_path_sim_v0\c4_se_simulation_bundle_..."
# optional: $env:C4_SE_DEMO_SEED = "0"
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

Verified locally where the real seed-0 checkpoint loads: see
`docs/SE_SIMULATION_ENVIRONMENT.md`.

## Sample request (shared observation builder)

```powershell
# After uvicorn is up, in another shell:
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
python -c @"
import json, numpy as np, urllib.request
from training_se.observation import build_observation
from training_se.catalogue import N_TOPICS, catalogue_hash

mastery = np.full(N_TOPICS, 0.35, dtype=np.float32)
avail = np.ones(N_TOPICS, dtype=np.float32)
obs = build_observation(mastery, avail, elapsed_env_steps=2, max_episode_steps=30,
                        prior_strength=0.4, mastery_threshold=0.8)
# mask: available and below threshold
mask = ((avail > 0.5) & (mastery < 0.8)).astype(bool).tolist()
body = {
  'observation': obs.tolist(),
  'action_mask': mask,
  'protocol': 'se-path-sim-v0',
  'catalogue_hash': catalogue_hash(),
  'deterministic': True,
}
req = urllib.request.Request('http://127.0.0.1:8004/v1/se-simulation/predict',
    data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
print(urllib.request.urlopen(req).read().decode())
"@
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/se-simulation/ready` | 503 if SE artifacts missing (research still works) |
| GET | `/v1/se-simulation/catalogue` | Topics + schema + catalogue_hash |
| POST | `/v1/se-simulation/predict` | Deterministic MaskablePPO + action_masks |

ASSISTments: `/v1/research/*` and `/ready` unchanged in role.
