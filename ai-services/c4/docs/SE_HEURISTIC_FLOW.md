# SE heuristic learning-path flow (implemented)

## Boundary

| Surface | Role |
|---|---|
| Node `/api/v1/c4/paths*` | SE rule-based path CRUD / progress / replan |
| Python `/v1/research/*` (port 8004) | ASSISTments MaskablePPO research only |
| C1 practice `/c1/practice/:topic` | Assessed attempts & mastery writes |

No relabelling of ASSISTments skill IDs to SE topics.

## Strategy

`weakest_stored_mastery_v1` / `1.0.0` — see `backend/src/modules/c4/services/sequencer.js`.

## Outstanding (not this delivery)

- SE-specific RL training / validation — see `SE_MODEL_TRAINING_SPEC.md`
- Exam-readiness predictions (blocked without labels) — see same spec
- Shared `App.jsx` mount (pages exist, not mounted — see `backend/src/modules/c4/docs/APP_JSX_ROUTE_PATCH.md`)
- Lecturer adaptive-path UI
