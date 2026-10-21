# SE supervised simulation protocol (`se-supervised-sim-v0`)

Package: `training_se_supervised/`. Colab: `experiments/06_se_supervised_simulation.ipynb`.

## Targets (implemented)

| ID | Target | Label | Primary val metric |
|---|---|---|---|
| A | Next-attempt correctness | `y_correct` | log loss |
| B | Synthetic mock-exam score | `y_exam_score` ∈ [0,1] | MAE |
| B-opt | Pass | `y_pass = 1[y_exam_score ≥ 0.55]` | log loss (if both classes ≥8 in train) |

Pass threshold **0.55** is frozen in `contract.py` before fitting. Not an institutional cutoff.

## Synthetic contract (assumed, not fitted)

- 12-topic C1 practice catalogue (shared with `training_se`).
- Smoke: 60 learners; full: 2000 learners (see `SizeConfig`).
- Question bank per topic with assumed difficulty ~ Normal(μ, σ) per scenario.
- Learners: latent ability + topic affinities (audit-only).
- Practice: chronological attempts; stochastic topic choice with weak-topic bias; Bernoulli responses via logistic of (ability + affinity + practice gain − difficulty + noise).
- Mock exam: after practice cutoff; `exam_items_per_topic × 12` items; score = fraction correct.
- Separate RNG streams: learner / questions / practice / exam / split.
- Scenarios (all reported): `baseline`, `high_noise`, `easy_bank`. Selection uses `baseline` only.

## Explicit non-claims

Synthetic metrics measure agreement with the generator only. Not real SE students, not real exams. Do not auto-connect the response model into `se-path-sim-v0` without a new versioned experiment.
