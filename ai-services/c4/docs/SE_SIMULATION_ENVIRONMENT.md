# SE simulation inference — verified local load environment

Recorded where the **real** seed-0 MaskablePPO checkpoint from
`c4_se_simulation_bundle_20261012T084659312700Z` was loaded and
`tests/test_se_simulation_inference.py` executed.

| Field | Value |
|---|---|
| OS | Windows 11 (win32 10.0.26200) |
| Python | 3.13.9 |
| Training capture (bundle train_meta) | gymnasium 1.3.0; torch 2.11.0+cpu; sb3_contrib 2.9.0 |
| Local load stack (this machine) | Uses existing research runtime pins where possible; torch may be newer than Colab training |

**Do not** blindly replace `constraints-runtime.txt` (ASSISTments research) solely
because Colab trained on slightly different patch versions — verify SE load with
tests instead.

Re-verify on another machine by re-running the SE inference tests after import.
