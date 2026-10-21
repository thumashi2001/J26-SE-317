# Colab: se-path-multi-v2

`se-path-multi-v1` stays as historical evidence. Its quiz reward is a correctness bonus and its revision reward can be paid after clipping. This protocol pays the actual clipped mastery change for practice, revision and quiz.

The live student plan is unchanged. It still uses the heuristic activity mix and the experimental v1 practice pin. Do not copy this export into `runtime-artifacts/se_path_multi_v1/active/`.

## Objective, frozen before training

- Primary metric: mean mastery change on topics available at episode start. Synthetic. Not accuracy.
- Also report weakest-topic progress, return split into learning delta and invalid penalty, action-type counts, invalid-action rate, and no-progress rate.
- Reward: clipped mastery change. Correctness bonus is 0. Invalid action is -0.2.
- Every action lasts one simulator step. There is no duration model, so comparisons are per action over 40 steps.
- Training revision `se-path-multi-v2-coverage-r2`: every seed alternates episodes, even index Y3S1 and odd index Y3S2. Seed 1 is not trained on Y3S2 alone.
- Selection: highest mean of Y3S1 and Y3S2 validation `mean_mastery_change`, seeds 0, 1 and 2, 80,000 steps. Ties use the lowest seed.
- Validation bank, shared by every candidate: Y3S1 `81000 + episode`, Y3S2 `82000 + episode`. Held-out bank: Y3S1 `91000 + episode`, Y3S2 `92000 + episode`. Training episode RNG is `11000000 + train_seed * 100000 + episode_index`. These streams do not overlap, and they are not the v1 final-test seeds. All of them are synthetic.
- A full export is rejected unless every seed has Y3S1 and Y3S2 episode and step counts, and neither semester is under 25% of that seed's steps. The mastery acceptance floor is unchanged.
- `activation_allowed` is true only when validation invalid-action rate is 0 and validation mastery change is at least the lowest of `weakest_practice`, `recent_performance` and `weakest_multi`. Training finishing is not approval. Passing is not real-student validation.
- `serves_students` stays false.

## Run

1. `python scripts/package_se_multi_v2_colab_zip.py`
2. Open `experiments/notebooks/v2/03_se_path_multi_v2.ipynb`.
3. Run from the top. Install dependencies, upload `se_path_multi_v2_colab.zip`, and let the notebook find the extracted root.
4. Leave `RUN_FULL_TRAINING = False`. Smoke should print a coverage line for seeds 0, 1 and 2, then `OK se-path-multi-v2`, and must not activate a policy.
5. Set `RUN_FULL_TRAINING = True` only for one corrected full run. The notebook writes a new timestamped directory under `MyDrive/AdaptiveLearnSE/c4_runs/se_path_multi_v2/`. It does not overwrite an older run. Read `semester_coverage` and `criterion_met` before importing anything.

Export directory: `<that timestamped run>/export/`

It contains `maskable_ppo_final.zip`, per-seed zips, `manifest.json`, `observation_schema.json`, `selection_val.json`, `final_test.json`, `train_config.json`, `dependency_versions.json` and `checksums.json`.

The verified run `se-path-multi-v2-coverage-r2_20261017T040345500695Z` is imported under `runtime-artifacts/se_path_multi_v2/`. `active/` is the rollback point: delete that directory and the endpoint returns to not-ready. The student plan then keeps the heuristic and says the recommendation is not RL. `serves_students` stays false. Passing the synthetic floor is not real-student effectiveness.
