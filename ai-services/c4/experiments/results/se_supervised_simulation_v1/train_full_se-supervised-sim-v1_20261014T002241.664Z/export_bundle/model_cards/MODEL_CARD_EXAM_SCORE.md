# Model card — synthetic mock-exam score

- Protocol: `se-supervised-sim-v1`
- Domain markers: `{'domain': 'se_simulation', 'synthetic': True, 'simulation_only': True, 'real_exam_validation': False, 'protocol': 'se-supervised-sim-v1', 'generator_version': 'se_supervised_gen_v1', 'scope_decision': 'S1'}`
- Selected model (validation MAE): **ridge_regression**
- Score scale: fraction correct in [0, 1]

## Target

At prediction cutoff (end of practice), predict subsequent mock-exam
`y_exam_score` from prior practice features only. Exam answers and
latents are excluded.

## Validation comparison

- `train_mean`: mae=0.15067650541698163, rmse=0.1821180451621497, y_mean=0.5214329805996473, n=300
- `ridge_regression`: mae=0.06850262447014432, rmse=0.083333534257756, y_mean=0.5214329805996473, n=300
- `hist_gradient_boosting_regressor`: mae=0.06997721398839246, rmse=0.08601329052823925, y_mean=0.5214329805996473, n=300

## Final test

Executed: False. Not run (gated).

## Non-claims

- Synthetic performance measures agreement with the generator only.
- Results do not validate real SE students or actual module exams.
- Assumed generator parameters are not empirically fitted.
- Do not wire this response model into se-path-sim-v1 without a new versioned experiment.
- PASS_THRESHOLD 0.55 is a labelled synthetic exam-score cutoff, not an institutional rule.
- Classification probability operating point is separate from PASS_THRESHOLD.
