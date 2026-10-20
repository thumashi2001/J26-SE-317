"""Masking, observation, and short smoke for se-path-sim-v1 (no full training)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from catalogues.c1_practice_full_2026_10 import N_TOPICS, Y3S1_INDICES, Y3S2_INDICES
from training_se_v1.environment import make_env
from training_se_v1.observation import OBS_DIM, availability_from_obs, build_observation
from training_se_v1.protocol import PROTOCOL_VERSION, VAL_SCENARIOS, assert_eval_seeds_disjoint
from training_se_v1.baselines import (
    RandomValidBaseline,
    WeakestStoredMasteryV1SimBaseline,
)


def test_obs_dim_and_missing_vs_zero():
    assert OBS_DIM == 2 * 46 + 4 == 96
    mastery = np.zeros(N_TOPICS, dtype=np.float32)
    available = np.zeros(N_TOPICS, dtype=np.float32)
    available[0] = 1.0
    mastery[0] = 0.0  # genuine zero
    mastery[1] = 0.9  # would be missing because unavailable
    obs = build_observation(
        mastery,
        available,
        elapsed_env_steps=0,
        max_episode_steps=40,
        prior_strength=0.4,
        mastery_threshold=0.8,
    )
    assert obs.shape == (96,)
    assert obs[0] == 0.0 and obs[N_TOPICS + 0] == 1.0
    assert obs[1] == 0.0 and obs[N_TOPICS + 1] == 0.0


def test_semester_mask_excludes_other_semester():
    env = make_env(scenario="y3s1_sim_train", seed=0)
    obs, info = env.reset(seed=0)
    mask = info["action_mask"]
    assert mask.shape == (46,)
    # No Y3S2 index may be True
    for i in Y3S2_INDICES:
        assert mask[i] is False or mask[i] == False
    assert mask.any() or info.get("n_eligible_actions", 0) >= 0
    env.close()


def test_y3s2_scenario_masks():
    env = make_env(scenario="y3s2_sim_val", seed=1)
    _, info = env.reset(seed=1)
    mask = info["action_mask"]
    for i in Y3S1_INDICES:
        assert not bool(mask[i])
    env.close()


def test_no_eligible_actions_safe():
    env = make_env(scenario="y3s1_sim_train", seed=2)
    obs, info = env.reset(seed=2)
    # Force empty mask by clearing availability
    env._state.available[:] = 0.0
    mask = env.available_action_mask()
    assert not mask.any()
    obs2, reward, terminated, truncated, info2 = env.step(0)
    assert info2["invalid_action"] is True
    assert info2.get("no_eligible_actions") is True
    assert terminated is True
    assert reward == env.cfg.invalid_action_penalty
    env.close()


def test_baseline_respects_mask():
    env = make_env(scenario="y3s1_sim_train", seed=3)
    obs, info = env.reset(seed=3)
    mask = info["action_mask"]
    a = WeakestStoredMasteryV1SimBaseline().predict(obs, mask)
    if mask.any():
        assert bool(mask[a])
    b = RandomValidBaseline(seed=99).predict(obs, mask)
    if mask.any():
        assert bool(mask[b])
    env.close()


def test_short_rollout_smoke():
    env = make_env(scenario="y3s1_sim_train", seed=4)
    obs, info = env.reset(seed=4)
    policy = WeakestStoredMasteryV1SimBaseline()
    for _ in range(5):
        mask = info["action_mask"]
        action = policy.predict(obs, mask)
        obs, reward, term, trunc, info = env.step(action)
        assert np.isfinite(reward)
        if term or trunc:
            break
    env.close()


def test_eval_seeds_disjoint():
    assert_eval_seeds_disjoint([0, 1, 2], 10)


def test_val_scenarios_both_semesters():
    assert "y3s1_sim_val" in VAL_SCENARIOS
    assert "y3s2_sim_val" in VAL_SCENARIOS


def test_v0_inference_protocol_unchanged():
    """Existing v0 package still declares se-path-sim-v0."""
    from training_se.protocol import PROTOCOL_VERSION as V0
    from training_se.observation import OBS_DIM as V0_DIM
    from training_se.catalogue import N_TOPICS as V0_N

    assert V0 == "se-path-sim-v0"
    assert V0_N == 12
    assert V0_DIM == 28
    assert PROTOCOL_VERSION == "se-path-sim-v1"


def test_maskable_ppo_tiny_learn_optional(tmp_path):
    """Optional tiny learn + save/load if deps present — not full training."""
    import importlib.util

    if importlib.util.find_spec("sb3_contrib") is None:
        pytest.skip("sb3-contrib not installed")
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.monitor import Monitor

    env = Monitor(make_env(scenario="y3s1_sim_train", seed=0))
    model = MaskablePPO(
        "MlpPolicy",
        env,
        n_steps=64,
        batch_size=32,
        n_epochs=1,
        verbose=0,
        seed=0,
        device="cpu",
    )
    model.learn(total_timesteps=128, use_masking=True)
    obs, _ = env.reset()
    action, _ = model.predict(
        obs, action_masks=env.unwrapped.action_masks(), deterministic=True
    )
    assert 0 <= int(action) < 46
    save_path = tmp_path / "tiny_maskable.zip"
    model.save(str(save_path))
    loaded = MaskablePPO.load(str(save_path), device="cpu")
    action2, _ = loaded.predict(
        obs, action_masks=env.unwrapped.action_masks(), deterministic=True
    )
    assert int(action) == int(action2)
    env.close()
