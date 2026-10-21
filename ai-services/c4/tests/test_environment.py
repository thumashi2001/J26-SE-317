"""Environment API, Gymnasium checker, seeding, and invalid-action checks."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training.config import EnvConfig
from training.dataset_assistments import normalise_interactions
from training.environment import make_env
from training.features import build_historical_features
from training.fixtures import build_fixture_dataframe
from training.response_model import fit_response_model
from training.simulator import Simulator, choose_top_skills
from training.splits import split_learners


@pytest.fixture(scope="module")
def simulator():
    raw = build_fixture_dataframe()
    norm = normalise_interactions(raw)
    splits = split_learners(norm)
    train = splits["train"]
    feats = build_historical_features(train)
    bundle = fit_response_model(feats, seed=0)
    skills = choose_top_skills(train, top_k=4)
    return Simulator(bundle, skills, EnvConfig(top_k_skills=4, max_episode_steps=10))


def test_spaces_valid(simulator):
    env = make_env(simulator)
    assert env.observation_space.shape[0] == simulator.n_skills + 4
    assert env.action_space.n == len(simulator.skill_list)
    obs, info = env.reset(seed=0)
    assert obs.shape == env.observation_space.shape
    assert "action_mask" in info


def test_full_gymnasium_check_env(simulator):
    env = make_env(simulator, seed=0)
    check_env(env, skip_render_check=True)


def test_invalid_action_not_remapped(simulator):
    cfg = EnvConfig(top_k_skills=4, max_episode_steps=10, mastery_threshold=0.5)
    sim = Simulator(simulator.response_model, simulator.skill_list, cfg)
    env = make_env(sim, cfg)
    env.reset(seed=1)
    env._state.skill_mastery[:] = 0.9
    env._state.skill_mastery[0] = 0.1  # only action 0 available
    mask = env.available_action_mask()
    invalid = int(np.flatnonzero(~mask)[0])
    before = env._state.skill_mastery.copy()
    _obs2, reward, _term, _trunc, info2 = env.step(invalid)
    assert info2["invalid_action"] is True
    assert reward == env.cfg.invalid_action_penalty
    assert np.allclose(before, env._state.skill_mastery)


def test_reset_seed_reproducible(simulator):
    env1 = make_env(simulator, seed=7)
    env2 = make_env(simulator, seed=7)
    o1, _ = env1.reset(seed=7)
    o2, _ = env2.reset(seed=7)
    assert np.allclose(o1, o2)
    assert env1.np_random is env1._rng
    assert env2.np_random is env2._rng


def test_constructor_and_reset_seeding_use_np_random(simulator):
    env = make_env(simulator, seed=123)
    assert env._rng is env.np_random
    obs_a, _ = env.reset(seed=99)
    assert env._rng is env.np_random
    obs_b, _ = env.reset(seed=99)
    assert np.allclose(obs_a, obs_b)


def test_seeded_rollout_reproducible(simulator):
    from training.baselines import WeakestMasteryBaseline, rollout_policy

    def run_once():
        env = make_env(simulator, EnvConfig(top_k_skills=4, max_episode_steps=8), seed=0)
        policy = WeakestMasteryBaseline(simulator.n_skills)
        return rollout_policy(env, policy, episodes=3, seed=50)

    a = run_once()
    b = run_once()
    assert [r["return"] for r in a] == [r["return"] for r in b]
    assert [r["steps"] for r in a] == [r["steps"] for r in b]
