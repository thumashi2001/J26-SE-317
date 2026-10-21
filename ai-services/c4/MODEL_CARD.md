# Model card — C4 MaskablePPO (ASSISTments research)

Figures below are reconciled from the imported research bundle
`c4_maskable_ppo_research_bundle_20261012T062204868154Z`
(`evidence/selection_val.json`, `evidence/comparison_val.json`,
`evidence/final_simulator_test/test_summary.csv`, `evidence/train_config.json`,
`artifacts/*`). Do **not** invent metrics. Software fixtures elsewhere demonstrate
code paths only; they are **not** SE model validity evidence.

## Model details

| Field | Value |
|---|---|
| Component | C4 — Reinforcement Learning-Based Adaptive Learning (research) |
| Algorithm selected (by validation) | `maskable_ppo` (sb3-contrib MaskablePPO; masks in train + eval) |
| Training mode | full |
| Seeds | 0, 1, 2 (three-seed reporting retained) |
| Requested training timestep budget | **100000** per seed (configured `train.timesteps` in `train_config.json`; the budget requested for learning, not a claim about every intermediate checkpoint) |
| Device | cpu |
| Env protocol | `c4-env-eval-v1.1` |
| Generator compat | `c4-sim-0.1.0` |
| Source run | `train_full_c4-env-eval-v1.1_20261012T051737.347320+0000` |
| Dependency versions (from train_config at training time) | gymnasium 1.3.0; numpy 2.1.3; pandas 2.2.3; sb3_contrib 2.9.0; sklearn 1.6.1; stable_baselines3 2.9.0; torch 2.11.0+cpu |
| Local inference env (verified where 11 tests passed) | See `docs/INFERENCE_ENVIRONMENT.md` and `constraints-runtime.txt` |

## Demo checkpoint (local inference)

Selection rule and hash: see `docs/DEMO_CHECKPOINT_SELECTION.md`.

| Field | Value |
|---|---|
| Selected seed | **2** (highest mean validation return; lowest-seed tie-break unused) |
| Checkpoint | `models/seed_2/maskable_ppo_final.zip` |
| Model SHA-256 | `7613e1e28375ca4a844fc064b130b8d8d38d38cf085adf1e52ab73322bd09fca` |

## Data

| Field | Value |
|---|---|
| Primary dataset | ASSISTments 2009–2010 corrected Skill Builder |
| Official page | https://sites.google.com/site/assistmentsdata/home/2009-2010-assistment-data/skill-builder-data-2009-2010 |
| Local filename (training capture) | `skill_builder_data_corrected.csv` |
| SHA-256 (raw CSV) | `162ef8d2d28bcbfea6591a282994062bd8d5eaa00636544292a0d268dca6e5da` |
| Domain | K-12 mathematics tutoring |
| SLIIT SE observations? | **No** |

Ordered skill catalogue (top-20 from train; inference must match exactly):

`311, 47, 277, 280, 312, 79, 49, 74, 279, 10, 27, 18, 2, 77, 50, 11, 67, 325, 310, 16`

## Intended use

- Research prototype for sequencing **ASSISTments skill practice** inside the C4 simulator.
- Offline comparison of MaskablePPO vs DQN, PPO, weakest-mastery, recent-performance, and random-valid.
- Local research inference service for demos with the selected MaskablePPO checkpoint.

## Out of scope / limitations

- Not validated for SLIIT Software Engineering students.
- Learning gains and forgetting dynamics are **assumed** (see `docs/FORGETTING_AND_LEARNING_ASSUMPTIONS.md`).
- **Selected-skill cumulative gain** (sum of per-step gains on the chosen skill) is distinct from **net total mastery change** (end − start across all skills, including forgetting). Positive return does **not** imply positive net total mastery.
- Inference requires valid-action masks and the original skill order.
- Do **not** rename math skill IDs to SE topics and claim validation.
- Response-model correctness ≠ causal knowledge gain.
- `order_id` within-learner ordering is a reproducible convention, not a verified wall-clock timeline.
- Action probabilities from the policy are **not** calibrated confidence.
- Simulator scenario labels (`sim_train` / `sim_val` / `sim_test`) are **initial-condition presets** (e.g. `prior_strength`), **not** held-out real SE learners and not a substitute for the ASSISTments learner train/val/test split.

## Training data splits

| Split | Rule |
|---|---|
| Train / val / test | By ASSISTments learner (see `artifacts/split_meta.json`) |
| Chronology | Preserved within learner |
| Preprocessing fit | Train only |
| Simulator scenarios | Initial-condition presets only (see limitations) |

## Evaluation (saved figures only)

Variability across the three training seeds uses **sample standard deviation** (ddof=1) of the **per-seed mean returns**, matching the convention used in `test_summary.csv`. Means are unchanged from the saved JSON/CSV. Historical result files under the bundle are preserved; nothing was retuned on final test.

### Table A — Validation (algorithm selection; not final test)

Source: `evidence/comparison_val.json` / `selection_val.json`.  
Cell format: **mean of per-seed mean returns ± sample SD (ddof=1)** across seeds `{0,1,2}`.

| Method | Validation return (mean ± sample SD) | Notes |
|---|---|---|
| **maskable_ppo** | **11.865 ± 0.154212** | Selected; invalid-action rate 0.0 |
| random_valid | 9.429 ± 0.252518 | Masked control |
| recent_performance | 7.945 ± 0.226321 | Masked baseline (implemented) |
| weakest_mastery | 7.488 ± 0.280000 | Masked baseline |
| dqn | 3.044 ± 6.651509 | Penalty-only; high seed variance |
| ppo | −36.839 ± 6.009251 | Penalty-only; high invalid rate |

Per-seed MaskablePPO validation mean return (preserved): seed0=11.940, seed1=11.688, seed2=11.968.

MaskablePPO validation (seed-mean aggregates from episode stats): **selected-skill cumulative gain** ≈ 2.43; path efficiency ≈ 0.049; time cost = 50 steps; invalid-action rate = 0.0. **Net total mastery change** is negative under default forgetting (see limitations).

### Table B — Final simulator test (reporting only — not used for selection)

Source: `evidence/final_simulator_test/test_summary.csv` (mean ± std as saved in that file).  
These episodes use the **test initial-condition scenario preset** in the ASSISTments-backed simulator. They are **not** evaluations on held-out real SE students.

| Method | Return | Selected-skill cumulative gain | Net total mastery Δ | Invalid-action rate |
|---|---|---|---|---|
| maskable_ppo | 13.125 ± 0.455 | 2.567 ± 0.049 | −2.183 ± 0.049 | 0.0 ± 0.0 |
| random_valid | 10.633 ± 0.429 | 2.300 ± 0.046 | −2.450 ± 0.046 | 0.0 ± 0.0 |
| recent_performance | 9.037 ± 0.154 | 2.129 ± 0.017 | −2.621 ± 0.017 | 0.0 ± 0.0 |
| weakest_mastery | 8.459 ± 0.529 | 2.067 ± 0.057 | −2.683 ± 0.057 | 0.0 ± 0.0 |
| dqn | −6.268 ± 5.919 | 1.712 ± 0.254 | −1.654 ± 0.195 | 0.291 ± 0.091 |
| ppo | −39.347 ± 5.440 | 0.428 ± 0.234 | −0.379 ± 0.162 | 0.830 ± 0.083 |

Did selected MaskablePPO outperform baselines on validation? **Yes** (11.865 vs next-best random_valid 9.429).

## Response model (simulator correctness predictor; not the RL policy)

Validation (held-out ASSISTments learners): accuracy 0.651, ROC-AUC 0.707, Brier 0.219, log-loss 0.628 (n=48089).  
Test (final report only): accuracy 0.666, ROC-AUC 0.712, Brier 0.216, log-loss 0.622 (n=54871).

## Ethical / academic notes

- Cite the ASSISTments dataset page URL in publications.
- Keep synthetic / fixture trajectories separate from real ASSISTments evidence.
- Domain adaptation and a supervised pilot on AdaptiveLearnSE/C1 features are required before any student-facing deployment.

## C1 / SE product mapping (future)

See `docs/SE_INTEGRATION_PLAN.md`. C1 SE topic IDs are **not** ASSISTments skill IDs; the research predictor must stay separate.
