# SE / C1 integration gaps (read-only inspection)

**Full contract proposal:** see `SE_INTEGRATION_PLAN.md` (topics, path APIs, C1
ownership, menus, exam-readiness evidence, now vs later).

C4 research inference uses **ASSISTments 2009–10 skill IDs** in a fixed order.
AdaptiveLearnSE / C1 uses **SLIIT Software Engineering topics** and mastery scores
from MongoDB (Atlas via Node). These are different domains. This document lists
what is missing before any product integration. No silent ID remapping is allowed.

## Inspected C1 surfaces (read-only)

| Surface | Role | Relevance to C4 |
|---|---|---|
| `GET /api/v1/c1/insights/:studentId` (Node → optional C1 AI) | Per-topic `estimatedNow`, confidence, `daysSincePractice`, engagement | Candidate **inputs** after domain adaptation — not drop-in observations |
| C1 practice bank / `practiceService.js` | SE topic practice questions | Not an ASSISTments activity catalogue |
| `ai-services/c1` FastAPI (`/diagnostic/score`, `/twin/*`, `/risk/predict`) | Mastery / forgetting / risk helpers on SE scores (0–100) | Different state semantics than C4 obs `[0,1]` mastery vector |
| `docs/auth-roles.md` | Shared JWT roles; menus in `App.jsx` / `menus.js` | Node owns auth; C4 Python must not issue tokens or talk to Atlas |

## Missing for integration

1. **Topic ↔ skill mapping**  
   No validated map from C1 SE topic names to the ordered ASSISTments catalogue
   (`311, 47, …, 16`). Renaming math IDs as SE topics is **forbidden** as “validation”.

2. **Mastery scale / observation builder**  
   C1 `estimatedNow` is typically 0–100; C4 expects a length-24 vector in `[0,1]`
   (`n_skills+4` under protocol `c4-env-eval-v1.1`). Need an explicit builder,
   including `mean_mastery`, `frac_mastered`, `elapsed_env_step_frac`, `prior_strength`.

3. **Action / activity catalogue**  
   C4 actions = practise one of 20 ASSISTments skills (plus optional simulation-only
   labels in training only). SE needs a product activity catalogue (questions,
   labs, revision) with availability masks — not present for C4 today.

4. **Valid-action mask source**  
   Research masks follow mastery-threshold logic in the simulator. Product masks
   must come from real availability (already mastered, no content, cooldowns, etc.).

5. **Readiness / evaluation evidence on SE data**  
   Bundle metrics are ASSISTments-simulator only. No SE-student offline eval,
   no A/B or supervised pilot, no calibration of policy probabilities.

6. **Shared UI / config coordination**  
   Student heuristic path: `frontend/src/pages/c4/PathPage.jsx` is mounted at
   `/c4/*` in `App.jsx` (menu entry in `menus.js` already existed). Lecturer
   `/lecturer/c4/*` remains ComingSoon. Do not add a duplicate menu item.

7. **Auth boundary**  
   Node remains responsible for JWT + `resolveStudentId` / `requireRole`. Python
   research service has no Atlas connection and must stay that way.

8. **Frozen SE simulation catalogue vs current C1 practice IDs (2026-10-13 audit)**  
   Audited without renaming models, remapping actions, or retraining.

   | Source | Count | Role |
   |---|---|---|
   | Current C1 `PRACTICE_QUESTIONS` keys | **46** | Authoritative for student heuristic path (`supportedTopics.js` / PathPage) |
   | Frozen `training_se.catalogue.ORDERED_TOPICS` + saved `topic_catalogue.json` (`catalogue_hash` `5001dd00…`) | **12** | Action / obs layout for `se-path-sim-v0` MaskablePPO |
   | Supervised bundle `feature_schema_*` topic one-hots / attempt features | **same 12 IDs** | `se-supervised-sim-v0` feature columns |

   **Exact overlap:** **0** of the 12 frozen IDs appear in current C1 practice keys.

   Frozen IDs (simulation / supervised only):
   `usability_heuristics`, `user_research_methods`, `prototyping`, `normalization`,
   `indexing`, `query_optimization`, `case_analysis_techniques`,
   `industry_case_studies`, `lessons_learned`, `risk_management`, `estimation`,
   `agile_planning`.

   Current C1 examples in the same modules (not a mapping — labels only for humans):
   SE3050 → `ux_testing_heuristics`, `user_research_synthesis`, `structuring_prototyping`, …
   SE3060 → `file_organization_indexing`, `object_relational_db`, `query_processing_tuning`, …
   SE3080 → `project_risk_management`, `schedule_cost_management`, …
   Plus entire AF / DSYS / SA / QM banks absent from the frozen 12.

   **Implication:** SE RL and supervised inference **must stay off the student Adaptive
   path** until a new catalogue/protocol is trained or an explicit, reviewed
   compatibility contract exists. Heuristic `weakest_stored_mastery_v1` continues
   to use live C1 IDs only. Do **not** silently map old actions to new topics.

## Explicit non-claims

- Software fixtures under `datasets/fixtures/` demonstrate code functionality only.
- Successful local MaskablePPO inference does **not** mean the full C4 component
  or SE adaptive learning product is finished.
- Conceptual module-level similarity between old and new topic names is **not**
  validation of action remapping.
