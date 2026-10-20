"""Regression tests for env timing, mastery metrics, seeds, recent-performance."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training.baselines import (
    RecentPerformanceBaseline,
    WeakestMasteryBaseline,
    rollout_policy,
)
from training.config import DEFAULT_COMPARISON_ALGORITHMS, EnvConfig
from training.dataset_assistments import normalise_interactions
from training.environment import make_env
from training.features import build_historical_features
from training.fixtures import build_fixture_dataframe
from training.protocol import (
    ENV_PROTOCOL_VERSION,
    assert_eval_seeds_disjoint,
    diag_episode_seed,
    final_test_episode_seed,
    protocol_manifest,
    val_episode_seed,
)
from training.response_model import fit_response_model
from training.simulator import Simulator, choose_top_skills
from training.splits import split_learners


@pytest.fixture(scope="module")
def sim():
    raw = build_fixture_dataframe(n_learners=12, steps=25, seed=3)
    norm = normalise_interactions(raw)
    train = split_learners(norm)["train"]
    bundle = fit_response_model(build_historical_features(train), seed=0)
    skills = choose_top_skills(train, top_k=4)
    cfg = EnvConfig(
        top_k_skills=4,
        max_episode_steps=20,
        mastery_threshold=0.5,
        assumed_forgetting_per_step=0.05,
        assumed_mastery_gain_correct=0.2,
        assumed_mastery_gain_incorrect=0.05,
    )
    return Simulator(bundle, skills, cfg)


def test_invalid_action_advances_elapsed_env_obs_not_learner_step(sim):
    """Regression: obs elapsed time must track _steps, not LearnerSimState.step."""
    env = make_env(sim, sim.env_config, seed=0)
    obs0, info0 = env.reset(seed=0)
    assert info0["elapsed_env_steps"] == 0
    assert info0["learner_interaction_count"] == 0
    k = sim.n_skills
    assert float(obs0[k + 2]) == 0.0  # elapsed_env_step_frac

    env._state.skill_mastery[:] = 0.9
    env._state.skill_mastery[0] = 0.1
    mask = env.available_action_mask()
    invalid = int(np.flatnonzero(~mask)[0])
    learner_before = int(env._state.step)

    obs1, _reward, _term, _trunc, info1 = env.step(invalid)
    assert info1["invalid_action"] is True
    assert info1["elapsed_env_steps"] == 1
    assert info1["learner_interaction_count"] == learner_before == 0
    # Observation step_frac must advance with environment clock (the pre-v1.1 bug).
    assert float(obs1[k + 2]) > float(obs0[k + 2])
    assert abs(float(obs1[k + 2]) - 1.0 / env.cfg.max_episode_steps) < 1e-6


def test_mastery_selected_vs_total_with_forgetting(sim):
    env = make_env(sim, sim.env_config, seed=1)
    obs, info = env.reset(seed=1)
    start_total = float(info["initial_total_mastery"])
    start_mean = float(info["initial_mean_mastery"])
    selected_sum = 0.0
    for _ in range(8):
        mask = info["action_mask"]
        action = 0 if mask[0] else int(np.flatnonzero(mask)[0])
        obs, _reward, term, trunc, info = env.step(action)
        if not info.get("invalid_action"):
            selected_sum += float(info["selected_skill_mastery_gain"])
        if term or trunc:
            break
    end_total = float(obs[: sim.n_skills].sum())
    end_mean = float(obs[: sim.n_skills].mean())
    total_delta = end_total - start_total
    mean_delta = end_mean - start_mean
    # Forgetting on non-selected skills => total/mean deltas diverge from selected-skill sum.
    assert sim.env_config.assumed_forgetting_per_step > 0
    assert not np.isclose(selected_sum, total_delta, atol=1e-6)
    rolls = rollout_policy(
        make_env(sim, sim.env_config, seed=2),
        WeakestMasteryBaseline(sim.n_skills),
        episodes=1,
        seed=2,
    )
    r0 = rolls[0]
    assert "selected_skill_mastery_gain_sum" in r0
    assert "total_mastery_delta_final_minus_initial" in r0
    assert "mean_mastery_delta_final_minus_initial" in r0
    assert isinstance(r0["mean_mastery_delta_final_minus_initial"], float)


def test_recent_performance_cold_start_and_distinct(sim):
    env = make_env(sim, sim.env_config, seed=0)
    policy = RecentPerformanceBaseline(sim.n_skills, window=3)
    policy.reset_episode()
    obs, info = env.reset(seed=5)
    # Cold-start: all untried -> lowest valid index
    a0 = policy.predict(obs, info["action_mask"])
    valid = list(np.flatnonzero(info["action_mask"][: sim.n_skills]))
    assert a0 == min(valid)

    # After observing strong performance on a0, prefer another skill if available.
    policy.observe_transition({"invalid_action": False, "action": a0, "correct": 1})
    policy.observe_transition({"invalid_action": False, "action": a0, "correct": 1})
    a1 = policy.predict(obs, info["action_mask"])
    if len(valid) > 1:
        assert a1 != a0 or a1 in valid

    weak = WeakestMasteryBaseline(sim.n_skills)
    # Different decision rules on a crafted obs
    obs2 = np.asarray([0.9, 0.1, 0.5, 0.8, 0.0, 0.0, 0.0, 0.4], dtype=np.float32)
    mask = np.ones(4, dtype=bool)
    # Give skill 1 perfect recent history, skill 0 none -> recent picks 0 (untried), weak picks 1
    rp = RecentPerformanceBaseline(4, window=3)
    rp.observe_transition({"invalid_action": False, "action": 1, "correct": 1})
    assert rp.predict(obs2, mask) == 0
    assert weak.predict(obs2, mask) == 1


def test_eval_seed_bands_disjoint():
    assert_eval_seeds_disjoint((0, 1, 2), 20)
    assert val_episode_seed(0, 0) != final_test_episode_seed(0, 0)
    assert diag_episode_seed(0, 0) != val_episode_seed(0, 0)
    assert ENV_PROTOCOL_VERSION.startswith("c4-env-eval-")
    man = protocol_manifest()
    assert "partial_observability" in man
    assert "hidden_from_policy_used_by_simulator" in man["partial_observability"]


def test_default_algorithms_include_recent_not_duplicate_alias():
    assert "recent_performance" in DEFAULT_COMPARISON_ALGORITHMS
    assert "lowest_first" not in DEFAULT_COMPARISON_ALGORITHMS
    assert "maskable_ppo" not in DEFAULT_COMPARISON_ALGORITHMS  # opt-in only
