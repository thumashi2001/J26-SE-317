# Learning / forgetting assumptions audit

Protocol status: documents **current** `c4-env-eval-v1.1` dynamics.
Proposed semantic changes are versioned separately as
`c4-sim-dynamics-proposal-v1` and are **not** applied to defaults in this audit.

## What the current simulator does

On each **valid** practice of skill \(i\) (away from clip bounds):

| Quantity | Default (K skills) |
|---|---|
| Selected-skill gain if correct | `+0.08` |
| Selected-skill gain if incorrect | `+0.02` |
| Forgetting on each other skill | `-0.005` |
| Forgetting mass | `(K-1) × 0.005` |

For **K = 20** (smoke catalogue size):

- Correct → net total mastery ≈ `0.08 − 19×0.005 = −0.015`
- Incorrect → net total mastery ≈ `0.02 − 19×0.005 = −0.075`

**Invalid actions:** advance elapsed environment steps and apply the invalid
penalty; they do **not** apply practice-interference forgetting and do not
increment learner interaction count.

## Does forgetting represent elapsed time or practice interference?

**Current mechanism = practice interference (assumption), not calendar time.**

Evidence in code: forgetting is applied inside `Simulator.step` only when a
valid skill is practised, and only to **non-selected** skills. Invalid-action
transitions in `AdaptivePracticeEnv` never call `Simulator.step`, so no
forgetting runs on those ticks.

It is **not** fitted from ASSISTments A/B forgetting studies. It is an
assumption chosen for a simple multi-skill coupling.

A true **elapsed-time** model would decay mastery on every environment step
(including invalid) or on wall-clock gaps. That is a different semantic
proposal (`c4-sim-dynamics-proposal-v1`) and must not be silently swapped in.

## Reward objective vs net learning (mismatch)

Episode reward uses:

- `correctness_reward_weight × correct`
- `mastery_gain_weight × selected_skill_gain`
- `− time_cost_weight`

It does **not** include net total mastery change across all skills.

Therefore a policy can obtain **positive return** (especially with masking and
frequent correct answers) while **net total mastery falls**, matching the
v1.1 smoke observation (e.g. maskable_ppo return ≈ 9.5 with net total mastery
change ≈ −2.6). That is arithmetic consistency, not a training bug.

Simulator mastery gains are **not** evidence of SLIIT SE learning.

## Evidence-backed vs assumed

| Component | Status |
|---|---|
| Logistic response model on ASSISTments historical features | Fitted on train learners |
| Skill catalogue from train frequencies | Derived from data |
| Mastery gain 0.08 / 0.02 | **Assumption** |
| Forgetting 0.005 per other skill per valid step | **Assumption** (practice interference) |
| Reward weights | **Assumption** (engineering objective) |
| Blend 0.5×p_model + 0.5×mastery | **Assumption** |

## Proposed main protocol (`c4-sim-dynamics-proposal-v1`) — not applied yet

Scientifically, the main comparison protocol should:

1. **Keep** the ASSISTments-fitted response model as the behavioural core.
2. **Declare** mastery dynamics as assumed; report net total mastery and
   selected-skill gain separately (already in v1.1 metrics).
3. Prefer a dynamics setting where **correct practice is not forced to reduce
   total mastery** at the operating catalogue size **or** change the reward to
   include an explicit net-mastery term — as an **explicit** protocol bump,
   after sensitivity review, not by silently retuning to chase leaderboard wins.
4. Keep vanilla DQN/PPO as unmasked penalty baselines; keep maskable_ppo as a
   separately named masked experiment.
5. Treat checkpoint eval under altered dynamics as **transfer/sensitivity**,
   never as “trained performance” in that world.

Candidate dynamics (for later adoption only; all reported in the sensitivity
grid):

- Keep current default as a published reference condition.
- Include **no-forgetting** as a control.
- Consider break-even interference (`≈ gain_correct / (K−1)`) if multi-skill
  coupling is retained.

Do **not** adopt a setting solely because it makes RL beat heuristics.

## Historical runs

Leave all `train_*_c4-env-eval-v1.1_*` folders and checkpoints intact.
New sensitivity outputs go under a **new timestamped** directory each run
(e.g. `metrics/forgetting_sensitivity_val_<utc>/`).

## Colab (real data) vs local fixtures

| Context | Artifacts / checkpoint | Interpretation |
|---|---|---|
| **Colab Drive** | `/content/drive/MyDrive/AdaptiveLearnSE/c4_runs/artifacts` and smoke run `train_smoke_c4-env-eval-v1.1_20261012T044411.975097+0000` (`seed_42` MaskablePPO) | Real ASSISTments-backed audit |
| **Local Cursor** | Software fixtures under `datasets/fixtures/` | Pipeline checks only — **not** research sensitivity results |

Use `train_seed=42` (and `checkpoint_training_seed=42`) on Colab so validation episode seeds match the smoke checkpoint seed across every method and grid setting.
