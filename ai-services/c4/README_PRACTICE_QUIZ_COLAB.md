# This-quiz pass pipeline (not served)

`se-supervised-sim-v1` predicts a different synthetic exam and must not be labelled as P(pass) for the C4 practice-bank quiz.

This package trains only on pre-start features for that quiz blueprint. The 0.6 cutoff is a product rule, not an institutional pass mark. Smoke and Colab runs keep `activation_allowed=false`. The live plan continues to show the heuristic `c4-practice-quiz-estimate-v1` and “insufficient evidence” for pass probability until a reviewed artifact is imported on purpose.

## Colab

1. Upload `experiments/colab_zips/practice_quiz_pass_v1_colab.zip`.
2. Unzip it and set the working directory to the extracted `c4` folder.
3. Run `experiments/notebooks/practice_quiz/01_practice_quiz_pass_v1.ipynb`, or:

```bash
python -m training_practice_quiz_v1.smoke_runner
```

Set `PRACTICE_QUIZ_FULL=1` only when you want the larger synthetic run (400 learners). That run still keeps `activation_allowed=false` and must not be copied into `runtime-artifacts`.
