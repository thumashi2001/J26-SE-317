"""Confirmed se-path-multi-v1 reward defects stay historical. v2 pays clipped learning."""

from __future__ import annotations

import numpy as np

from training_se_v2.multi_action.contract import encode_action
from training_se_v2.multi_action.environment import MultiActionSimEnv
from training_se_v2.multi_action_v2.baselines import WeakestMulti
from training_se_v2.multi_action_v2.contract import N_TOPICS, action_mask, build_observation
from training_se_v2.multi_action_v2.environment import MultiActionSimEnvV2
from training_se_v2.multi_action_v2.objective import criterion_met
from training_se_v2.multi_action_v2.smoke_runner import _fixture


def _set_one(env, mastery: float) -> None:
    env.reset()
    env.state.mastery[:] = 0.0
    env.state.available[:] = 0.0
    env.state.mastery[0] = mastery
    env.state.available[0] = 1.0


def _reward(env, kind: str, mastery: float) -> tuple[float, dict]:
    _set_one(env, mastery)
    before = float(env.state.mastery[0])
    _obs, reward, _done, info = env.step(encode_action(kind, 0))
    info = dict(info)
    info["actual"] = float(env.state.mastery[0] - before)
    return float(reward), info


def test_v1_quiz_and_revision_pay_without_learning() -> None:
    env = MultiActionSimEnv(semester="Y3S1", seed=0)
    revision, revision_info = _reward(env, "revision", 1.0)
    quiz, quiz_info = _reward(env, "quiz", 1.0)
    practice, practice_info = _reward(env, "practice", 1.0)
    assert revision_info["actual"] == 0.0
    assert quiz_info["actual"] == 0.0
    assert practice_info["actual"] == 0.0
    assert revision == 0.04
    assert quiz in (0.5, -0.5)
    assert practice == 0.0


def test_v2_reward_matches_clipped_mastery_change() -> None:
    env = MultiActionSimEnvV2(semester="Y3S1", seed=0)
    for kind in ("practice", "revision", "quiz"):
        reward, info = _reward(env, kind, 1.0)
        assert info["actual"] == 0.0
        assert reward == 0.0
        assert info["components"]["correctness_bonus"] == 0.0
        assert info["components"]["learning_delta"] == 0.0
    reward, info = _reward(env, "revision", 0.99)
    assert abs(info["actual"] - 0.01) < 1e-6
    assert abs(reward - 0.01) < 1e-6
    quiz_reward, quiz_info = _reward(env, "quiz", 0.4)
    assert abs(quiz_reward - quiz_info["actual"]) < 1e-6
    assert quiz_reward not in (0.5, -0.5)


def test_v2_features_match_v1_layout() -> None:
    mastery = np.full(N_TOPICS, 0.4, dtype=np.float32)
    available = np.zeros(N_TOPICS, dtype=np.float32)
    available[:8] = 1.0
    obs = build_observation(
        mastery,
        available,
        elapsed_env_steps=0,
        recent_accuracy=None,
        engagement_completion_rate=None,
        exam_urgency=None,
    )
    from training_se_v2.multi_action.contract import build_observation as v1_obs

    historical = v1_obs(
        mastery,
        available,
        elapsed_env_steps=0,
        recent_accuracy=None,
        engagement_completion_rate=None,
        exam_urgency=None,
    )
    assert np.allclose(obs, historical)
    mask = action_mask(semester="Y3S1", available=available, mastery=mastery)
    assert not mask[3 * N_TOPICS :].any()
    _fixture()


def test_weakest_multi_uses_revision_and_quiz() -> None:
    mastery = np.full(N_TOPICS, 0.4, dtype=np.float32)
    available = np.zeros(N_TOPICS, dtype=np.float32)
    available[0] = 1.0
    mask = action_mask(semester="Y3S1", available=available, mastery=mastery)
    rule = WeakestMulti()
    kinds = []
    from training_se_v2.multi_action_v2.contract import decode_action

    for _ in range(3):
        kinds.append(decode_action(rule.action(mastery, mask))[0])
    assert kinds == ["practice", "revision", "quiz"]


def test_acceptance_rejects_high_return_low_learning() -> None:
    def block(mastery: float) -> dict:
        summary = {
            "mean_mastery_change": {"mean": mastery},
            "invalid_action_rate": {"mean": 0.0},
        }
        return summary

    validation = {"selected_seed": 1, "by_seed": {"1": {}}}
    for semester in ("Y3S1", "Y3S2"):
        validation["by_seed"]["1"][semester] = {
            "maskable_ppo": block(0.02),
            "weakest_practice": block(0.09),
            "recent_performance": block(0.09),
            "weakest_multi": block(0.08),
        }
    assert criterion_met(validation) is False
    for semester in ("Y3S1", "Y3S2"):
        validation["by_seed"]["1"][semester]["maskable_ppo"] = block(0.08)
    assert criterion_met(validation) is True
