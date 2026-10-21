"""High-level pipeline stages used by notebooks and tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .config import EnvConfig, SplitConfig, DEFAULT_TOP_K_SKILLS
from .data_quality import build_quality_report, save_quality_report
from .dataset_assistments import (
    load_assistments_csv,
    normalise_interactions,
    resolve_csv_path,
    save_provenance_for_csv,
)
from .features import assert_no_current_outcome_leakage, build_historical_features
from .paths import ensure_dir, processed_dir, require_path
from .provenance import read_json, write_json
from .response_model import evaluate_response_model, fit_response_model
from .environment import make_env
from .simulator import Simulator, choose_top_skills
from .splits import drop_meta, split_learners
from .synthetic import write_synthetic_splits


def run_data_preparation(
    *,
    csv_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    split_config: SplitConfig | None = None,
    allow_download: bool = False,
    top_k_skills: int = DEFAULT_TOP_K_SKILLS,
    seed: int = 42,
) -> dict[str, Any]:
    """Stage 1: load real CSV, quality report, learner splits, fit response model on train only."""
    out = ensure_dir(output_dir or processed_dir())
    path = resolve_csv_path(csv_path, allow_download=allow_download)
    raw = load_assistments_csv(path)
    normalised = normalise_interactions(raw)
    report = build_quality_report(raw, normalised)
    save_quality_report(report, str(out / "quality_report.json"))
    prov = save_provenance_for_csv(path, out / "real_data_provenance.json")

    splits = split_learners(normalised, split_config or SplitConfig(seed=seed))
    meta = splits["_meta"]
    write_json(out / "split_meta.json", meta)
    frames = drop_meta(splits)
    for name, df in frames.items():
        df.to_pickle(out / f"interactions_{name}.pkl")

    train_feat = build_historical_features(frames["train"])
    val_feat = build_historical_features(frames["validation"])
    test_feat = build_historical_features(frames["test"])
    assert_no_current_outcome_leakage(train_feat)
    train_feat.to_pickle(out / "features_train.pkl")
    val_feat.to_pickle(out / "features_validation.pkl")
    test_feat.to_pickle(out / "features_test.pkl")

    bundle = fit_response_model(train_feat, val_feat, seed=seed)
    bundle.to_disk(str(out / "response_model.joblib"))
    test_metrics = evaluate_response_model(bundle, test_feat)
    write_json(
        out / "response_metrics.json",
        {
            "train": bundle.train_metrics,
            "validation": bundle.val_metrics,
            "test_held_out": test_metrics,
            "fitted_parameters": bundle.fitted_parameters,
            "assumed_parameters": bundle.assumed_parameters,
            "disclaimer": (
                "Predicted correctness is not measured causal knowledge gain. "
                "Test metrics reserved for final reporting; do not retune on test."
            ),
        },
    )

    skills = choose_top_skills(frames["train"], top_k_skills)
    write_json(out / "skill_catalogue.json", {"skills": skills, "top_k": top_k_skills, "source_split": "train"})

    return {
        "output_dir": str(out),
        "csv_path": str(path),
        "quality_report": report,
        "split_meta": meta,
        "skill_catalogue": skills,
        "provenance": prov,
        "response_metrics": {
            "train": bundle.train_metrics,
            "validation": bundle.val_metrics,
            "test_held_out": test_metrics,
        },
    }


def load_simulator_from_artifacts(
    artifacts_dir: str | Path,
    env_config: EnvConfig | None = None,
) -> Simulator:
    from .response_model import ResponseModelBundle

    art = Path(artifacts_dir)
    require_path(art / "response_model.joblib", "Run notebook 01_data_preparation first.")
    require_path(art / "skill_catalogue.json", "Run notebook 01_data_preparation first.")
    bundle = ResponseModelBundle.from_disk(str(art / "response_model.joblib"))
    skills = read_json(art / "skill_catalogue.json")["skills"]
    parent = None
    prov_path = art / "real_data_provenance.json"
    if prov_path.exists():
        parent = read_json(prov_path).get("sha256")
    return Simulator(
        response_model=bundle,
        skill_list=list(skills),
        env_config=env_config or EnvConfig(top_k_skills=len(skills)),
        parent_real_checksum=parent,
    )


def run_simulator_stage(
    artifacts_dir: str | Path,
    *,
    output_dir: str | Path | None = None,
    env_config: EnvConfig | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Stage 2: build env, generate synthetic trajectories, persist assumptions."""
    art = Path(artifacts_dir)
    cfg = env_config or EnvConfig()
    sim = load_simulator_from_artifacts(art, cfg)
    out = ensure_dir(output_dir or (art.parent / "synthetic"))
    paths = write_synthetic_splits(sim, cfg, out, seed=seed)
    write_json(out / "simulator_assumptions.json", sim.assumptions())
    write_json(out / "action_catalogue.json", make_env(sim, cfg).action_catalogue())
    return {"sim_output_dir": str(out), "trajectory_paths": {k: str(v) for k, v in paths.items()}}


def require_previous_stage(path: Path | str, stage_name: str, hint: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Missing outputs from {stage_name}: {p}\nAction: {hint}"
        )
    return p
