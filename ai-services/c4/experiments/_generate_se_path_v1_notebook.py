"""Generate experiments/07_se_path_simulation_v1.ipynb"""

from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parent / "07_se_path_simulation_v1.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in text.split("\n")]}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in text.split("\n")],
    }


cells = [
    md(
        "# C4 SE path simulation v1 (`se-path-sim-v1`)\n\n"
        "S1 scope: **46** C1 practice topics with semester eligibility masks.\n"
        "Additive package `training_se_v1` — does **not** modify `training_se` (v0).\n\n"
        "Synthetic simulation only. Not real student behaviour. "
        "No automatic wiring of supervised response models into this env.\n\n"
        "Run cells **in order**. `RUN_FULL_TRAINING` and `RUN_FINAL_EVALUATION` default **False**.\n"
        "Artifacts go under a **new** Drive folder (`se_path_sim_v1`), never into v0 paths."
    ),
    md("## 1. Dependencies"),
    code(
        "%pip install -q \"numpy>=1.23,<3\" \"gymnasium>=0.29.1,<2.0\" "
        "\"stable-baselines3>=2.3.0,<3.0\" \"sb3-contrib>=2.3.0,<3.0\" "
        "\"torch>=2.0\" \"pandas>=1.5,<3\" cloudpickle tqdm"
    ),
    md("## 2. Upload & extract `c4-se-v1-source-colab.zip`"),
    code(
        "from pathlib import Path\n"
        "import zipfile, shutil\n"
        "from google.colab import files\n"
        "\n"
        "UPLOAD_DIR = Path('/content/c4_se_v1_upload')\n"
        "EXTRACT_DIR = Path('/content/c4_se_v1_src')\n"
        "UPLOAD_DIR.mkdir(parents=True, exist_ok=True)\n"
        "if EXTRACT_DIR.exists():\n"
        "    shutil.rmtree(EXTRACT_DIR)\n"
        "EXTRACT_DIR.mkdir(parents=True)\n"
        "\n"
        "print('Upload c4-se-v1-source-colab.zip')\n"
        "uploaded = files.upload()\n"
        "if not uploaded:\n"
        "    raise RuntimeError('No file uploaded')\n"
        "zip_name = next(iter(uploaded))\n"
        "zip_path = UPLOAD_DIR / zip_name\n"
        "zip_path.write_bytes(uploaded[zip_name])\n"
        "with zipfile.ZipFile(zip_path, 'r') as zf:\n"
        "    zf.extractall(EXTRACT_DIR)\n"
        "print('Extracted to', EXTRACT_DIR)\n"
        "print('Top:', list(EXTRACT_DIR.iterdir())[:10])"
    ),
    md("## 3. Drive mount (v1 output root only)"),
    code(
        "from google.colab import drive\n"
        "drive.mount('/content/drive')\n"
        "DRIVE_ROOT = Path('/content/drive/MyDrive/AdaptiveLearnSE/c4_runs/se_path_sim_v1')\n"
        "DRIVE_ROOT.mkdir(parents=True, exist_ok=True)\n"
        "print('Artifacts root:', DRIVE_ROOT)\n"
        "print('Do not write into se_path_sim_v0')"
    ),
    md("## 4. Imports / versions / paths"),
    code(
        "import sys, os, json\n"
        "from pathlib import Path\n"
        "\n"
        "if 'EXTRACT_DIR' not in globals() or 'DRIVE_ROOT' not in globals():\n"
        "    raise RuntimeError('Run cells 2 (extract) and 3 (Drive mount) first.')\n"
        "\n"
        "hits = list(Path(EXTRACT_DIR).rglob('training_se_v1/protocol.py'))\n"
        "if not hits:\n"
        "    raise FileNotFoundError('training_se_v1/protocol.py not found; re-upload ZIP')\n"
        "C4_ROOT = hits[0].parents[1].resolve()\n"
        "sys.path.insert(0, str(C4_ROOT))\n"
        "os.chdir(C4_ROOT)\n"
        "print('C4_ROOT', C4_ROOT)\n"
        "\n"
        "from training_se_v1.colab_bootstrap import require_symbol\n"
        "import gymnasium, numpy, torch, stable_baselines3, sb3_contrib\n"
        "from training_se_v1.protocol import PROTOCOL_VERSION, GENERATOR_VERSION\n"
        "print('protocol', PROTOCOL_VERSION, GENERATOR_VERSION)\n"
        "print('gymnasium', gymnasium.__version__, 'sb3', stable_baselines3.__version__, "
        "'sb3_contrib', sb3_contrib.__version__, 'torch', torch.__version__)"
    ),
    md("## 5. Frozen catalogue / observation schema / assumptions"),
    code(
        "from training_se_v1.catalogue import (\n"
        "    catalogue_payload, catalogue_hash, ORDERED_TOPICS, N_TOPICS, validate_catalogue,\n"
        ")\n"
        "from training_se_v1.config import frozen_config_dict, ASSUMPTIONS\n"
        "from training_se_v1.observation import observation_schema, OBS_DIM\n"
        "\n"
        "print(validate_catalogue())\n"
        "print('n_topics', N_TOPICS, 'obs_dim', OBS_DIM)\n"
        "print('catalogue_sha256', catalogue_hash())\n"
        "print('first/last topic', ORDERED_TOPICS[0], ORDERED_TOPICS[-1])\n"
        "print(json.dumps(observation_schema(), indent=2)[:1200])\n"
        "print(json.dumps(ASSUMPTIONS, indent=2))\n"
        "print(json.dumps(frozen_config_dict(), indent=2)[:1500])\n"
        "(DRIVE_ROOT / '_session_catalogue_preview.json').write_text(\n"
        "    json.dumps({**catalogue_payload(), 'sha256': catalogue_hash()}, indent=2), encoding='utf-8'\n"
        ")"
    ),
    md("## 6. Environment + semester-mask + reproducibility checks"),
    code(
        "import numpy as np\n"
        "from training_se_v1.environment import make_env\n"
        "from training_se_v1.config import SeEnvConfig\n"
        "from catalogues.c1_practice_full_2026_10 import Y3S1_INDICES, Y3S2_INDICES\n"
        "\n"
        "cfg = SeEnvConfig()\n"
        "e1 = make_env(cfg, scenario='y3s1_sim_val', seed=0)\n"
        "e2 = make_env(cfg, scenario='y3s1_sim_val', seed=0)\n"
        "o1, i1 = e1.reset(seed=123)\n"
        "o2, i2 = e2.reset(seed=123)\n"
        "assert np.allclose(o1, o2)\n"
        "assert o1.shape == (OBS_DIM,)\n"
        "assert i1['synthetic'] is True\n"
        "assert not any(bool(i1['action_mask'][i]) for i in Y3S2_INDICES)\n"
        "print('y3s1 repro OK; mask sum', int(i1['action_mask'].sum()))\n"
        "e1.close(); e2.close()\n"
        "\n"
        "e3 = make_env(cfg, scenario='y3s2_sim_val', seed=1)\n"
        "_, i3 = e3.reset(seed=1)\n"
        "assert not any(bool(i3['action_mask'][i]) for i in Y3S1_INDICES)\n"
        "print('y3s2 mask OK; mask sum', int(i3['action_mask'].sum()))\n"
        "e3.close()"
    ),
    md("## 7. Smoke training + validation selection (both semester scenarios)"),
    code(
        "from training_se_v1.pipeline import run_training_and_validation\n"
        "\n"
        "smoke = run_training_and_validation(\n"
        "    DRIVE_ROOT,\n"
        "    mode='smoke',\n"
        "    timesteps=2000,\n"
        "    seeds=[0],\n"
        "    eval_episodes=8,\n"
        "    device='cpu',\n"
        "    cfg=cfg,\n"
        "    run_full=False,\n"
        ")\n"
        "SMOKE_RUN_DIR = Path(smoke['run_dir'])\n"
        "print('smoke run', SMOKE_RUN_DIR)\n"
        "print('selected', smoke['selection'].get('selected'))\n"
        "print(json.dumps(smoke['selection'], indent=2)[:2500])"
    ),
    md("## 8. Schema-aware comparison table (returns / mastery — not accuracy)"),
    code(
        "import pandas as pd\n"
        "\n"
        "require_symbol('SMOKE_RUN_DIR', globals().get('SMOKE_RUN_DIR'))\n"
        "sel = json.loads((SMOKE_RUN_DIR / 'selection_val.json').read_text())\n"
        "rows = []\n"
        "by_alg = sel.get('mean_val_return_by_algorithm') or sel.get('by_algorithm') or {}\n"
        "for method, stats in by_alg.items():\n"
        "    if isinstance(stats, dict):\n"
        "        rows.append({\n"
        "            'method': method,\n"
        "            'val_return_mean': stats.get('mean'),\n"
        "            'val_return_sample_sd': stats.get('sample_sd'),\n"
        "            'selected': method == sel.get('selected'),\n"
        "            'domain': 'se_simulation',\n"
        "            'synthetic': True,\n"
        "            'protocol': 'se-path-sim-v1',\n"
        "        })\n"
        "df = pd.DataFrame(rows)\n"
        "if len(df):\n"
        "    df = df.sort_values('val_return_mean', ascending=False)\n"
        "display(df)\n"
        "print('Label: simulation_only — RL metrics are returns/mastery/progress, not classification accuracy')"
    ),
    md("## 9. Full training (gated)"),
    code(
        "# Set True only for a multi-seed full run. Creates a NEW run folder under se_path_sim_v1.\n"
        "RUN_FULL_TRAINING = False\n"
        "FULL_TIMESTEPS = 50_000\n"
        "FULL_SEEDS = [0, 1, 2]\n"
        "\n"
        "FULL_RUN_DIR = None\n"
        "if RUN_FULL_TRAINING:\n"
        "    full = run_training_and_validation(\n"
        "        DRIVE_ROOT,\n"
        "        mode='full',\n"
        "        timesteps=FULL_TIMESTEPS,\n"
        "        seeds=FULL_SEEDS,\n"
        "        eval_episodes=20,\n"
        "        device='cuda',\n"
        "        cfg=cfg,\n"
        "        run_full=True,\n"
        "    )\n"
        "    FULL_RUN_DIR = Path(full['run_dir'])\n"
        "    print('full run', FULL_RUN_DIR)\n"
        "else:\n"
        "    print('Skipped full training (RUN_FULL_TRAINING=False)')"
    ),
    md("## 10. Final simulator evaluation (gated; after frozen selection)"),
    code(
        "from training_se_v1.pipeline import run_final_evaluation\n"
        "\n"
        "RUN_FINAL_EVALUATION = False\n"
        "FINAL_TARGET_RUN = FULL_RUN_DIR or globals().get('SMOKE_RUN_DIR')\n"
        "\n"
        "if RUN_FINAL_EVALUATION:\n"
        "    require_symbol('FINAL_TARGET_RUN', FINAL_TARGET_RUN)\n"
        "    plan = run_final_evaluation(FINAL_TARGET_RUN, run_final=True, eval_episodes=20, cfg=cfg)\n"
        "    print(plan)\n"
        "else:\n"
        "    print('Skipped final evaluation (RUN_FINAL_EVALUATION=False); '\n"
        "          'validation selection remains frozen separately from final test.')"
    ),
    md("## 11. Artifact export reminder"),
    code(
        "require_symbol('SMOKE_RUN_DIR', globals().get('SMOKE_RUN_DIR'))\n"
        "exp = SMOKE_RUN_DIR / 'export_bundle'\n"
        "print('Export bundle:', exp)\n"
        "print('Files:', sorted(p.name for p in exp.iterdir()) if exp.is_dir() else 'missing')\n"
        "print('Label: simulation_only / domain=se_simulation / protocol=se-path-sim-v1')\n"
        "print('Manifest:', (exp / 'manifest.json').is_file())\n"
        "print('Student Adaptive path remains heuristic; no model wiring from this notebook.')"
    ),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "cells": cells,
}
NB.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print("Wrote", NB)
