# Protocol `se-path-sim-v0`

Synthetic SE practice-path simulation for Colab. Separate from ASSISTments
`c4-env-eval-v1.1`. Package: `training_se/`.

## Proposal PDF

**Limitation:** The C4 proposal PDF attached in chat was **not readable** in this
agent environment (no PDF bytes available under the workspace). Requirement
mapping in `SE_MODEL_TRAINING_SPEC.md` uses the user-stated proposal themes
(RL paths, daily study activities, dynamic exam simulation using C2 content,
readiness / pass-probability when labels exist) plus repository evidence.
Reconcile again when the PDF is placed on disk.

## Dimensions

| Item | Value |
|---|---|
| Actions | 12 (`ORDERED_TOPICS` = C1 `PRACTICE_QUESTIONS` keys) |
| Observation dim | **28** = mastery×12 + availability×12 + mean, frac_mastered, step_frac, prior |
| Scale | All [0,1]; C1 0–100 ↔ /100 |
| Episode horizon | 30 steps (config) |
| Step | One synthetic practice **attempt** |
| Forgetting | **0** (explicit hypothetical default) |
| Domain labels | `domain=se_simulation`, `synthetic=true` |

## Dynamics (frozen)

- `P(correct) = clip(0.15 + 0.70 * mastery, 0.15, 0.95)`
- Gain +0.08 correct / +0.02 incorrect on selected topic only
- Reward: `0.5*correct + 1.0*gain - 0.05`
- Invalid: −1.0, no mastery change

## Baselines

- `maskable_ppo` (masks train+eval)
- `weakest_stored_mastery_v1_sim` (ranking-compatible with Node heuristic; **state source differs**)
- `random_valid` (separate RNG stream)
- `recent_performance` (window=5, cold-start lowest untried index)

## Drive

`MyDrive/AdaptiveLearnSE/c4_runs/se_path_sim_v0/` — new timestamped run folders only.
