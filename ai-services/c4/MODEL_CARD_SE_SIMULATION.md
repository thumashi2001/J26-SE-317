# Model card — SE path simulation MaskablePPO (`se-path-sim-v0`)

Figures reconciled from imported bundle
`c4_se_simulation_bundle_20261012T084659312700Z`
(`export_bundle/selection_val.json`, `final_simulator_test/test_summary.csv`,
`run_metadata/*/train_meta.json`, `train_config.json`). **Simulation only.**

## Model details

| Field | Value |
|---|---|
| Protocol | `se-path-sim-v0` |
| Domain | `se_simulation` / `synthetic=true` |
| Algorithm (validation-selected) | `maskable_ppo` |
| Seeds | 0, 1, 2 |
| Requested timesteps / seed | 50000 |
| Actual timesteps / seed | 50176 (from train_meta) |
| Device (training capture) | cpu |
| Training stack (train_meta) | gymnasium 1.3.0; numpy 2.1.3; sb3_contrib 2.9.0; stable_baselines3 2.9.0; torch 2.11.0+cpu |
| Actions | 12 C1 practice topics (practice-only initial catalogue) |
| Observation dim | 28 |
| Forgetting | **None** (explicit v0 hypothetical default) |

## Demo checkpoint (inference)

Chosen **now** from saved validation means (highest = seed 0). See
`docs/SE_DEMO_CHECKPOINT_SELECTION.md`. Not a preregistered pick.

| Field | Value |
|---|---|
| Seed | 0 |
| Model SHA-256 | `265bbf85cdd4b1096ba90752e2cc39f1d45daf8655ad97346f2f7d64f38c0468` |
| Catalogue SHA-256 | `5001dd005443e61a27118d094ee02bd3c39fb668bbc7222dc95951e3f0624543` |

## Assumptions (synthetic — not measured SE behaviour)

- One step = one practice **attempt**
- `P(correct)=clip(0.15 + 0.70·mastery, 0.15, 0.95)`
- Mastery gains +0.08 / +0.02 on selected topic; no cross-topic forgetting
- Reward: `0.5·correct + 1.0·selected_gain − 0.05`

## Table A — Validation (selection; mean of per-seed means ± sample SD)

| Method | Val return |
|---|---|
| **maskable_ppo** | **7.7707 ± 0.2510** |
| random_valid | 6.7160 ± 0.1749 |
| recent_performance | 6.4920 ± 0.1220 |
| weakest_stored_mastery_v1_sim | 6.1560 ± 0.2963 |

Per-seed MaskablePPO val means: 8.060, 7.640, 7.612.

## Table B — Final simulator test (reporting only; not used for demo seed pick)

From `test_summary.csv` (mean ± sample SD across seeds):

| Method | Return | Selected-topic gain | Net total mastery Δ | Invalid rate |
|---|---|---|---|---|
| maskable_ppo | 8.704 ± 0.778 | 1.621 ± 0.078 | 1.621 ± 0.078 | 0.0 |
| random_valid | 7.966 ± 0.771 | 1.550 ± 0.082 | 1.550 ± 0.082 | 0.0 |
| recent_performance | 8.084 ± 0.739 | 1.559 ± 0.077 | 1.559 ± 0.077 | 0.0 |
| weakest_stored_mastery_v1_sim | 7.603 ± 0.762 | 1.511 ± 0.082 | 1.511 ± 0.082 | 0.0 |

With no forgetting, selected-topic cumulative gain equals net total mastery change
in these runs (no interference mass).

## Limitations

- Not validated on real SE students
- Not exam simulation or readiness / pass-probability
- Practice-only 12-topic catalogue ≠ full lecture coverage
- Node heuristic path remains separate from this sim policy
- Local inference may use a newer torch build than Colab training; verify load with tests

## Inference

Isolated FastAPI: `/v1/se-simulation/ready|catalogue|predict` (see
`docs/SE_SIMULATION_INFERENCE.md`). Does not disable `/v1/research/*`.
