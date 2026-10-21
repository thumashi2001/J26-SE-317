"""One-shot helper to write the four Colab notebooks. Not used at runtime."""

from __future__ import annotations

import json
from pathlib import Path


def nb(cells):
    out = []
    for kind, text in cells:
        src = text.splitlines(keepends=True)
        if src and not src[-1].endswith("\n"):
            src[-1] += "\n"
        if kind == "md":
            out.append({"cell_type": "markdown", "metadata": {}, "source": src})
        else:
            out.append(
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": src,
                }
            )
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": out,
    }


def main() -> None:
    root = Path(__file__).resolve().parent

    nb1 = nb(
        [
            (
                "md",
                """# 01 — Data preparation (C4)

Beginner path: install packages → get C4 source into the runtime → load the **real** ASSISTments corrected CSV → quality report → learner splits → fit response model on **train only**.

**Expected outputs** (under your output/Drive folder):
- `artifacts/quality_report.json`
- `artifacts/real_data_provenance.json`
- `artifacts/split_meta.json`
- `artifacts/response_model.joblib`
- `artifacts/skill_catalogue.json`
- feature pickle files

This notebook does **not** train RL policies.""",
            ),
            (
                "md",
                """## Step 0 — Configuration

Edit these values before running other cells.""",
            ),
            (
                "code",
                """# === USER CONFIG ===
RUN_IN_COLAB = True  # set False for local Cursor/Jupyter
DRIVE_SUBDIR = "AdaptiveLearnSE/c4_runs"  # under Google Drive MyDrive
ALLOW_GDOWN = False  # True attempts Drive file id from the official ASSISTments page
# Path to CSV after manual upload, or None to search default locations
CSV_PATH = None  # e.g. "/content/skill_builder_data_corrected.csv"
TOP_K_SKILLS = 20
SEED = 42
SOURCE_MODE = "zip"  # "zip" | "github" | "local"
GITHUB_URL = "https://github.com/thumashi2001/J26-SE-317.git"
GITHUB_BRANCH = "feature/c4-adaptive-learning"
GITHUB_COMMIT = None  # set to a verified SHA when using github mode
""",
            ),
            (
                "md",
                """## Step 1 — Install training dependencies (run before project imports)""",
            ),
            (
                "code",
                """import sys
print(sys.executable, sys.version)
""",
            ),
            (
                "md",
                """## Step 2 — Obtain C4 source (ZIP recommended for unpushed work)""",
            ),
            (
                "code",
                """from pathlib import Path
import sys
import subprocess

C4_ROOT = None
if SOURCE_MODE == "local":
    C4_ROOT = Path("..").resolve()
elif RUN_IN_COLAB and SOURCE_MODE == "zip":
    from google.colab import files
    import zipfile
    print("Upload c4-source.zip (repo or ai-services/c4)...")
    up = files.upload()
    name = next(iter(up))
    dest = Path("/content/J26-SE-317")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(name) as zf:
        zf.extractall(dest)
    candidates = [dest / "ai-services" / "c4", dest]
    for child in dest.iterdir():
        if child.is_dir():
            candidates.append(child / "ai-services" / "c4")
            candidates.append(child)
    for c in candidates:
        if (c / "training").exists():
            C4_ROOT = c
            break
    if C4_ROOT is None:
        raise FileNotFoundError("Could not locate ai-services/c4 after ZIP extract")
elif RUN_IN_COLAB and SOURCE_MODE == "github":
    import shutil
    dest = Path("/content/J26-SE-317")
    if dest.exists():
        shutil.rmtree(dest)
    cmd = ["git", "clone", "--branch", GITHUB_BRANCH, "--single-branch", GITHUB_URL, str(dest)]
    subprocess.check_call(cmd)
    if GITHUB_COMMIT:
        subprocess.check_call(["git", "checkout", GITHUB_COMMIT], cwd=str(dest))
    C4_ROOT = dest / "ai-services" / "c4"
else:
    C4_ROOT = Path("..").resolve()

assert (C4_ROOT / "training").exists(), C4_ROOT
sys.path.insert(0, str(C4_ROOT))
print("C4_ROOT =", C4_ROOT)

req = C4_ROOT / "requirements-training.txt"
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(req)])
print("Dependencies installed from", req)
""",
            ),
            (
                "md",
                """## Step 3 — Output directories (Drive if available)""",
            ),
            (
                "code",
                """from training.paths import resolve_output_root, stage_dirs
from training.colab_bootstrap import mount_drive

if RUN_IN_COLAB:
    try:
        mount_drive()
    except Exception as e:
        print("Drive mount skipped/failed:", e)

OUT = resolve_output_root(DRIVE_SUBDIR if RUN_IN_COLAB else None, prefer_drive=RUN_IN_COLAB)
DIRS = stage_dirs(OUT)
ARTIFACTS = DIRS["artifacts"]
print("Output root:", OUT)
print("Artifacts:", ARTIFACTS)
""",
            ),
            (
                "md",
                """## Step 4 — Acquire ASSISTments corrected CSV

Official page: https://sites.google.com/site/assistmentsdata/home/2009-2010-assistment-data/skill-builder-data-2009-2010

Corrected Drive link from that page: https://drive.google.com/file/d/1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE/view?usp=sharing

If you need to upload manually in Colab, run the next cell.""",
            ),
            (
                "code",
                """# Optional manual CSV upload (Colab)
if RUN_IN_COLAB and CSV_PATH is None:
    from google.colab import files
    print("If the CSV is not already on disk, upload skill_builder_data_corrected.csv now (or cancel to skip).")
    try:
        up = files.upload()
        if up:
            CSV_PATH = list(up.keys())[0]
            print("Using uploaded", CSV_PATH)
    except Exception as e:
        print("Upload skipped:", e)
""",
            ),
            (
                "md",
                """## Step 5 — Run data preparation""",
            ),
            (
                "code",
                """from training.pipeline import run_data_preparation
from training.config import SplitConfig

result = run_data_preparation(
    csv_path=CSV_PATH,
    output_dir=ARTIFACTS,
    split_config=SplitConfig(seed=SEED),
    allow_download=ALLOW_GDOWN,
    top_k_skills=TOP_K_SKILLS,
    seed=SEED,
)
print("Done. Keys:", sorted(result.keys()))
print("Learners:", result["split_meta"]["n_learners"])
print("Response val metrics:", result["response_metrics"]["validation"])
print("IMPORTANT: test metrics are held out — do not retune on them.")
print(result["response_metrics"]["test_held_out"])
""",
            ),
            (
                "md",
                """## Step 6 — Quick peek at the quality report""",
            ),
            (
                "code",
                """import json
qr = json.loads((ARTIFACTS / "quality_report.json").read_text())
print("columns:", len(qr["available_columns"]))
print("learners:", qr["n_learners"], "interactions:", qr["n_normalised_interactions"])
print("multi-skill fraction:", qr["multi_skill"]["fraction"])
print("domain_warning:", qr["domain_warning"])
""",
            ),
        ]
    )

    nb2 = nb(
        [
            (
                "md",
                """# 02 — Simulator and Gymnasium environment

Loads **preprocessing artifacts from notebook 01** (does not refit them).

Builds the learner-response simulator, validates the environment, and writes **synthetic** trajectories with provenance.

**Expected outputs:**
- `synthetic/sim_train_trajectories.csv` (+ val/test)
- `synthetic/*_provenance.json`
- `synthetic/simulator_assumptions.json`
- `synthetic/action_catalogue.json`""",
            ),
            (
                "code",
                """# === USER CONFIG ===
RUN_IN_COLAB = True
DRIVE_SUBDIR = "AdaptiveLearnSE/c4_runs"
C4_ROOT = None  # defaults to parent of experiments/
""",
            ),
            (
                "code",
                """from pathlib import Path
import sys
import subprocess

if C4_ROOT is None:
    C4_ROOT = Path("..").resolve()
sys.path.insert(0, str(C4_ROOT))
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(C4_ROOT / "requirements-training.txt")])

from training.paths import resolve_output_root, stage_dirs
from training.colab_bootstrap import mount_drive
from training.config import EnvConfig
from training.pipeline import run_simulator_stage, load_simulator_from_artifacts, require_previous_stage
from training.environment import make_env
from gymnasium.utils.env_checker import check_env

if RUN_IN_COLAB:
    try:
        mount_drive()
    except Exception as e:
        print(e)

OUT = resolve_output_root(DRIVE_SUBDIR if RUN_IN_COLAB else None, prefer_drive=RUN_IN_COLAB)
DIRS = stage_dirs(OUT)
ARTIFACTS = require_previous_stage(
    DIRS["artifacts"] / "response_model.joblib",
    "01_data_preparation",
    "Run notebook 01 first.",
).parent
print("Artifacts:", ARTIFACTS)
""",
            ),
            (
                "code",
                """env_cfg = EnvConfig(include_simulation_only_actions=False)
sim_info = run_simulator_stage(ARTIFACTS, output_dir=DIRS["synthetic"], env_config=env_cfg, seed=42)
print(sim_info)

sim = load_simulator_from_artifacts(ARTIFACTS, env_cfg)
env = make_env(sim, env_cfg)
check_env(env, skip_render_check=True)
obs, info = env.reset(seed=0)
print("obs shape", obs.shape, "n_actions", env.action_space.n)
print("action catalogue sample", env.action_catalogue()[:3])
print("Fitted vs assumed:", sim.assumptions()["fitted_from_data"], list(sim.assumptions()["assumed_not_fitted"]))
""",
            ),
            (
                "md",
                """Synthetic files are **not** ASSISTments rows. Do not use them as evidence of SE learning gains.""",
            ),
        ]
    )

    nb3 = nb(
        [
            (
                "md",
                """# 03 — Train and compare (protocol c4-env-eval-v1.1)

Uses simulator artifacts from notebooks 01–02. **Reuse notebook 01 artifacts** after a code-only ZIP reload; do not refit the response model unless artifacts are missing.

Default comparison:
- `dqn` / `ppo` — vanilla SB3; **no** mask; penalties only
- `weakest_mastery` — lowest current mastery (masked)
- `random_valid` — seeded random valid (masked)
- `recent_performance` — lowest rolling in-episode accuracy (masked); cold-start → untried

Opt-in: add `maskable_ppo` for sb3-contrib MaskablePPO (masks in train **and** eval).

New runs write `train_*_c4-env-eval-v1.1_*` folders and **do not overwrite** historical metrics.
Scenario names only change `prior_strength` presets (not held-out real learners).

- `RUN_MODE = "smoke"` — short CPU run (safe default).
- `RUN_MODE = "full"` — longer training, multiple seeds. **Set manually; not auto-started.**

Optional: `training.diagnostics.run_checkpoint_diagnostics` for validation-only traces on old checkpoints.""",
            ),
            (
                "code",
                """# === USER CONFIG ===
RUN_IN_COLAB = True
DRIVE_SUBDIR = "AdaptiveLearnSE/c4_runs"
RUN_MODE = "smoke"  # change to "full" only when ready
DEVICE = "auto"  # auto -> cpu for small MLP policies; set "cuda" if desired
C4_ROOT = None
# Defaults: dqn, ppo, weakest_mastery, random_valid, recent_performance
# Opt-in mask-aware: TrainConfig(..., algorithms=(..., "maskable_ppo"))
""",
            ),
            (
                "code",
                """from pathlib import Path
import sys
import subprocess

if C4_ROOT is None:
    C4_ROOT = Path("..").resolve()
sys.path.insert(0, str(C4_ROOT))
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(C4_ROOT / "requirements-training.txt")])

from training.paths import resolve_output_root, stage_dirs
from training.colab_bootstrap import mount_drive
from training.config import EnvConfig, TrainConfig
from training.baselines import COMPARISON_LABELS, COMPARISON_NOTES
from training.pipeline import load_simulator_from_artifacts, require_previous_stage
from training.train_rl import run_training_comparison, resume_instructions

if RUN_IN_COLAB:
    try:
        mount_drive()
    except Exception as e:
        print(e)

OUT = resolve_output_root(DRIVE_SUBDIR if RUN_IN_COLAB else None, prefer_drive=RUN_IN_COLAB)
DIRS = stage_dirs(OUT)
ARTIFACTS = require_previous_stage(DIRS["artifacts"] / "response_model.joblib", "01", "Run notebook 01 once; reuse artifacts after code ZIP reload.").parent
require_previous_stage(DIRS["synthetic"] / "simulator_assumptions.json", "02", "Run notebook 02 (or reuse synthetic/).")

env_cfg = EnvConfig()
sim = load_simulator_from_artifacts(ARTIFACTS, env_cfg)
train_cfg = TrainConfig(mode=RUN_MODE, device=DEVICE)
resolved = train_cfg.resolved()
print("Resolved train config:", resolved)
print("Algorithms:", resolved.algorithms)
print("Labels:", {k: COMPARISON_LABELS[k] for k in resolved.algorithms})
print("Notes:", COMPARISON_NOTES)
print("Resume help:\\n", resume_instructions(DIRS["checkpoints"]))
""",
            ),
            (
                "code",
                """# Smoke by default. Full mode only if RUN_MODE="full".
# Writes a NEW train_* folder; does not overwrite previous smoke outputs.
results = run_training_comparison(sim, env_cfg, train_cfg, DIRS["root"])
print("Run dir:", results["run_dir"])
print("Validation selection:", results["selection"])
print("Do not interpret these as SLIIT SE gains. Numbers come from the simulator.")
print("Do not claim improvement vs prior smoke until you compare the new metrics explicitly.")
""",
            ),
        ]
    )

    nb4 = nb(
        [
            (
                "md",
                """# 04 — Evaluate (test scenarios) and export

Uses the **validation-selected** policy from notebook 03.
Runs reserved **sim_test** scenarios, sensitivity checks, export bundle, and save/load consistency.

Fill `MODEL_CARD_TEMPLATE.md` with real numbers only — never invent results.""",
            ),
            (
                "code",
                """# === USER CONFIG ===
RUN_IN_COLAB = True
DRIVE_SUBDIR = "AdaptiveLearnSE/c4_runs"
RUN_DIR = None  # path to train_smoke_... folder; if None, pick latest under output root
C4_ROOT = None
EVAL_EPISODES = 20
""",
            ),
            (
                "code",
                """from pathlib import Path
import sys
import subprocess
import json

if C4_ROOT is None:
    C4_ROOT = Path("..").resolve()
sys.path.insert(0, str(C4_ROOT))
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", str(C4_ROOT / "requirements-training.txt")])

from training.paths import resolve_output_root, stage_dirs
from training.colab_bootstrap import mount_drive
from training.config import EnvConfig
from training.pipeline import load_simulator_from_artifacts, require_previous_stage
from training.evaluate import evaluate_on_test, sensitivity_to_assumptions, save_evaluation
from training.export_policy import export_bundle, inference_example_source, save_load_consistency_check
from training.provenance import read_json

if RUN_IN_COLAB:
    try:
        mount_drive()
    except Exception as e:
        print(e)

OUT = resolve_output_root(DRIVE_SUBDIR if RUN_IN_COLAB else None, prefer_drive=RUN_IN_COLAB)
DIRS = stage_dirs(OUT)
ARTIFACTS = require_previous_stage(DIRS["artifacts"] / "response_model.joblib", "01", "Run notebook 01.").parent

if RUN_DIR is None:
    cands = sorted(OUT.glob("train_*"), key=lambda p: p.stat().st_mtime)
    if not cands:
        raise FileNotFoundError("No train_* run dir found. Run notebook 03 first.")
    RUN_DIR = cands[-1]
RUN_DIR = Path(RUN_DIR)
selection = read_json(RUN_DIR / "selection_val.json")
print("Using RUN_DIR", RUN_DIR)
print("Selection", selection)
""",
            ),
            (
                "code",
                """algo = selection.get("selected")
if not algo:
    raise RuntimeError("No algorithm selected in selection_val.json")

model_path = None
comp = read_json(RUN_DIR / "comparison_val.json")
seed_key = sorted(comp["seeds"].keys())[0]
payload = comp["seeds"][seed_key].get(algo, {})
model_path = payload.get("path")

env_cfg = EnvConfig()
sim = load_simulator_from_artifacts(ARTIFACTS, env_cfg)

test_report = evaluate_on_test(
    sim,
    env_cfg,
    selected_algorithm=algo,
    model_path=model_path,
    episodes=EVAL_EPISODES,
    seed=123,
    scenario="sim_test",
)
sens = sensitivity_to_assumptions(
    sim,
    env_cfg,
    policy_name=algo,
    model_path=model_path,
    episodes=max(5, EVAL_EPISODES // 2),
    seed=99,
)
report = {"test": test_report, "sensitivity": sens, "selection": selection}
save_evaluation(report, DIRS["metrics"] / "final_test_report.json")
print(json.dumps(test_report["summary"], indent=2))
print(test_report["disclaimer"])
""",
            ),
            (
                "code",
                """prov = read_json(ARTIFACTS / "real_data_provenance.json")
train_cfg = read_json(RUN_DIR / "train_config.json")
export_dir = export_bundle(
    export_dir=DIRS["exports"] / "latest",
    simulator=sim,
    env_config=env_cfg,
    selected_algorithm=algo,
    model_path=model_path,
    preprocessing_dir=ARTIFACTS,
    dataset_provenance=prov,
    evaluation_summary=report,
    training_config=train_cfg,
)
print("Exported to", export_dir)
if model_path and algo in {"dqn", "ppo"}:
    print("Save/load check", save_load_consistency_check(Path(model_path), sim, env_cfg, algorithm=algo))
print("\\nInference example:\\n")
print(inference_example_source())
print("\\nFill MODEL_CARD_TEMPLATE.md with the metrics above. Do not invent numbers.")
""",
            ),
        ]
    )

    for name, obj in [
        ("01_data_preparation.ipynb", nb1),
        ("02_simulator_and_environment.ipynb", nb2),
        ("03_train_and_compare.ipynb", nb3),
        ("04_evaluate_and_export.ipynb", nb4),
    ]:
        path = root / name
        path.write_text(json.dumps(obj, indent=1), encoding="utf-8")
        print("wrote", path)


if __name__ == "__main__":
    main()
