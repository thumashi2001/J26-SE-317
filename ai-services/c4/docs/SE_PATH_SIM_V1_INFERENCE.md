# SE path simulation v1 inference (isolated)

Protocol: **`se-path-sim-v1`** (S1 / 46 topics). Does **not** replace
`/v1/se-simulation/*` (v0). Not wired to Node student Adaptive path.

## Bundle

```text
runtime-artifacts/se_path_sim_v1/train_full_se-path-sim-v1_20261013T181643.681Z/export_bundle/
```

Catalogue SHA-256:
`95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622`  
Observation dim **96**; actions **46**.

## Demo checkpoint (validation only)

See [`SE_DEMO_CHECKPOINT_SELECTION_V1.md`](SE_DEMO_CHECKPOINT_SELECTION_V1.md).

- **Seed 2** — mean validation return across Y3S1+Y3S2 = `11.273999686539169`
- Model SHA-256: `53d2c5d60698b7debe96ed42db1b6e22089ef96875c75e63a205550dd6c3c029`
- Final-test metrics were **not** used for selection.

Optional override: `$env:C4_SE_PATH_V1_DEMO_SEED`, `$env:C4_SE_PATH_V1_BUNDLE_DIR`.

## Mask rule

1. Request must include `semester` (`Y3S1` or `Y3S2`).
2. Valid actions ⊆ semester-eligible ∩ available ∩ (mastery &lt; 0.8),
   with reopen-all-available-in-semester if all eligible available topics are mastered.
3. Off-semester or unavailable `True` mask bits → **400**.
4. All-invalid mask → **400**.
5. Missing artifacts → **503** (no silent v0 fallback).

## Startup

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

## Endpoints

| Method | Path |
|---|---|
| GET | `/v1/se-path-simulation-v1/ready` |
| GET | `/v1/se-path-simulation-v1/catalogue` |
| POST | `/v1/se-path-simulation-v1/predict` |

## Sample predict

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
python -c @"
import json, numpy as np, urllib.request
from catalogues.c1_practice_full_2026_10 import catalogue_hash, semester_eligibility_mask, N_TOPICS
from training_se_v1.observation import build_observation

semester = 'Y3S1'
mastery = np.full(N_TOPICS, 0.35, dtype=np.float32)
avail = np.asarray(semester_eligibility_mask(semester), dtype=np.float32)
mastery = np.where(avail > 0.5, mastery, 0.0).astype(np.float32)
obs = build_observation(mastery, avail, elapsed_env_steps=2, max_episode_steps=40,
                        prior_strength=0.4, mastery_threshold=0.8)
mask = ((avail > 0.5) & (mastery < 0.8)).astype(bool).tolist()
body = {
  'observation': obs.tolist(),
  'action_mask': mask,
  'semester': semester,
  'protocol': 'se-path-sim-v1',
  'catalogue_hash': catalogue_hash(),
  'deterministic': True,
}
req = urllib.request.Request('http://127.0.0.1:8004/v1/se-path-simulation-v1/predict',
    data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
print(urllib.request.urlopen(req).read().decode())
"@
```

## Authenticated Node proxy (demo UI)

Browser never supplies the Python base URL. Node uses `C4_AI_URL`
(default `http://127.0.0.1:8004`) and mounts authenticated routes under
`/api/v1/c4/simulation/v1/*` (see `backend/src/modules/c4/routes/index.js`).
Synthetic scenarios: `GET /api/v1/c4/simulation/v1/scenarios`.

Live C1 feature mapping: [`LIVE_INPUT_COMPATIBILITY_V1.md`](LIVE_INPUT_COMPATIBILITY_V1.md).

## Limitations

- Simulation-only (`domain=se_simulation`, `synthetic=true`, `simulation_only=true`).
- Not real-student validated; not exam readiness.
- Not wired into the operational heuristic student Adaptive path.
- Does not consume supervised response / exam / pass outputs.
