# C4 observability and evaluation protocol (`c4-env-eval-v1.1`)

## Confirmed bug (fixed in v1.1)

On invalid actions, `_steps` (environment clock) advanced but observation
`step_frac` used `LearnerSimState.step`, which does **not** advance on invalid
transitions. Elapsed episode time in the observation was therefore inconsistent.

**Fix:** `step_frac` uses elapsed environment steps (`_steps`). Learner
interaction count remains `LearnerSimState.step` / `info["learner_interaction_count"]`.

Observation **dimension** is unchanged (`n_skills + 4`) so old SB3 checkpoints
still load. Re-evaluate under v1.1; do not assume step_frac semantics match pre-v1.1.

## Partial observability

| Visible to policy (observation) | Used by response simulator but hidden from policy |
|---|---|
| Per-skill mastery | `skill_attempts`, `skill_correct`, `skill_streak` |
| Mean mastery, frac mastered | Global attempt/correct counts |
| Elapsed env step fraction | Logistic regression features / coefficients |
| `prior_strength` | Assumed mastery gain / forgetting parameters |

Implication: the control problem is partially observable relative to the
simulator’s internal history. This is intentional for v1.1 (no silent obs
expansion that would break old checkpoints).

## What is actually held out

1. **Real ASSISTments learners** — train/validation/test split from notebook 01
   (response model fit on train only). This is the true held-out structure for
   supervised response modelling.
2. **Simulator scenario names** (`sim_train` / `sim_val` / `sim_test`) — only
   change **initial `prior_strength` presets**. They are **not** disjoint real
   students.
3. **Episode seeds** — validation / diagnostic / test bands are numerically
   disjoint (`training/protocol.py`).

## Masking

- Vanilla **DQN/PPO**: unmasked; learn via invalid-action penalties.
- **maskable_ppo** (opt-in, `sb3-contrib.MaskablePPO`): masks during **train and
  eval**. Inference-only remapping is not masked training.
- Heuristics: use masks at decision time.

## Mastery metrics

- `selected_skill_mastery_gain_sum` — sum of per-step gains on the **chosen** skill.
- `mean_mastery_delta_final_minus_initial` / `total_mastery_delta_final_minus_initial`
  — end vs start across **all** skills (includes forgetting).
