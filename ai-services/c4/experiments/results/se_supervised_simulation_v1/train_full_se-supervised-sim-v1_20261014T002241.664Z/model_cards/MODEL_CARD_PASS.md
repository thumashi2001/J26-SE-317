# Model card — synthetic mock-exam pass (optional)

- Pass threshold (declared before training): **0.55**
- Note: Pass label = 1[y_exam_score >= 0.55] on the synthetic exam fraction-correct scale. This is a declared synthetic exam-score cutoff only — not an institutional rule.
- Selected model: **logistic_regression**

## Validation comparison

- `constant_train_prevalence`: log_loss=0.6859556538650001, brier=0.24641275510204083, roc_auc=0.5, prevalence=0.44
- `logistic_regression`: log_loss=0.3213306231001037, brier=0.10145395651240419, roc_auc=0.9349296536796536, prevalence=0.44
- `hist_gradient_boosting_classifier`: log_loss=0.34735813833299756, brier=0.11120593241641719, roc_auc=0.9250541125541126, prevalence=0.44

## Non-claims

- Synthetic performance measures agreement with the generator only.
- Results do not validate real SE students or actual module exams.
- Assumed generator parameters are not empirically fitted.
- Do not wire this response model into se-path-sim-v1 without a new versioned experiment.
- PASS_THRESHOLD 0.55 is a labelled synthetic exam-score cutoff, not an institutional rule.
- Classification probability operating point is separate from PASS_THRESHOLD.
