# Component 4 — Adaptive learning paths (SE heuristic)

Node module auto-mounted at **`/api/v1/c4`** when `routes/index.js` is present.

## Strategy

`weakest_stored_mastery_v1` — deterministic ranking of **actual C1 practice topics**
by lowest available mastery (0–100). **Not** ASSISTments MaskablePPO.

See `services/sequencer.js` and `ai-services/c4/docs/SE_INTEGRATION_PLAN.md`.

## Collections (C4-owned)

- `c4_learning_paths`
- `c4_learning_path_revisions`

Never writes C1 `mastery_state` / `mastery_history` / `learning_events`.

## Student workflow (C4-owned)

| Area | Routes |
|---|---|
| Paths + daily schedule | `/paths*` including `refresh`, `revisions` |
| Mock quizzes (practice-bank) | `/exams*` |
| Feedback | `/feedback` |
| Synthetic model demo | `/simulation/v1/*` |

Collections: `c4_learning_paths`, `c4_learning_path_revisions`, `c4_exam_attempts`, `c4_feedback`.

Operational ranking: **`weakest_stored_mastery_v1`**. SE v1 models are simulation-demo / experimental-estimate only.

## Synthetic simulation demo (v1)

Authenticated proxy to Python on **`C4_AI_URL`** (default `http://127.0.0.1:8004`):

| Method | Path |
|---|---|
| GET | `/api/v1/c4/simulation/v1/ready` |
| GET | `/api/v1/c4/simulation/v1/scenarios` |
| GET/POST | `/api/v1/c4/simulation/v1/path/*` |
| GET/POST | `/api/v1/c4/simulation/v1/supervised/*` |

UI tab **Model simulation demo** on `/c4/*`. Demo inputs are synthetic only —
no student DB writes. Operational path remains `weakest_stored_mastery_v1`.

## Tests (isolated; no Atlas)

```powershell
cd backend
node --test src/modules/c4/tests/*.test.js
```
