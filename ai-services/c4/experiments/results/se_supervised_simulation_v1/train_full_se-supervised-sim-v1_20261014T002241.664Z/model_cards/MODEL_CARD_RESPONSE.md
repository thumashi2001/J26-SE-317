# Model card — SE next-attempt correctness (synthetic)

- Protocol: `se-supervised-sim-v1`
- Domain markers: `{'domain': 'se_simulation', 'synthetic': True, 'simulation_only': True, 'real_exam_validation': False, 'protocol': 'se-supervised-sim-v1', 'generator_version': 'se_supervised_gen_v1', 'scope_decision': 'S1'}`
- Selected model (validation `log_loss`): **hist_gradient_boosting_classifier**
- Primary scenario: `baseline`

## Target

Predict `y_correct` for the next practice attempt using features computed
strictly before that attempt. Synthetic generator agreement only.

## Validation comparison

- `constant_train_prevalence`: log_loss=0.6931768926913289, brier=0.25001485606236307, roc_auc=0.5, prevalence=0.4820337503636893, n=13748
- `logistic_regression`: log_loss=0.6149419583557282, brier=0.21315862187238227, roc_auc=0.7201948207478366, prevalence=0.4820337503636893, n=13748
- `hist_gradient_boosting_classifier`: log_loss=0.6103379736241487, brier=0.2112751580726346, roc_auc=0.7252752105613995, prevalence=0.4820337503636893, n=13748

## Final test

Executed: False. Not run (gated). Do not invent metrics.

## Non-claims

- Synthetic performance measures agreement with the generator only.
- Results do not validate real SE students or actual module exams.
- Assumed generator parameters are not empirically fitted.
- Do not wire this response model into se-path-sim-v1 without a new versioned experiment.
- PASS_THRESHOLD 0.55 is a labelled synthetic exam-score cutoff, not an institutional rule.
- Classification probability operating point is separate from PASS_THRESHOLD.

## Sensitivity scenarios

All predeclared scenarios are reported in `scenario_sensitivity.json`.
Generator settings were not retuned after seeing metrics.

