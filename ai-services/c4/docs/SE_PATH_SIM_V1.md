# SE path simulation v1 (`se-path-sim-v1`)

Additive MaskablePPO path trainer for AdaptiveLearnSE. Does **not** modify
`training_se` (`se-path-sim-v0`), ASSISTments artifacts, or student UI wiring.

## Scope (S1)

- Catalogue: `c1-practice-full-2026.10` — **46** C1 practice topic IDs
- Semester eligibility masks: Y3S1 (28) / Y3S2 (18)
- Implementation scope choice — **not** proposal-PDF verification
- No mapping of retired v0 topic IDs onto live IDs

## Observation

- Dimension: **96** = `2 * 46 + 4`
- Layout: mastery[46] ‖ available[46] ‖ mean_mastery, frac_mastered,
  elapsed_env_step_frac, prior_strength
- Missing mastery: `available=0`, mastery forced to 0
- Genuine zero: `available=1`, mastery=0

## Training

- Package: `ai-services/c4/training_se_v1/`
- Notebook: `experiments/07_se_path_simulation_v1.ipynb`
- Colab ZIP: `c4-se-v1-source-colab.zip`
- Drive root: `…/AdaptiveLearnSE/c4_runs/se_path_sim_v1`
- Gates: `RUN_FULL_TRAINING=False`, `RUN_FINAL_EVALUATION=False` by default
- Validation scenarios include both semesters; reported separately
- Baselines: `weakest_stored_mastery_v1_sim`, `random_valid`, `recent_performance`
- Metrics: episode return / mastery / progress — **not** classification accuracy
- Empty action mask → invalid step + terminate (`no_eligible_actions`)

## Labels

All generated runs are **simulation-only**. Student Adaptive path remains the
heuristic Node flow; this protocol does not wire models into the product UI.
