# SE simulation demo checkpoint selection

**Decision made at import/inference wiring time** from **saved validation results
only** (bundle `selection_val.json`). This is **not** described as a preregistered
choice before those metrics existed.

## Rule applied now

Among MaskablePPO training seeds `{0,1,2}`, choose the seed with the highest
**mean validation episode return**. On a tie, lowest seed wins.

## Saved per-seed validation mean returns

| Seed | Mean validation return | Checkpoint SHA-256 |
|---|---|---|
| **0** | **8.059999790787698** | `265bbf85cdd4b1096ba90752e2cc39f1d45daf8655ad97346f2f7d64f38c0468` |
| 1 | 7.639999769628049 | `40068d2a69e06073e50e177afc9534442e895895e9c4f79e779066bb8b15ca09` |
| 2 | 7.6119997575879115 | `614151d0423717c59f52b5df8509a8c271a9d3f9d21ee2d0072d68d24d88cf11` |

**Selected for demo inference:** seed **0**  
**Relative path:** `export_bundle/models/seed_0/maskable_ppo_final.zip`  
**Model hash:** `265bbf85cdd4b1096ba90752e2cc39f1d45daf8655ad97346f2f7d64f38c0468`  

All three checkpoints and aggregate research results remain in the imported bundle.
Final-test metrics were **not** used for this demo choice.
