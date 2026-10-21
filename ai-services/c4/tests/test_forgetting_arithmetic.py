"""Focused tests for mastery gain / forgetting arithmetic and time behaviour."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training.config import EnvConfig
from training.dataset_assistments import normalise_interactions
from training.environment import make_env
from training.features import build_historical_features
from training.fixtures import build_fixture_dataframe
from training.forgetting_audit import (
    DECLARED_SENSITIVITY_GRID,
    DYNAMICS_PROPOSAL_VERSION,
    display_summary_table,
    expected_arithmetic_for_config,
    locate_unique_maskable_checkpoint,
    new_sensitivity_output_dir,
    run_forgetting_sensitivity,
)
from training.response_model import fit_response_model
from training.simulator import Simulator, choose_top_skills
from training.splits import split_learners


def _sim(n_skills: int = 20, forget: float = 0.005) -> Simulator:
    raw = build_fixture_dataframe(n_learners=16, steps=40, seed=11)
    # Inflate skill diversity for a 20-skill catalogue.
    norm = normalise_interactions(raw)
    # Map primary skills onto 20 synthetic ids for arithmetic tests.
    skills = [f"S{i}" for i in range(n_skills)]
    train = split_learners(norm)["train"]
    # Relabel a cycling primary_skill so response model has enough variety.
    train = train.copy()
    train["primary_skill"] = [skills[i % n_skills] for i in range(len(train))]
    train["skill_tokens"] = [[s] for s in train["primary_skill"]]
    bundle = fit_response_model(build_historical_features(train), seed=0)
    cfg = EnvConfig(
        top_k_skills=n_skills,
        max_episode_steps=30,
        assumed_mastery_gain_correct=0.08,
        assumed_mastery_gain_incorrect=0.02,
        assumed_forgetting_per_step=forget,
        mastery_threshold=0.99,  # keep actions valid
    )
    return Simulator(bundle, skills, cfg)


def test_declared_grid_lists_current_and_no_forgetting_before_use():
    ids = [g["setting_id"] for g in DECLARED_SENSITIVITY_GRID]
    assert ids[0] == "v1_1_current_default"
    assert "no_forgetting_control" in ids
    assert DECLARED_SENSITIVITY_GRID[0]["hypothetical"] is False
    assert DYNAMICS_PROPOSAL_VERSION.startswith("c4-sim-dynamics-proposal-")


def test_expected_arithmetic_k20_matches_smoke_audit():
    cfg = EnvConfig()
    arith = expected_arithmetic_for_config(cfg, n_skills=20)
    assert arith.n_other == 19
    assert abs(arith.forgetting_mass_per_valid_step - 0.095) < 1e-12
    assert abs(arith.net_total_if_correct_interior - (-0.015)) < 1e-12
    assert abs(arith.net_total_if_incorrect_interior - (-0.075)) < 1e-12


def test_simulator_correct_and_incorrect_net_total_interior():
    sim = _sim(n_skills=20, forget=0.005)
    rng = np.random.default_rng(0)
    state = sim.initial_state(rng, prior_strength=0.5)
    # Interior mastery so clipping does not absorb gain/forget.
    state.skill_mastery[:] = 0.5

    # Force correct by temporarily patching predict.
    sim.predict_correct_prob = lambda st, idx: 1.0  # type: ignore[method-assign]
    before = state.skill_mastery.sum()
    new, info = sim.step(state, 0, rng)
    assert info["correct"] == 1
    assert abs(info["selected_skill_mastery_gain"] - 0.08) < 1e-6
    assert abs(info["net_total_mastery_delta_step"] - (-0.015)) < 1e-5
    assert abs(float(new.skill_mastery.sum() - before) - (-0.015)) < 1e-5

    state2 = new
    state2.skill_mastery[:] = 0.5
    sim.predict_correct_prob = lambda st, idx: 0.0  # type: ignore[method-assign]
    before2 = state2.skill_mastery.sum()
    new2, info2 = sim.step(state2, 1, rng)
    assert info2["correct"] == 0
    assert abs(info2["selected_skill_mastery_gain"] - 0.02) < 1e-6
    assert abs(info2["net_total_mastery_delta_step"] - (-0.075)) < 1e-5
    assert abs(float(new2.skill_mastery.sum() - before2) - (-0.075)) < 1e-5


def test_invalid_action_no_forgetting_but_elapsed_steps_advance():
    sim = _sim(n_skills=20, forget=0.005)
    env = make_env(sim, sim.env_config, seed=0)
    obs, info = env.reset(seed=0)
    env._state.skill_mastery[:] = 0.5
    # Make action 1 invalid by mastering it; keep 0 available.
    env.cfg.mastery_threshold = 0.4
    env._state.skill_mastery[1:] = 0.9
    env._state.skill_mastery[0] = 0.1
    before = env._state.skill_mastery.copy()
    learner_before = int(env._state.step)
    elapsed_before = int(info["elapsed_env_steps"])
    mask = env.available_action_mask()
    invalid = int(np.flatnonzero(~mask)[0])
    obs2, reward, term, trunc, info2 = env.step(invalid)
    assert info2["invalid_action"] is True
    assert np.allclose(before, env._state.skill_mastery)
    assert int(env._state.step) == learner_before
    assert int(info2["elapsed_env_steps"]) == elapsed_before + 1
    assert reward == env.cfg.invalid_action_penalty


def test_valid_practice_applies_forgetting_to_others_only():
    sim = _sim(n_skills=20, forget=0.005)
    env = make_env(sim, sim.env_config, seed=1)
    env.reset(seed=1)
    env._state.skill_mastery[:] = 0.5
    env.simulator.predict_correct_prob = lambda st, idx: 1.0  # type: ignore[method-assign]
    before = env._state.skill_mastery.copy()
    _obs, _r, _t, _u, info = env.step(0)
    assert not info.get("invalid_action")
    assert abs(env._state.skill_mastery[0] - (0.5 + 0.08)) < 1e-5
    assert np.allclose(env._state.skill_mastery[1:], before[1:] - 0.005, atol=1e-5)


def test_locate_unique_maskable_checkpoint(tmp_path):
    run = tmp_path / "train_smoke_demo"
    seed_dir = run / "seed_42" / "maskable_ppo"
    seed_dir.mkdir(parents=True)
    ckpt = seed_dir / "maskable_ppo_final.zip"
    ckpt.write_bytes(b"fake")
    found = locate_unique_maskable_checkpoint(run, train_seed=42)
    assert found == ckpt
    # Ambiguous
    (seed_dir / "nested").mkdir()
    (seed_dir / "nested" / "maskable_ppo_final.zip").write_bytes(b"x")
    with pytest.raises(RuntimeError, match="Ambiguous"):
        locate_unique_maskable_checkpoint(run, train_seed=42)
    # Missing seed folder
    with pytest.raises(FileNotFoundError, match="seed folder missing"):
        locate_unique_maskable_checkpoint(run, train_seed=99)


def test_sensitivity_runs_all_declared_settings(tmp_path):
    sim = _sim(n_skills=8, forget=0.005)
    out = new_sensitivity_output_dir(tmp_path / "metrics", prefix="forgetting_sensitivity_val")
    # Local fixture harness only — not Colab real-data results.
    report = run_forgetting_sensitivity(
        sim,
        sim.env_config,
        output_dir=out,
        train_seed=42,
        checkpoint_training_seed=42,
        episodes=2,
        methods=("weakest_mastery", "random_valid", "recent_performance"),
        maskable_ppo_checkpoint=None,
        print_grid_before_rollouts=False,
    )
    assert report["train_seed"] == 42
    assert report["checkpoint_training_seed"] == 42
    assert (out / "DECLARED_SENSITIVITY_GRID.json").exists()
    assert "v1_1_current_default" in report["settings"]
    assert "no_forgetting_control" in report["settings"]
    assert report["settings"]["time_like_forgetting_note_only_same_as_default"]["skipped_rollout"]
    rows = display_summary_table(out / "summary_table.json")
    assert isinstance(rows, list)
    for sid, block in report["settings"].items():
        if block.get("skipped_rollout"):
            continue
        assert set(block["methods"]) >= {
            "weakest_mastery",
            "random_valid",
            "recent_performance",
        }
        for method, payload in block["methods"].items():
            assert "metrics" in payload
            assert "return_mean" in payload["metrics"]
            assert "valid_practice_count_mean" in payload["metrics"]
            assert "total_mastery_delta_final_minus_initial_mean" in payload["metrics"]
