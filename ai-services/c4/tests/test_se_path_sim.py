"""Focused tests for se-path-sim-v0 (synthetic SE simulation)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from training_se.baselines import (
    RandomValidBaseline,
    WeakestStoredMasteryV1SimBaseline,
)
from training_se.catalogue import N_TOPICS, ORDERED_TOPICS, catalogue_hash
from training_se.config import SeEnvConfig
from training_se.environment import SePathSimEnv, make_env
from training_se.evaluate import MaskablePpoAdapter
from training_se.export_bundle import export_se_bundle
from training_se.observation import OBS_DIM, availability_from_obs, build_observation, mastery_from_obs
from training_se.protocol import assert_eval_seeds_disjoint, final_test_episode_seed, val_episode_seed
from training_se.provenance import sha256_file
from training_se.simulator import SeSyntheticSimulator


def test_catalogue_order_and_hash_stable():
    assert N_TOPICS == 12
    assert ORDERED_TOPICS[0] == "usability_heuristics"
    assert ORDERED_TOPICS[-1] == "agile_planning"
    h1 = catalogue_hash()
    h2 = catalogue_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_observation_bounds_and_missing_vs_zero():
    mastery = np.zeros(N_TOPICS, dtype=np.float32)
    avail = np.zeros(N_TOPICS, dtype=np.float32)
    avail[0] = 1.0
    mastery[0] = 0.0  # genuine zero
    # topic 1 unavailable with latent junk cleared
    mastery[1] = 0.9
    obs = build_observation(
        mastery,
        avail,
        elapsed_env_steps=3,
        max_episode_steps=30,
        prior_strength=0.4,
        mastery_threshold=0.8,
    )
    assert obs.shape == (OBS_DIM,)
    assert obs[1] == 0.0  # unavailable mastery forced to 0
    assert availability_from_obs(obs)[0] == 1.0
    assert availability_from_obs(obs)[1] == 0.0
    assert mastery_from_obs(obs)[0] == 0.0


def test_seeded_reproducibility():
    cfg = SeEnvConfig()
    env1 = make_env(cfg, scenario="sim_val", seed=123)
    env2 = make_env(cfg, scenario="sim_val", seed=123)
    o1, _ = env1.reset(seed=999)
    o2, _ = env2.reset(seed=999)
    assert np.allclose(o1, o2)
    for _ in range(5):
        a = 0
        # pick first valid
        mask = env1.action_masks()
        a = int(np.flatnonzero(mask)[0])
        o1, r1, *_ = env1.step(a)
        o2, r2, *_ = env2.step(a)
        assert r1 == r2
        assert np.allclose(o1, o2)


def test_gain_reward_arithmetic_no_forgetting():
    sim = SeSyntheticSimulator(SeEnvConfig())
    rng = np.random.default_rng(0)
    st = sim.initial_state(rng, prior_strength=0.4, availability_rate=1.0)
    i = 0
    m0 = float(st.mastery[i])
    # Force correct by mocking: step until we get known gain via config
    cfg = SeEnvConfig()
    st2, info = sim.step_attempt(st, i, rng)
    assert info["selected_topic_gain"] == pytest.approx(
        (cfg.mastery_gain_correct if info["correct"] else cfg.mastery_gain_incorrect),
        rel=0,
        abs=1e-6,
    )
    # Other topics unchanged (no forgetting)
    for j in range(N_TOPICS):
        if j == i:
            continue
        assert st2.mastery[j] == st.mastery[j]
    assert st2.mastery[i] == pytest.approx(m0 + info["selected_topic_gain"], abs=1e-6)


def test_all_invalid_mask_and_unavailable():
    env = make_env(SeEnvConfig(), scenario="sim_train", seed=1)
    obs, info = env.reset(seed=7)
    # Force no available topics
    env._state.available[:] = 0.0
    mask = env.available_action_mask()
    assert not mask.any()
    obs2, reward, term, trunc, info2 = env.step(0)
    assert info2["invalid_action"] is True
    assert info2.get("all_invalid_mask") is True
    assert reward == SeEnvConfig().invalid_action_penalty


def test_mask_respecting_weakest_baseline():
    env = make_env(SeEnvConfig(), scenario="sim_val", seed=0)
    obs, info = env.reset(seed=11)
    policy = WeakestStoredMasteryV1SimBaseline()
    for _ in range(20):
        mask = info["action_mask"]
        a = policy.predict(obs, mask)
        assert mask[a]
        obs, _, term, trunc, info = env.step(a)
        if term or trunc:
            break


def test_eval_seeds_disjoint():
    assert_eval_seeds_disjoint([0, 1, 2], 20)
    assert val_episode_seed(0, 0) != final_test_episode_seed(0, 0)


def test_random_baseline_separate_rng_from_env():
    # Same baseline seed produces stable action choices for fixed masks
    b1 = RandomValidBaseline(seed=42)
    b2 = RandomValidBaseline(seed=42)
    mask = np.zeros(N_TOPICS, dtype=bool)
    mask[0] = mask[3] = mask[5] = True
    obs = np.zeros(OBS_DIM, dtype=np.float32)
    seq1 = [b1.predict(obs, mask) for _ in range(10)]
    seq2 = [b2.predict(obs, mask) for _ in range(10)]
    assert seq1 == seq2
    assert all(mask[a] for a in seq1)


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("sb3_contrib") is None,
    reason="sb3_contrib not installed",
)
def test_saveload_prediction_consistency(tmp_path: Path):
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.monitor import Monitor

    from training_se.train_rl import train_maskable_ppo

    out = tmp_path / "seed0"
    meta = train_maskable_ppo(out, timesteps=256, seed=0, device="cpu", checkpoint_freq=10_000)
    path = Path(meta["checkpoint"])
    assert path.is_file()
    env = Monitor(make_env(SeEnvConfig(), scenario="sim_val", seed=0))
    model = MaskablePPO.load(str(path), device="cpu")
    adapter = MaskablePpoAdapter(model)
    obs, info = env.reset(seed=100)
    a1 = adapter.predict(obs, info["action_mask"])
    model2 = MaskablePPO.load(str(path), device="cpu")
    a2 = int(model2.predict(obs, action_masks=info["action_mask"], deterministic=True)[0])
    assert a1 == a2
    assert info["action_mask"][a1]
    env.close()


def test_export_checksum(tmp_path: Path):
    cfg = SeEnvConfig()
    run = tmp_path / "run"
    run.mkdir()
    # fake empty selection
    selection = {"selected": "weakest_stored_mastery_v1_sim", "mean_val_return_by_algorithm": {}}
    export = export_se_bundle(
        export_dir=tmp_path / "export",
        run_dir=run,
        cfg=cfg,
        selected_algorithm="weakest_stored_mastery_v1_sim",
        model_paths={},
        selection=selection,
        include_final_test=False,
    )
    manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    for rel, expected in manifest["sha256"].items():
        if rel == "manifest.json":
            continue
        got = sha256_file(export / rel)
        assert got == expected, rel


def test_gymnasium_check_env():
    try:
        from gymnasium.utils.env_checker import check_env
    except ImportError:
        pytest.skip("gymnasium env_checker unavailable")
    env = SePathSimEnv(SeEnvConfig(), scenario="sim_train", seed=0)
    # skip render checks
    check_env(env, skip_render_check=True)
