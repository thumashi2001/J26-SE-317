"""Export selected policy + preprocessing artifacts + model card fields."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import numpy as np

from .config import EnvConfig, ASSISTMENTS_OFFICIAL_PAGE
from .environment import make_env
from .paths import ensure_dir
from .provenance import utc_now, write_json
from .simulator import Simulator
from .train_rl import _versions


# Mapping guidance from C1 insights API (backend/src/modules/c1) to C4 state features.
C1_TO_C4_FEATURE_MAP = {
    "topics.<topic>.estimatedNow": {
        "c4_state_field": "skill_mastery[i] (scaled 0-1 from 0-100)",
        "status": "requires_domain_adaptation",
        "note": "C1 topics are SLIIT SE topics; ASSISTments skills are K-12 math. Do not rename math skills as SE topics.",
    },
    "topics.<topic>.confidence": {
        "c4_state_field": "optional reliability weight (not used in v0.1 state vector)",
        "status": "future",
    },
    "topics.<topic>.daysSincePractice": {
        "c4_state_field": "related to assumed forgetting; not directly observed in ASSISTments CSV",
        "status": "assumption",
    },
    "engagement.index": {
        "c4_state_field": "not in v0.1 observation; candidate context feature for later pilots",
        "status": "future",
    },
}


def export_bundle(
    *,
    export_dir: Path | str,
    simulator: Simulator,
    env_config: EnvConfig,
    selected_algorithm: str,
    model_path: str | Path | None,
    preprocessing_dir: Path | str,
    dataset_provenance: dict[str, Any],
    evaluation_summary: dict[str, Any],
    training_config: dict[str, Any],
) -> Path:
    out = ensure_dir(export_dir)
    # Copy preprocessing artifacts
    pre = Path(preprocessing_dir)
    for name in (
        "response_model.joblib",
        "quality_report.json",
        "split_meta.json",
        "skill_catalogue.json",
        "real_data_provenance.json",
        "response_metrics.json",
    ):
        src = pre / name
        if src.exists():
            shutil.copy2(src, out / name)

    env = make_env(simulator, env_config)
    action_catalogue = env.action_catalogue()
    state_schema = {
        "observation_vector": (
            [f"mastery::{s}" for s in simulator.skill_list]
            + ["mean_mastery", "frac_mastered", "step_frac", "prior_strength"]
        ),
        "dtype": "float32",
        "range": [0.0, 1.0],
        "scales": "mastery already in [0,1]; no additional observation scaler in v0.1",
    }

    if model_path and Path(model_path).exists():
        shutil.copy2(model_path, out / Path(model_path).name)

    manifest = {
        "created_at_utc": utc_now(),
        "selected_algorithm": selected_algorithm,
        "model_file": Path(model_path).name if model_path else None,
        "state_schema": state_schema,
        "action_catalogue": action_catalogue,
        "dependency_versions": _versions(),
        "training_config": training_config,
        "dataset_provenance": dataset_provenance,
        "evaluation_summary": evaluation_summary,
        "c1_feature_mapping": C1_TO_C4_FEATURE_MAP,
        "domain_limitations": [
            "Trained on ASSISTments 2009-2010 math Skill Builder interactions (see official page).",
            "Not validated for SLIIT Software Engineering learners.",
            "Simulated mastery gains use assumed transition parameters.",
            "Do not present mathematics skills as SE topics.",
            f"Cite dataset page: {ASSISTMENTS_OFFICIAL_PAGE}",
        ],
        "generator_version": simulator.assumptions().get("generator_version"),
    }
    write_json(out / "export_manifest.json", manifest)
    write_json(out / "action_catalogue.json", action_catalogue)
    write_json(out / "state_schema.json", state_schema)
    return out


def inference_example_source() -> str:
    return '''
from pathlib import Path
import json
import numpy as np
from stable_baselines3 import DQN, PPO
from training.environment import make_env
from training.response_model import ResponseModelBundle
from training.simulator import Simulator
from training.config import EnvConfig

export_dir = Path("exports/latest")
manifest = json.loads((export_dir / "export_manifest.json").read_text())
bundle = ResponseModelBundle.from_disk(export_dir / "response_model.joblib")
skills = [a["label"] for a in manifest["action_catalogue"] if a["kind"] == "assistments_skill_practice"]
sim = Simulator(bundle, skills, EnvConfig())
env = make_env(sim)
obs, info = env.reset(seed=0)
algo = manifest["selected_algorithm"]
model_file = export_dir / manifest["model_file"] if manifest["model_file"] else None
if algo in {"dqn", "ppo"} and model_file:
    model = PPO.load(model_file) if algo == "ppo" else DQN.load(model_file)
    action, _ = model.predict(obs, deterministic=True)
else:
    # baseline path omitted
    action = int(np.argmin(obs[:len(skills)]))
print("action", int(action), "mask", info["action_mask"])
'''.strip()


def save_load_consistency_check(
    model_path: Path,
    simulator: Simulator,
    env_config: EnvConfig,
    *,
    algorithm: str,
) -> dict[str, Any]:
    from stable_baselines3 import DQN, PPO

    env = make_env(simulator, env_config, seed=123)
    obs, _ = env.reset(seed=123)
    cls = PPO if algorithm == "ppo" else DQN
    m1 = cls.load(str(model_path))
    a1, _ = m1.predict(obs, deterministic=True)
    tmp = model_path.parent / "_reload_check.zip"
    m1.save(str(tmp))
    m2 = cls.load(str(tmp))
    a2, _ = m2.predict(obs, deterministic=True)
    tmp.unlink(missing_ok=True)
    ok = int(a1) == int(a2)
    return {"ok": ok, "action_before": int(a1), "action_after": int(a2)}
