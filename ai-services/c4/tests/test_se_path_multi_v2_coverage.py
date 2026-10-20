"""Dual-semester training schedule for se-path-multi-v2. Does not run 80_000 steps."""

from __future__ import annotations

import json

import numpy as np
import pytest

from catalogues.c1_practice_full_2026_10 import N_TOPICS, Y3S1_INDICES, Y3S2_INDICES
from training_se_v2.multi_action_v2.contract import N_ACTIONS, action_mask
from training_se_v2.multi_action_v2.evaluate import load_model
from training_se_v2.multi_action_v2.export_bundle import load_training_coverage
from training_se_v2.multi_action_v2.gym_env import MultiActionGymEnvV2
from training_se_v2.multi_action_v2.objective import (
    TEST_RANDOM_SEED,
    TRAINING_REVISION,
    VAL_RANDOM_SEED,
    coverage_balanced,
    coverage_complete,
    heldout_scenario_seed,
    training_episode_rng_seed,
    training_semester,
    val_scenario_seed,
)
from training_se_v2.multi_action_v2.serving import assess_artifact, predict_with_model
from training_se_v2.multi_action_v2.train_rl import train_maskable_ppo


def _first_valid(env: MultiActionGymEnvV2) -> int:
    return int(np.flatnonzero(env.action_masks())[0])


def test_each_seed_alternates_both_semesters():
    for seed in (0, 1, 2):
        env = MultiActionGymEnvV2(schedule_training=True, train_seed=seed, seed=seed)
        _obs, info = env.reset()
        assert info["semester"] == "Y3S1"
        assert training_semester(0) == "Y3S1"
        for _ in range(40):
            env.step(_first_valid(env))
        _obs, info = env.reset()
        assert info["semester"] == "Y3S2"
        env.step(_first_valid(env))
        assert env.coverage["Y3S1"]["episodes"] == 1
        assert env.coverage["Y3S1"]["steps"] == 40
        assert env.coverage["Y3S2"]["episodes"] == 1
        assert env.coverage["Y3S2"]["steps"] == 1


def test_observation_and_mask_follow_the_active_semester():
    for semester, foreign in (("Y3S1", Y3S2_INDICES), ("Y3S2", Y3S1_INDICES)):
        env = MultiActionGymEnvV2(semester=semester, seed=4, schedule_training=False)
        obs, info = env.reset(seed=val_scenario_seed(semester, 0))
        assert info["semester"] == semester
        mask = np.asarray(info["action_mask"])
        expected = action_mask(
            semester=semester,
            available=info["available"],
            mastery=info["mastery"],
        )
        assert np.array_equal(mask, expected)
        assert not mask[3 * N_TOPICS :].any()
        for index in foreign:
            assert obs[N_TOPICS + index] == 0.0
            assert not mask[index]
            assert not mask[N_TOPICS + index]
            assert not mask[2 * N_TOPICS + index]
        assert mask.shape == (N_ACTIONS,)


def test_seeded_resets_repeat():
    def episode_pair(seed: int):
        env = MultiActionGymEnvV2(schedule_training=True, train_seed=seed, seed=seed)
        first, info_first = env.reset()
        second, info_second = env.reset()
        return first, info_first["semester"], second, info_second["semester"]

    a = episode_pair(1)
    b = episode_pair(1)
    assert a[1] == b[1] == "Y3S1"
    assert a[3] == b[3] == "Y3S2"
    assert np.allclose(a[0], b[0])
    assert np.allclose(a[2], b[2])


def test_evaluation_semester_stays_fixed():
    env = MultiActionGymEnvV2(semester="Y3S2", seed=0, schedule_training=False)
    _obs, info = env.reset(seed=val_scenario_seed("Y3S2", 0))
    assert info["semester"] == "Y3S2"
    _obs, info = env.reset(seed=val_scenario_seed("Y3S2", 1))
    assert info["semester"] == "Y3S2"


def test_rng_streams_are_disjoint_and_validation_is_shared():
    train = {training_episode_rng_seed(seed, episode) for seed in (0, 1, 2) for episode in range(5_000)}
    validation = {val_scenario_seed(semester, episode) for semester in ("Y3S1", "Y3S2") for episode in range(20)}
    held_out = {heldout_scenario_seed(semester, episode) for semester in ("Y3S1", "Y3S2") for episode in range(20)}
    retired = {51_000 + seed * 100 + episode for seed in (0, 1, 2) for episode in range(20)}
    retired |= {71_000 + seed * 100 + episode for seed in (0, 1, 2) for episode in range(20)}
    assert val_scenario_seed("Y3S1", 0) == 81_000
    assert val_scenario_seed("Y3S2", 3) == 82_003
    assert heldout_scenario_seed("Y3S1", 0) == 91_000
    assert train.isdisjoint(validation)
    assert train.isdisjoint(held_out)
    assert validation.isdisjoint(held_out)
    assert train.isdisjoint(retired)
    assert validation.isdisjoint(retired)
    assert held_out.isdisjoint(retired)
    assert VAL_RANDOM_SEED not in train | validation | held_out | retired
    assert TEST_RANDOM_SEED not in train | validation | held_out | retired


def test_full_export_rejects_missing_semester_coverage(tmp_path):
    folder = tmp_path / "seed_1"
    folder.mkdir()
    (folder / "training_coverage.json").write_text(
        json.dumps(
            {
                "training_revision": TRAINING_REVISION,
                "semesters": {
                    "Y3S1": {"episodes": 0, "steps": 0},
                    "Y3S2": {"episodes": 1000, "steps": 40_000},
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="semester coverage"):
        load_training_coverage(folder)
    assert coverage_complete({"Y3S1": {"episodes": 1, "steps": 40}, "Y3S2": {"episodes": 1, "steps": 40}})
    assert not coverage_balanced({"Y3S1": {"episodes": 1, "steps": 40}, "Y3S2": {"episodes": 1, "steps": 40}})
    assert coverage_balanced(
        {"Y3S1": {"episodes": 500, "steps": 20_000}, "Y3S2": {"episodes": 500, "steps": 20_000}}
    )


def test_native_save_load_and_inactive_smoke(tmp_path):
    trained = train_maskable_ppo(tmp_path, timesteps=64, seed=1)
    assert trained["activation_allowed"] is False
    assert trained["training_revision"] == TRAINING_REVISION
    assert coverage_complete(trained["semester_coverage"])
    assert trained["semester_coverage"]["Y3S1"]["steps"] > 0
    assert trained["semester_coverage"]["Y3S2"]["steps"] > 0
    reloaded = load_model(tmp_path / "maskable_ppo_final.zip")
    env = MultiActionGymEnvV2(semester="Y3S1", seed=9, schedule_training=False)
    obs, info = env.reset(seed=81_000)
    live = predict_with_model(trained["model"], obs, info["action_mask"])
    loaded = predict_with_model(reloaded, obs, info["action_mask"])
    assert live["action_index"] == loaded["action_index"]
    assert not info["action_mask"][3 * N_TOPICS :].any()
    assert assess_artifact(tmp_path)["ready"] is False
