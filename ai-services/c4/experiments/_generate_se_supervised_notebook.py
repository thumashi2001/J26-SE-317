"""Generate experiments/06_se_supervised_simulation.ipynb"""

from __future__ import annotations

import json
from pathlib import Path

NB = Path(__file__).resolve().parent / "06_se_supervised_simulation.ipynb"


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
        "# C4 SE supervised simulation (`se-supervised-sim-v0`)\n\n"
        "Synthetic prototypes:\n"
        "- **A.** Next-attempt correctness\n"
        "- **B.** Future mock-exam score (+ optional pass if classes support it)\n\n"
        "Explicitly synthetic. **Not** real SE / real-exam validation. "
        "Does **not** retrain ASSISTments or SE MaskablePPO.\n\n"
        "Run cells **in order**. Full training and final-test are gated (`False` by default)."
    ),
    md("## 1. Dependencies"),
    code(
        "%pip install -q \"numpy>=1.23,<3\" \"pandas>=1.5,<3\" \"scikit-learn>=1.2,<2\" "
        "\"scipy>=1.10,<2\" \"joblib>=1.2,<2\" matplotlib tqdm"
    ),
    md("## 2. Upload & extract `c4-se-supervised-source-colab.zip`"),
    code(
        "from pathlib import Path\n"
        "import zipfile, shutil\n"
        "from google.colab import files\n"
        "\n"
        "UPLOAD_DIR = Path('/content/c4_se_sup_upload')\n"
        "EXTRACT_DIR = Path('/content/c4_se_sup_src')\n"
        "UPLOAD_DIR.mkdir(parents=True, exist_ok=True)\n"
        "if EXTRACT_DIR.exists():\n"
        "    shutil.rmtree(EXTRACT_DIR)\n"
        "EXTRACT_DIR.mkdir(parents=True)\n"
        "\n"
        "print('Upload c4-se-supervised-source-colab.zip')\n"
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
        "DRIVE_ROOT = Path('/content/drive/MyDrive/AdaptiveLearnSE/c4_runs/se_supervised_sim_v0')\n"
        "DRIVE_ROOT.mkdir(parents=True, exist_ok=True)\n"
        "print('Artifacts root:', DRIVE_ROOT)"
    ),
    md("## 4. Imports / versions / paths"),
    code(
        "import sys, os, json\n"
        "from pathlib import Path\n"
        "\n"
        "if 'EXTRACT_DIR' not in globals() or 'DRIVE_ROOT' not in globals():\n"
        "    raise RuntimeError('Run cells 2 (extract) and 3 (Drive mount) first.')\n"
        "\n"
        "hits = list(Path(EXTRACT_DIR).rglob('training_se_supervised/protocol.py'))\n"
        "if not hits:\n"
        "    raise FileNotFoundError('training_se_supervised/protocol.py not found; re-upload ZIP')\n"
        "C4_ROOT = hits[0].parents[1].resolve()\n"
        "sys.path.insert(0, str(C4_ROOT))\n"
        "os.chdir(C4_ROOT)\n"
        "print('C4_ROOT', C4_ROOT)\n"
        "\n"
        "from training_se_supervised.colab_bootstrap import require_symbol\n"
        "from training_se_supervised.protocol import PROTOCOL_VERSION, GENERATOR_VERSION, DOMAIN_MARKERS\n"
        "from training_se_supervised.provenance import capture_versions\n"
        "print('protocol', PROTOCOL_VERSION, GENERATOR_VERSION)\n"
        "print('markers', DOMAIN_MARKERS)\n"
        "print(json.dumps(capture_versions(), indent=2))"
    ),
    md("## 5. Frozen generation / evaluation contract + data inventory"),
    code(
        "from training_se_supervised.contract import frozen_contract_dict, PASS_THRESHOLD, SCENARIOS\n"
        "from training_se_supervised.inventory import inventory_local_se_exports\n"
        "from training_se_supervised.catalogue import catalogue_hash, ORDERED_TOPICS\n"
        "\n"
        "CONTRACT = frozen_contract_dict(mode='smoke', master_seed=42)\n"
        "print('pass_threshold', PASS_THRESHOLD)\n"
        "print('topics', ORDERED_TOPICS)\n"
        "print('catalogue_sha256', catalogue_hash())\n"
        "print('scenarios', list(SCENARIOS))\n"
        "print(json.dumps(CONTRACT, indent=2)[:2500])\n"
        "print(json.dumps(inventory_local_se_exports(C4_ROOT), indent=2))\n"
        "\n"
        "# Persist a copy under Drive for the session audit trail\n"
        "(DRIVE_ROOT / '_session_contract_preview.json').write_text(\n"
        "    json.dumps(CONTRACT, indent=2), encoding='utf-8'\n"
        ")"
    ),
    md("## 6. Smoke generation + leakage checks + train/evaluate on validation"),
    code(
        "from training_se_supervised.pipeline import run_training_and_validation\n"
        "\n"
        "smoke = run_training_and_validation(\n"
        "    DRIVE_ROOT,\n"
        "    mode='smoke',\n"
        "    master_seed=42,\n"
        "    c4_root=C4_ROOT,\n"
        ")\n"
        "SMOKE_RUN_DIR = Path(smoke['run_dir'])\n"
        "print('smoke run', SMOKE_RUN_DIR)\n"
        "print('selection', json.dumps(smoke['selection'], indent=2))\n"
        "print('leakage', smoke['leakage'])"
    ),
    md("## 7. Validation selection table"),
    code(
        "import pandas as pd\n"
        "\n"
        "require_symbol('SMOKE_RUN_DIR', globals().get('SMOKE_RUN_DIR'))\n"
        "sel = json.loads((SMOKE_RUN_DIR / 'selection_val.json').read_text())\n"
        "resp = json.loads((SMOKE_RUN_DIR / 'comparison_val_response.json').read_text())\n"
        "exam = json.loads((SMOKE_RUN_DIR / 'comparison_val_exam_score.json').read_text())\n"
        "\n"
        "df_resp = pd.DataFrame([\n"
        "    {\n"
        "        'target': 'response',\n"
        "        'model': r['name'],\n"
        "        'val_log_loss': r['val_metrics'].get('log_loss'),\n"
        "        'val_brier': r['val_metrics'].get('brier'),\n"
        "        'val_roc_auc': r['val_metrics'].get('roc_auc'),\n"
        "        'prevalence': r['val_metrics'].get('prevalence'),\n"
        "        'selected': r['name'] == sel['response']['name'],\n"
        "        'synthetic': True,\n"
        "        'domain': 'se_simulation',\n"
        "    }\n"
        "    for r in resp\n"
        "])\n"
        "df_exam = pd.DataFrame([\n"
        "    {\n"
        "        'target': 'exam_score',\n"
        "        'model': r['name'],\n"
        "        'val_mae': r['val_metrics'].get('mae'),\n"
        "        'val_rmse': r['val_metrics'].get('rmse'),\n"
        "        'y_mean': r['val_metrics'].get('y_mean'),\n"
        "        'selected': r['name'] == sel['exam_score']['name'],\n"
        "        'synthetic': True,\n"
        "        'domain': 'se_simulation',\n"
        "    }\n"
        "    for r in exam\n"
        "])\n"
        "display(df_resp)\n"
        "display(df_exam)\n"
        "print('All scenarios reported in scenario_sensitivity.json (not used to pick generator).')"
    ),
    md("## 8. Full data generation + training (gated)"),
    code(
        "# Set True only for the intended full synthetic run. Creates a NEW timestamped folder.\n"
        "RUN_FULL_TRAINING = False\n"
        "\n"
        "FULL_RUN_DIR = None\n"
        "if RUN_FULL_TRAINING:\n"
        "    full = run_training_and_validation(\n"
        "        DRIVE_ROOT,\n"
        "        mode='full',\n"
        "        master_seed=42,\n"
        "        run_full=True,\n"
        "        c4_root=C4_ROOT,\n"
        "    )\n"
        "    FULL_RUN_DIR = Path(full['run_dir'])\n"
        "    print('full run', FULL_RUN_DIR)\n"
        "    print('selection', json.dumps(full['selection'], indent=2))\n"
        "else:\n"
        "    print('Skipped full training (RUN_FULL_TRAINING=False)')"
    ),
    md("## 9. Final-test evaluation (gated; loads frozen selection — no config fallback)"),
    code(
        "from training_se_supervised.pipeline import run_final_evaluation, reload_run\n"
        "\n"
        "RUN_FINAL_EVALUATION = False\n"
        "# Point at a run that already has SELECTION_FROZEN.json + frozen_contract.json\n"
        "FINAL_TARGET_RUN = FULL_RUN_DIR or globals().get('SMOKE_RUN_DIR')\n"
        "\n"
        "if RUN_FINAL_EVALUATION:\n"
        "    require_symbol('FINAL_TARGET_RUN', FINAL_TARGET_RUN)\n"
        "    # Demonstrate reload after restart\n"
        "    reloaded = reload_run(FINAL_TARGET_RUN)\n"
        "    print('reloaded selection keys', list(reloaded['selection'].keys()))\n"
        "    final = run_final_evaluation(FINAL_TARGET_RUN, run_final=True)\n"
        "    print(json.dumps(final, indent=2))\n"
        "else:\n"
        "    print('Skipped final evaluation (RUN_FINAL_EVALUATION=False)')"
    ),
    md("## 10. Export reminder"),
    code(
        "from training_se_supervised.export_bundle import verify_manifest\n"
        "\n"
        "target = globals().get('FULL_RUN_DIR') or globals().get('SMOKE_RUN_DIR')\n"
        "if target is None:\n"
        "    print('No run directory in this session')\n"
        "else:\n"
        "    export_dir = Path(target) / 'export_bundle'\n"
        "    print('export_bundle', export_dir)\n"
        "    print(verify_manifest(export_dir))\n"
        "    print('Download export_bundle from Drive. Marks: domain=se_simulation, synthetic=true,')\n"
        "    print('simulation_only=true, real_exam_validation=false.')\n"
        "    print('Do NOT auto-wire into se-path-sim-v0 MaskablePPO dynamics.')"
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
