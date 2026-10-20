# C4 runtime artifacts (gitignored)

Place imported research / SE simulation bundles here. Model `.zip` checkpoints,
`response_model.joblib`, and raw datasets must **not** be committed.

## Layout

```
runtime-artifacts/
  c4_maskable_ppo_research_bundle_.../     # ASSISTments research (do not overwrite)
  se_path_sim_v0/
    c4_se_simulation_bundle_.../           # SE path simulation export_bundle + run_metadata
  se_supervised_sim_v0/
    c4_se_supervised_bundle_.../           # SE supervised simulation export_bundle
  *.zip                                    # source ZIPs (also gitignored via *.zip)
```

```powershell
cd ai-services/c4
python scripts/import_research_bundle.py "path\to\assistments_bundle.zip"
python scripts/import_se_simulation_bundle.py runtime-artifacts\c4_se_simulation_bundle_....zip
python scripts/import_se_supervised_bundle.py runtime-artifacts\c4_se_supervised_bundle_....zip
```

ASSISTments demo seed: `docs/DEMO_CHECKPOINT_SELECTION.md` (seed 2).  
SE simulation demo seed: `docs/SE_DEMO_CHECKPOINT_SELECTION.md` (seed 0, chosen from saved val).  
SE supervised models: frozen selection in bundle `SELECTION_FROZEN.json` (do not reselect).
