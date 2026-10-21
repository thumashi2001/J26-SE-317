# Colab: se-path-sim-v2 — PAUSED

**Do not run full training or activate in product now.** Scaffolding only.

Would replace the unobservable `prior_strength` latent with frozen `episode_init_mean_mastery`.
Does **not** overwrite v1. Live product stays on se-path-sim-v1.

1. Build ZIP locally: `python scripts/package_se_v2_colab_zip.py`
2. Upload `experiments/colab_zips/se_path_sim_v2_colab.zip` to Colab
3. Open `experiments/notebooks/v2/01_se_path_simulation_v2.ipynb`
4. Run cells in order; keep `RUN_FULL_TRAINING = False` until intentional
5. Full-train exports: `MyDrive/AdaptiveLearnSE/c4_runs/se_path_sim_v2/`
6. Import with a **new** v2 loader only after catalogue + schema checks pass

Live product continues on **se-path-sim-v1** + protocol constant prior until v2 artifacts exist.
