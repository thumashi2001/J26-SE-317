# SE supervised simulation v1 (`se-supervised-sim-v1`)

Additive supervised prototypes on the S1 46-topic catalogue. Does **not**
modify `training_se_supervised` (v0) or auto-connect into `se-path-sim-v1`.

## Targets

1. Next-attempt correctness (`y_correct`)
2. Synthetic mock-exam score (`y_exam_score` ∈ [0,1])
3. Synthetic pass label (`y_pass = 1[y_exam_score ≥ 0.55]`) — **labelled cutoff only**,
   not an institutional rule

`CLASSIFICATION_PROB_THRESHOLD=0.5` is separate (hard-class accuracy only).

## Features

- Response: 8 base numerics + 46 topic one-hots → **54** columns
- Exam: 46 attempts + 46 accuracies + 6 globals → **98** columns
- Learner-disjoint splits; pre-target chronology; train-only preprocessing
- Latent generator values excluded from model inputs

## Exam coverage

- Y3S1 exam items: `2 * 28 = 56` (eligible Y3S1 topics only)
- Y3S2 exam items: `2 * 18 = 36` (eligible Y3S2 topics only)

## Delivery

- Package: `ai-services/c4/training_se_supervised_v1/`
- Notebook: `experiments/08_se_supervised_simulation_v1.ipynb`
- Colab ZIP: `c4-se-supervised-v1-source-colab.zip`
- Drive root: `…/AdaptiveLearnSE/c4_runs/se_supervised_sim_v1`
- Gates default False; frozen validation selection separate from final test
- Do not retune generation or test data to force 80–90% accuracy
