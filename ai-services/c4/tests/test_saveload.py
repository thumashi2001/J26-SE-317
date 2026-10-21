"""Response-model and (optional) SB3 save/load consistency."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training.config import EnvConfig
from training.dataset_assistments import normalise_interactions
from training.features import build_historical_features
from training.fixtures import build_fixture_dataframe
from training.pipeline import run_data_preparation
from training.response_model import ResponseModelBundle, fit_response_model
from training.simulator import Simulator, choose_top_skills
from training.splits import split_learners


def test_response_model_roundtrip(tmp_path):
    raw = build_fixture_dataframe()
    norm = normalise_interactions(raw)
    feats = build_historical_features(norm)
    bundle = fit_response_model(feats, seed=0)
    path = tmp_path / "rm.joblib"
    bundle.to_disk(str(path))
    loaded = ResponseModelBundle.from_disk(str(path))
    p1 = bundle.predict_proba(feats.head(10))
    p2 = loaded.predict_proba(feats.head(10))
    assert np.allclose(p1, p2)


def test_pipeline_fixture_end_to_end(tmp_path):
    from training.fixtures import write_default_fixture

    csv_path = write_default_fixture(tmp_path / "fix.csv")
    # Ensure banner column survives write
    out = tmp_path / "artifacts"
    result = run_data_preparation(csv_path=csv_path, output_dir=out, allow_download=False, top_k_skills=4)
    assert Path(result["output_dir"]).joinpath("response_model.joblib").exists()
    assert Path(result["output_dir"]).joinpath("quality_report.json").exists()


def test_sb3_smoke_save_load(tmp_path):
    pytest.importorskip("stable_baselines3")
    from training.export_policy import save_load_consistency_check
    from training.train_rl import train_dqn

    raw = build_fixture_dataframe()
    norm = normalise_interactions(raw)
    splits = split_learners(norm)
    train = splits["train"]
    feats = build_historical_features(train)
    bundle = fit_response_model(feats, seed=0)
    skills = choose_top_skills(train, top_k=4)
    cfg = EnvConfig(top_k_skills=4, max_episode_steps=8)
    sim = Simulator(bundle, skills, cfg)
    path = train_dqn(
        sim,
        cfg,
        tmp_path / "dqn",
        timesteps=512,
        seed=0,
        device="cpu",
        checkpoint_freq=10_000,
    )
    check = save_load_consistency_check(path, sim, cfg, algorithm="dqn")
    assert check["ok"] is True
