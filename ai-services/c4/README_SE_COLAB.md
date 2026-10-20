# SE path simulation Colab (`se-path-sim-v0`)

## First steps

1. Open `experiments/05_se_path_simulation.ipynb` in Colab.
2. Run cell 1 (pip install).
3. Upload **`c4-se-source-colab.zip`** in cell 2 (built by `scripts/package_se_colab_zip.py`).
4. Mount Drive (cell 3) → artifacts under
   `MyDrive/AdaptiveLearnSE/c4_runs/se_path_sim_v0/`.
5. Run imports → contract display → env checks → **smoke** training.
6. Leave `RUN_FULL_TRAINING` / `RUN_FINAL_EVALUATION` False unless intentional.

Does **not** need ASSISTments CSV or `response_model.joblib`. Does **not** use Atlas.

Rebuild ZIP locally:

```powershell
cd ai-services/c4
python experiments/_generate_se_notebook.py
python scripts/package_se_colab_zip.py
```
