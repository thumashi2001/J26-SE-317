# Colab: se-supervised-sim-v1

1. Build ZIP locally: `python scripts/package_se_supervised_v1_colab_zip.py`
2. Open `experiments/08_se_supervised_simulation_v1.ipynb` in Colab
3. Run cells in order: deps → upload ZIP → Drive mount → imports → contract → smoke
4. Keep gates False until intentionally enabling full / final-test
5. Artifacts land under `MyDrive/AdaptiveLearnSE/c4_runs/se_supervised_sim_v1/`

`PASS_THRESHOLD=0.55` is a synthetic label cutoff only.
Do not auto-wire response models into `se-path-sim-v1`.
