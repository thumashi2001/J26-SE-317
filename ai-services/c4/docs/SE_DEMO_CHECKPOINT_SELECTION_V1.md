# SE path simulation v1 demo checkpoint selection

**Decision made at inference wiring time** from **saved validation results only**
(`export_bundle/selection_val.json` for
`train_full_se-path-sim-v1_20261013T181643.681Z`).
Not described as a preregistered choice before those metrics existed.

## Rule

Among MaskablePPO training seeds `{0,1,2}`, choose the seed with the highest
**mean of per-semester validation episode returns** (average of Y3S1 and Y3S2
`summary.return.mean`). On an exact tie, **lowest seed** wins.

Final-test metrics were **not** used.

## Saved per-seed validation returns

| Seed | Y3S1 `return.mean` | Y3S2 `return.mean` | Mean across semesters | Checkpoint SHA-256 |
|---|---|---|---|---|
| 0 | 11.091999648511406 | 10.72799968719482 | 10.909999667853114 | `62399dbe53dac15f25bf3984150fbba84b871770791eca3dcd364ea749e8cb86` |
| 1 | 10.867999672889704 | 10.923999677598472 | 10.895999675244088 | `3cb010399cd7920a756f415f82d0c9a12ca2d6a860d1e2e43801488d429fbbb2` |
| **2** | **11.455999673902983** | **11.091999699175354** | **11.273999686539169** | `53d2c5d60698b7debe96ed42db1b6e22089ef96875c75e63a205550dd6c3c029` |

**Selected for `/v1/se-path-simulation-v1/*` demo inference:** seed **2**  
**Relative path:** `export_bundle/models/seed_2/maskable_ppo_final.zip`  
**Model hash:** `53d2c5d60698b7debe96ed42db1b6e22089ef96875c75e63a205550dd6c3c029`

All three seed checkpoints remain in the imported bundle. Aggregate algorithm
selection (`selected=maskable_ppo`) is separate from this per-seed demo choice.
