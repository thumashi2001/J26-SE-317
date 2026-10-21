"""Baseline identity and distinct-behaviour checks."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training.baselines import (
    COMPARISON_ALGORITHMS,
    LowestPerformanceFirstBaseline,
    RandomValidBaseline,
    RuleBasedBaseline,
    WeakestMasteryBaseline,
    rollout_policy,
)
from training.config import DEFAULT_COMPARISON_ALGORITHMS, EnvConfig, TrainConfig, normalize_algorithm_key
from training.dataset_assistments import normalise_interactions
from training.environment import make_env
from training.features import build_historical_features
from training.fixtures import build_fixture_dataframe
from training.response_model import fit_response_model
from training.simulator import Simulator, choose_top_skills
from training.splits import split_learners


def _sim():
    raw = build_fixture_dataframe(n_learners=12, steps=30, seed=2)
    norm = normalise_interactions(raw)
    train = split_learners(norm)["train"]
    bundle = fit_response_model(build_historical_features(train), seed=0)
    skills = choose_top_skills(train, top_k=4)
    return Simulator(bundle, skills, EnvConfig(top_k_skills=4, max_episode_steps=12))


def test_legacy_alias_is_same_heuristic_not_independent():
    assert RuleBasedBaseline is WeakestMasteryBaseline
    assert issubclass(LowestPerformanceFirstBaseline, WeakestMasteryBaseline)
    assert normalize_algorithm_key("rule_based") == "weakest_mastery"
    assert normalize_algorithm_key("lowest_first") == "weakest_mastery"
    # Default comparison lists weakest_mastery once, not the alias pair.
    assert DEFAULT_COMPARISON_ALGORITHMS == COMPARISON_ALGORITHMS
    assert "recent_performance" in DEFAULT_COMPARISON_ALGORITHMS
    assert "lowest_first" not in DEFAULT_COMPARISON_ALGORITHMS
    assert "rule_based" not in DEFAULT_COMPARISON_ALGORITHMS
    cfg = TrainConfig(algorithms=("dqn", "rule_based", "lowest_first", "random_valid")).resolved()
    assert cfg.algorithms.count("weakest_mastery") == 1
    assert "lowest_first" not in cfg.algorithms


def test_weakest_mastery_picks_lowest_available():
    policy = WeakestMasteryBaseline(n_skills=4)
    obs = np.asarray([0.9, 0.2, 0.5, 0.8, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    mask = np.asarray([True, True, True, False], dtype=bool)
    assert policy.predict(obs, mask) == 1


def test_random_valid_is_seeded_and_distinct_from_weakest_mastery():
    sim = _sim()
    cfg = EnvConfig(top_k_skills=4, max_episode_steps=12)
    env_w = make_env(sim, cfg, seed=0)
    env_r = make_env(sim, cfg, seed=0)
    weak = WeakestMasteryBaseline(sim.n_skills)
    rand = RandomValidBaseline(seed=42)

    # Collect first actions on an identical fixed scenario seed.
    weak_actions = []
    rand_actions = []
    for ep in range(5):
        obs, info = env_w.reset(seed=100 + ep)
        weak_actions.append(weak.predict(obs, info["action_mask"]))
        obs2, info2 = env_r.reset(seed=100 + ep)
        assert np.allclose(obs, obs2)
        rand_actions.append(rand.predict(obs2, info2["action_mask"]))

    assert weak_actions != rand_actions

    # Same seed => same random-valid sequence.
    rand_a = RandomValidBaseline(seed=7)
    rand_b = RandomValidBaseline(seed=7)
    seq_a, seq_b = [], []
    env = make_env(sim, cfg, seed=0)
    for ep in range(4):
        obs, info = env.reset(seed=200 + ep)
        seq_a.append(rand_a.predict(obs, info["action_mask"]))
        seq_b.append(rand_b.predict(obs, info["action_mask"]))
    assert seq_a == seq_b


def test_rollout_returns_differ_on_fixed_scenario():
    sim = _sim()
    cfg = EnvConfig(top_k_skills=4, max_episode_steps=12)
    env1 = make_env(sim, cfg, seed=0)
    env2 = make_env(sim, cfg, seed=0)
    weak_rolls = rollout_policy(env1, WeakestMasteryBaseline(sim.n_skills), episodes=4, seed=10)
    rand_rolls = rollout_policy(env2, RandomValidBaseline(seed=99), episodes=4, seed=10)
    # Distinct policies on the same episode seeds should not be identical sequences.
    assert [r["return"] for r in weak_rolls] != [r["return"] for r in rand_rolls] or [
        r["steps"] for r in weak_rolls
    ] != [r["steps"] for r in rand_rolls]
