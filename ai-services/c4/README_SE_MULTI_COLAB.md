# Colab: se-path-multi-v1

Multi-action policy (practice, revision, quiz). Coding stays masked. No `prior_strength` observation slot.

The student plan stays on the heuristic activity mix, plus the experimental v1 practice pin, until a full native MaskablePPO export passes the loader checks. `activation_allowed: true` alone does not activate anything. A linear `policy.npz` is not loaded.

## Local checks (do not start the 80k run)

From `ai-services/c4`:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m training_se_v2.multi_action.run_smoke
python -m training_se_v2.multi_action.parity_export
```

Smoke checks the observation contract and the separate linear smoke file. It prints `activation_allowed` false.

Parity trains 128 MaskablePPO steps, reloads `maskable_ppo_final.zip` through the production predict function, and checks:

- the same deterministic action on Y3S1 and Y3S2 masks
- masked action probabilities match after reload
- coding and other masked actions stay at probability 0
- an all-false mask is rejected
- the parity folder is not ready for activation
- flipping `activation_allowed` and `training_mode` on that 128-step run is still rejected
- `policy.npz` alone is rejected

Parity output stays in `experiments/parity_runs/se_path_multi_v1/`. Do not copy it to `runtime-artifacts`.

## Full training

1. `python scripts/package_se_multi_v1_colab_zip.py`
2. In Colab, open `experiments/notebooks/v2/02_se_path_multi_v1.ipynb` from the ZIP, or upload that notebook separately.
3. Run the cells from the top. The first code cell installs numpy, Gymnasium, stable-baselines3 and sb3-contrib. The next code cell uploads `se_path_multi_v1_colab.zip` if it is not already in `/content`, extracts it, and sets `ROOT` to the directory that contains `training_se_v2/multi_action/smoke_runner.py`. Do not assume the source is at `/content/c4`.
4. Leave `RUN_FULL_TRAINING = False`. The smoke cell should print the protocol, observation size 101, and 184 actions, and `training_se_v1.protocol` must resolve inside `ROOT`.
5. Set `RUN_FULL_TRAINING = True` and run the last code cell only for the real run (`run_full`, seeds 0, 1, 2, 80,000 steps, validation selection, then frozen test).
6. The export is `MyDrive/AdaptiveLearnSE/c4_runs/se_path_multi_v1/run_full/export/`.

Copy that export folder to:

`ai-services/c4/runtime-artifacts/se_path_multi_v1/active/`

Restart the C4 Python service on port 8004. Restart Node once if it is still running the build from before this integration. The next path create or replan calls `/v1/se-path-multi-v1/predict`. If that returns 503, the heuristic plan remains.

Do not report simulator return as accuracy.
