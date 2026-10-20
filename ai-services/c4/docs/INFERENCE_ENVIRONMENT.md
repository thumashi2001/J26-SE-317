# Verified local inference environment

Captured on the machine where real MaskablePPO inference and
`tests/test_inference_service.py` (**11 passed**) were executed.
**Do not claim another environment is verified without re-running those tests.**

| Field | Value |
|---|---|
| OS | Windows 11 (win32 10.0.26200) |
| Python | **3.13.9** (`tags/v3.13.9:8183fa5`, MSC v.1944, 64-bit) |
| Torch build reported | `2.14.1+cpu` (`pip freeze` lists `torch==2.14.1`) |
| Pin file | `../constraints-runtime.txt` |
| Runtime reqs | `../requirements.txt` |
| Dev/test reqs | `../requirements-dev.txt` |

## Install

```powershell
cd ai-services/c4
python -m pip install -c constraints-runtime.txt -r requirements.txt
# for tests:
python -m pip install -c constraints-runtime.txt -r requirements.txt -r requirements-dev.txt
```

## Verify

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/import_research_bundle.py --verify-only runtime-artifacts\c4_maskable_ppo_research_bundle_20261012T062204868154Z
python -m pytest tests/test_inference_service.py -v
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

## SE v1 isolated inference (additional)

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest tests/test_se_path_sim_v1_inference.py tests/test_se_supervised_v1_inference.py -v
# Docs: SE_PATH_SIM_V1_INFERENCE.md, SE_SUPERVISED_SIM_V1_INFERENCE.md,
#        SE_DEMO_CHECKPOINT_SELECTION_V1.md
```

v1 routes are independent of v0/ASSISTments; a v1 503 must not disable other families.

## Notes

- Training-time versions in the Colab bundle `train_config.json` (e.g. gymnasium 1.3.0, torch 2.11.0+cpu) differ from this local inference pin set. Checkpoint load succeeded here; that does not auto-verify every other OS/Python combination.
- `pytest` / `httpx` are development-only for the service test client; production runtime install can omit `requirements-dev.txt`.
