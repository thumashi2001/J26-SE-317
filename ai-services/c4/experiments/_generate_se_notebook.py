"""Generate experiments/05_se_path_simulation.ipynb"""

from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parent / "05_se_path_simulation.ipynb"


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
        "# C4 SE path simulation (se-path-sim-v0)\n\n"
        "Synthetic SE practice RL — **not** ASSISTments, **not** real student labels.\n\n"
        "Run cells **in order**. Full training and final eval are gated by flags."
    ),
    md("## 1. Dependencies"),
    code(
        "%pip install -q \"numpy>=1.23,<3\" \"gymnasium>=0.29.1,<2.0\" "
        "\"stable-baselines3>=2.3.0,<3.0\" \"sb3-contrib>=2.3.0,<3.0\" "
        "\"torch>=2.0\" \"pandas>=1.5,<3\" cloudpickle tqdm"
    ),
    md("## 2. Upload & extract `c4-se-source-colab.zip`"),
    code(
        "from pathlib import Path\n"
        "import zipfile, shutil\n"
        "from google.colab import files\n"
        "\n"
        "UPLOAD_DIR = Path('/content/c4_se_upload')\n"
        "EXTRACT_DIR = Path('/content/c4_se_src')\n"
        "UPLOAD_DIR.mkdir(parents=True, exist_ok=True)\n"
        "if EXTRACT_DIR.exists():\n"
        "    shutil.rmtree(EXTRACT_DIR)\n"
        "EXTRACT_DIR.mkdir(parents=True)\n"
        "\n"
        "print('Upload c4-se-source-colab.zip')\n"
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
    md("## 3. Drive mount"),
    code(
        "from google.colab import drive\n"
        "drive.mount('/content/drive')\n"
        "DRIVE_ROOT = Path('/content/drive/MyDrive/AdaptiveLearnSE/c4_runs/se_path_sim_v0')\n"
        "DRIVE_ROOT.mkdir(parents=True, exist_ok=True)\n"
        "print('Artifacts root:', DRIVE_ROOT)"
    ),
    md("## 4. Imports / versions / paths"),
    code(
        "import sys, os\n"
        "from pathlib import Path\n"
        "\n"
        "if 'EXTRACT_DIR' not in globals() or 'DRIVE_ROOT' not in globals():\n"
        "    raise RuntimeError('Run cells 2 (extract) and 3 (Drive mount) first.')\n"
        "\n"
        "hits = list(Path(EXTRACT_DIR).rglob('training_se/protocol.py'))\n"
        "if not hits:\n"
        "    raise FileNotFoundError('training_se/protocol.py not found under EXTRACT_DIR; re-upload ZIP')\n"
        "C4_ROOT = hits[0].parents[1].resolve()\n"
        "sys.path.insert(0, str(C4_ROOT))\n"
        "os.chdir(C4_ROOT)\n"
        "print('C4_ROOT', C4_ROOT)\n"
        "\n"
        "from training_se.colab_bootstrap import require_symbol\n"
        "import gymnasium, numpy, torch, stable_baselines3, sb3_contrib\n"
        "from training_se.protocol import PROTOCOL_VERSION, GENERATOR_VERSION\n"
        "print('protocol', PROTOCOL_VERSION, GENERATOR_VERSION)\n"
        "print('gymnasium', gymnasium.__version__, 'sb3', stable_baselines3.__version__, "
        "'sb3_contrib', sb3_contrib.__version__, 'torch', torch.__version__)"
    ),
    md("## 5. Contract / catalogue / assumptions"),
    code(
        "import json\n"
        "from training_se.catalogue import catalogue_payload, catalogue_hash, ORDERED_TOPICS\n"
        "from training_se.config import frozen_config_dict, ASSUMPTIONS\n"
        "from training_se.observation import observation_schema, OBS_DIM\n"
        "\n"
        "print('topics', ORDERED_TOPICS)\n"
        "print('catalogue_sha256', catalogue_hash())\n"
        "print('obs_dim', OBS_DIM)\n"
        "print(json.dumps(observation_schema(), indent=2)[:800])\n"
        "print(json.dumps(ASSUMPTIONS, indent=2))\n"
        "print(json.dumps(frozen_config_dict(), indent=2)[:1200])"
    ),
    md("## 6. Environment + reproducibility checks"),
    code(
        "import numpy as np\n"
        "from training_se.environment import make_env\n"
        "from training_se.config import SeEnvConfig\n"
        "\n"
        "cfg = SeEnvConfig()\n"
        "e1 = make_env(cfg, scenario='sim_val', seed=0)\n"
        "e2 = make_env(cfg, scenario='sim_val', seed=0)\n"
        "o1, i1 = e1.reset(seed=123)\n"
        "o2, i2 = e2.reset(seed=123)\n"
        "assert np.allclose(o1, o2)\n"
        "assert o1.shape == (OBS_DIM,)\n"
        "assert i1['synthetic'] is True\n"
        "print('repro OK', o1[:4], 'mask sum', i1['action_mask'].sum())\n"
        "e1.close(); e2.close()"
    ),
    md("## 7. Smoke training + validation selection"),
    code(
        "from training_se.pipeline import run_training_and_validation\n"
        "\n"
        "smoke = run_training_and_validation(\n"
        "    DRIVE_ROOT,\n"
        "    mode='smoke',\n"
        "    timesteps=2000,\n"
        "    seeds=[0],\n"
        "    eval_episodes=8,\n"
        "    device='cpu',\n"
        ")\n"
        "SMOKE_RUN_DIR = Path(smoke['run_dir'])\n"
        "print('smoke run', SMOKE_RUN_DIR)\n"
        "print('selected', smoke['selection']['selected'])\n"
        "print('mean_val', smoke['selection']['mean_val_return_by_algorithm'])"
    ),
    md("## 8. Schema-aware comparison table"),
    code(
        "import pandas as pd\n"
        "\n"
        "require_symbol('SMOKE_RUN_DIR', globals().get('SMOKE_RUN_DIR'))\n"
        "sel = json.loads((SMOKE_RUN_DIR / 'selection_val.json').read_text())\n"
        "rows = []\n"
        "for method, stats in sel['mean_val_return_by_algorithm'].items():\n"
        "    rows.append({\n"
        "        'method': method,\n"
        "        'val_return_mean': stats['mean'],\n"
        "        'val_return_sample_sd': stats['sample_sd'],\n"
        "        'selected': method == sel['selected'],\n"
        "        'domain': 'se_simulation',\n"
        "        'synthetic': True,\n"
        "        'protocol': 'se-path-sim-v0',\n"
        "    })\n"
        "df = pd.DataFrame(rows).sort_values('val_return_mean', ascending=False)\n"
        "display(df)"
    ),
    md("## 9. Full training (gated)"),
    code(
        "# Set True only when you intend a multi-seed full run. Creates a NEW run folder.\n"
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
        "        device='cpu',\n"
        "        run_full=True,\n"
        "    )\n"
        "    FULL_RUN_DIR = Path(full['run_dir'])\n"
        "    print('full run', FULL_RUN_DIR)\n"
        "else:\n"
        "    print('Skipped full training (RUN_FULL_TRAINING=False)')"
    ),
    md("## 10. Final simulator evaluation (gated; after frozen selection)"),
    code(
        "from training_se.pipeline import run_final_evaluation\n"
        "\n"
        "RUN_FINAL_EVALUATION = False\n"
        "# Point at a run that already has SELECTION_FROZEN.json (full or smoke).\n"
        "FINAL_TARGET_RUN = FULL_RUN_DIR or globals().get('SMOKE_RUN_DIR')\n"
        "\n"
        "if RUN_FINAL_EVALUATION:\n"
        "    require_symbol('FINAL_TARGET_RUN', FINAL_TARGET_RUN)\n"
        "    plan = run_final_evaluation(FINAL_TARGET_RUN, run_final=True, eval_episodes=20)\n"
        "    print(plan)\n"
        "else:\n"
        "    print('Skipped final evaluation (RUN_FINAL_EVALUATION=False)')"
    ),
    md("## 11. Artifact export reminder"),
    code(
        "require_symbol('SMOKE_RUN_DIR', globals().get('SMOKE_RUN_DIR'))\n"
        "exp = SMOKE_RUN_DIR / 'export_bundle'\n"
        "print('Export bundle:', exp)\n"
        "print('Files:', sorted(p.name for p in exp.iterdir()) if exp.is_dir() else 'missing')\n"
        "print('Label: simulation_only / domain=se_simulation / no readiness claims')\n"
        "print('Manifest:', (exp / 'manifest.json').is_file())"
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
