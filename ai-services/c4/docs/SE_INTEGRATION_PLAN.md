# C4 SE integration plan (contract proposal)

Status: **Heuristic SE path flow implemented** under `backend/src/modules/c4/` and
`frontend/src/pages/c4/` (see `SE_HEURISTIC_FLOW.md`). Student `/c4/*` mounts
`PathPage` inside the shared authenticated student layout; `menus.js` already
had “Adaptive path” (no duplicate menu). Lecturer `/lecturer/c4/*` remains
ComingSoon. SE RL / supervised simulation stay **unwired** to the student UI —
frozen 12-topic catalogues do not match current C1 practice IDs (see
`SE_INTEGRATION_GAPS.md` §8). ASSISTments research MaskablePPO stays **separate**.

Related: `SE_INTEGRATION_GAPS.md`, `NODE_PYTHON_CONTRACT.md`, `SE_MODEL_TRAINING_SPEC.md`,
`docs/auth-roles.md` (shared auth; Node-owned).

---

## 1. Actual SE topic IDs and mastery / history fields

### Topic IDs (practice catalogue today)

**Authoritative:** `backend/src/modules/c1/data/practiceQuestions.js`
(`PRACTICE_QUESTIONS` keys) — **46** IDs after Development content refresh
(e.g. `ux_testing_heuristics`, `file_organization_indexing`,
`project_risk_management`, plus AF/DSYS/SA/QM banks). Heuristic C4 sequencing
reads these via `supportedTopics.js`.

**Frozen simulation catalogue (do not treat as live C1):** the 12 IDs in
`training_se/catalogue.py` / saved `topic_catalogue.json` (`indexing`,
`usability_heuristics`, …) are historical practice-only labels used by
`se-path-sim-v0` / `se-supervised-sim-v0`. **Zero ID overlap** with current C1
keys as of 2026-10-13 — see `SE_INTEGRATION_GAPS.md` §8.

Diagnostic topics come from `question_bank` filtered by the student’s `semester`.
Twin mastery keys are whatever topics appear in the diagnostic AI score response.

### Mastery / twin fields (C1-owned)

| Collection / API | Fields usable by a future C4 planner |
|---|---|
| `mastery_state` via `GET /api/v1/c1/twin/:studentId` | `diagnosticCompleted`, `semester`, per-topic `score` (0–100), `answered`, `correct`, `last_practiced`, `practice_sessions`; `riskLevel` |
| `GET /api/v1/c1/insights/:studentId` | Per topic: `storedScore`, `estimatedNow` (null if C1 AI down), `daysSincePractice`, `lastPracticed`, `confidence`, `confidenceLabel`, engagement index |
| `GET /api/v1/c1/history/:studentId/:topic` | Versioned points: `score`, `scoreBefore`, `afterForgetting`, `source`; current answered/correct/sessions |
| `GET /api/v1/c1/behaviour/:studentId` | Answer-behaviour summary |
| `learning_events` (via C1 event path) | `topic`, `correct`, `hint_used`, `time_sec`, optional `question_id` / `session_id` |

**Not available as drop-in C4 research obs:** length-24 ASSISTments vector, math skill
masks, or calibrated policy confidence.

---

## 2. Activity catalogue and prerequisite / availability rules

### What exists now

- **Practice activities:** MCQ bank per topic (`practice_bank` / `PRACTICE_QUESTIONS`).
  APIs: `GET /practice/topics`, `POST /practice/start`, `POST /practice/answer`.
- Availability today: topic must exist on the twin; practice questions must exist;
  diagnostic must be completed for insights/history; open session cleanup in
  `practiceService`.
- **No** explicit prerequisite graph (e.g. indexing before query_optimization).
- **No** C4 activity types for labs, lecture revision, mock exams, or coding tasks
  beyond C1 practice quizzes.

### Required for SE adaptive paths

1. Ordered **SE activity catalogue** with stable IDs (topic practice session, future
   lab/revision/exam-prep types).
2. **Availability mask rules**: diagnostic done; content exists; optional mastery
   ceiling; cooldowns; semester/module scope; lecturer locks.
3. Optional **prerequisite** edges between topics/modules — product decision, not
   present in code today.

---

## 3. Learning-path create / retrieve / progress / replan

**Implemented (heuristic Node module, not a trained SE policy):**
`backend/src/modules/c4/routes/index.js` auto-mounts at `/api/v1/c4` with
`requireAuth` + `resolveStudentId`. Strategy: `weakest_stored_mastery_v1`.
Collections: `c4_learning_paths`, `c4_learning_path_revisions`.
See `SE_HEURISTIC_FLOW.md` and `backend/src/modules/c4/docs/API_EXAMPLES.md`.

| Operation | Route | Persistence / semantics |
|---|---|---|
| Create path | `POST /api/v1/c4/paths` | Idempotent active path; `clientRequestId` safe |
| List / active / detail | `GET /api/v1/c4/paths`, `/paths/active`, `/paths/:pathId` | C4-owned docs only |
| Progress | `POST /api/v1/c4/paths/:pathId/progress` | **Self-reported** completion; does **not** write C1 mastery/events |
| Replan | `POST /api/v1/c4/paths/:pathId/replan` | Versions revision; preserves completed activities |

Assessed performance still goes through C1 practice (`POST /api/v1/c1/practice/answer`).
Frontend pages exist under `frontend/src/pages/c4/` but **App.jsx is not mounted**
until coordinated (`APP_JSX_ROUTE_PATCH.md`).

---

## 4. Learner-state changes that must go through C1-owned APIs

C4 must **not** update `mastery_state`, `mastery_history`, `learning_events`, or
`practice_sessions` itself. Use:

| Change | C1 API |
|---|---|
| Diagnostic bootstrap | `GET/POST /api/v1/c1/diagnostic*` |
| Practice attempt | `POST /api/v1/c1/practice/start`, `POST /api/v1/c1/practice/answer` |
| Generic quiz/event mastery update | `POST /api/v1/c1/events` |
| Read current estimates | `GET /api/v1/c1/insights/:studentId`, `GET /api/v1/c1/twin/:studentId` |
| Topic trajectory | `GET /api/v1/c1/history/:studentId/:topic` |
| What-if score trajectory | `GET /api/v1/c1/forecast/:studentId/:topic` (C1 AI) |

C1 Python (`C1_AI_URL`, default `:8001`) owns score/forgetting/risk maths.
C4 Python must not connect to Atlas.

---

## 5. Node ↔ Python contracts and failure behaviour

Keep **two** Python surfaces:

| Service | Port (proposed) | Role |
|---|---|---|
| C1 AI (existing) | 8001 | Twin score, decay, risk, forecast |
| C4 research AI (existing) | 8004 | ASSISTments MaskablePPO demo only |
| C4 SE planner AI (future) | e.g. 8005 | SE-topic policy / heuristics — **new** model & contract |

### Failure behaviour (Node)

| Condition | Behaviour |
|---|---|
| C4 AI unreachable / `/ready` 503 | Return **502/503** with clear error; show last saved path or heuristic fallback; **never** invent masked RL actions |
| C1 insights `estimatedNow` null | Planner may use `storedScore` with lower confidence; do not pretend AI decay ran |
| Incompatible catalogue / bad obs | **400**; do not coerce SE topics into ASSISTments slots |
| Auth failure | Node rejects before proxy (`requireAuth` / role) |

Research predict contract remains as in `NODE_PYTHON_CONTRACT.md`
(`/health`, `/ready`, `/v1/research/catalogue`, `/v1/research/predict`).
Future SE planner should use a **different path prefix** (e.g. `/v1/se/plan`) so
clients cannot confuse domains.

---

## 6. Student / lecturer pages and proposed menu entries

Menus already reserve placeholders (do not edit shared files until coordinated):

| Role | Existing menu | Existing route stub |
|---|---|---|
| Student | `Study plan` → `/c4` “Adaptive path” | `ComingSoon` Adaptive Learning Path |
| Lecturer | `/lecturer/c4` “Adaptive paths” | `ComingSoon` study plans |

### Proposed pages (future shared edits)

**Student**

- `/c4` — current path overview (next activities, progress).
- `/c4/path/:pathId` — step detail + deep-link to `/c1/practice/:topic`.
- Optional `/c4/research-demo` — clearly labelled ASSISTments research demo (not SE).

**Lecturer**

- `/lecturer/c4` — class list of active paths / replans.
- `/lecturer/c4/student/:studentId` — inspect recommended sequence (read-only mastery via C1).

Menu labels can stay “Adaptive path(s)” until product naming is fixed. Coordinate
`App.jsx` + `menus.js` in one change set with backend routes.

---

## 7. Missing evidence for exam-readiness predictions

Cannot claim exam readiness from the ASSISTments bundle. Still needed:

1. SE-labelled outcomes (mock/exam scores or lecturer readiness ratings) linked to
   topic mastery trajectories.
2. Offline eval protocol on held-out SE students (not `sim_test` presets).
3. Calibration study if any probability/readiness score is shown to users.
4. Agreement with C1 risk/forecast semantics (avoid duplicate competing “readiness”).
5. Content coverage proof: enough activities per topic for a meaningful path.
6. Ethics/consent for any live pilot.

Until then, UI copy must describe **study sequencing suggestions**, not certified
exam-pass predictions.

---

## 8. What can be implemented now vs needs a new SE training contract

### Can implement now (orchestration / product shell; no fake SE↔math mapping)

- C4 Node module skeleton: path CRUD, progress, replan **hooks**, proxy patterns.
- UI pages that read C1 insights/twin and list heuristic sequences (e.g. weakest
  `estimatedNow` / `storedScore` among topics with practice content).
- Availability checks using C1 `practice/topics` + twin keys.
- Keep `/v1/research/*` MaskablePPO demo isolated and labelled research-only.
- Service failure handling and readiness gates as above.
- Documentation and contracts in `ai-services/c4/docs/` (this file).

### Requires a new SE-specific training / data contract (not the ASSISTments checkpoint)

- Fixed ordered **SE topic/activity** action space and observation schema.
- Dataset of SE learner trajectories (or high-fidelity SE simulator with
  parameters fit or validated on SE data).
- Train/val/test by **SE student**, with selection on validation only.
- Maskable (or other) policy trained for that catalogue — new model hash & card.
- Mapping rules only if explicitly designed (many-to-one activities, module goals);
  **never** by relabelling ASSISTments IDs `311…16` as SE topics.
- Exam-readiness model or supervised head with the evidence in §7.

### Explicit non-goals for the current research predictor

- Do not feed C1 topic vectors into the ASSISTments MaskablePPO.
- Do not return ASSISTments `skill_id` values as AdaptiveLearnSE practice topics.
- Do not treat Table B simulator-test metrics as SE product validation.
