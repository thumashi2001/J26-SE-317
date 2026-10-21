"""Local smoke: contract, baselines, train, reload, mask. Does not activate a product policy."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from catalogues.c1_practice_full_2026_10 import N_TOPICS, catalogue_hash

from .baselines import random_valid, weakest_practice
from .contract import (
    N_ACTIONS,
    OBS_DIM,
    PROTOCOL,
    action_mask,
    build_observation,
    decode_action,
)
from .environment import MultiActionSimEnv
from .smoke_policy import load_and_predict, train_smoke


def main() -> None:
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
    assert obs.shape == (OBS_DIM,)
    assert abs(float(obs[2 * N_TOPICS + 3]) - 0.5) < 1e-6
    assert float(obs[2 * N_TOPICS + 4]) == 0.0
    mask = action_mask(semester="Y3S1", available=available, mastery=mastery)
    assert mask.shape == (N_ACTIONS,)
    assert not mask[3 * N_TOPICS :].any(), "coding must be masked"
    assert mask.any()
    bad = action_mask(semester="Y2S1", available=available, mastery=mastery)
    assert not bad.any()
    action = weakest_practice(mastery, mask)
    kind, _topic = decode_action(action)
    assert kind == "practice"
    rng = np.random.default_rng(1)
    assert bool(mask[random_valid(mask, rng)])

    env = MultiActionSimEnv(seed=1)
    env.reset()
    _obs, reward, _done, info = env.step(int(np.flatnonzero(env.mask())[0]))
    assert info["synthetic"] is True
    assert np.isfinite(reward)

    out = Path(__file__).resolve().parents[2] / "experiments" / "smoke_runs" / "se_path_multi_v1"
    manifest = train_smoke(out, episodes=2, seed=1)
    assert manifest["activation_allowed"] is False
    assert manifest["protocol"] == PROTOCOL
    reloaded = load_and_predict(out, obs, mask)
    assert bool(mask[reloaded])

    fixture = {
        "protocol": PROTOCOL,
        "catalogue_hash": catalogue_hash(),
        "mastery": mastery.tolist(),
        "available": available.tolist(),
        "elapsed_env_steps": 0,
        "observation": [float(x) for x in obs.tolist()],
        "mask_prefix_len": int(mask.sum()),
        "coding_block_any": bool(mask[3 * N_TOPICS :].any()),
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
    }
    fix_path = Path(__file__).resolve().parent / "fixtures" / "obs_case.json"
    fix_path.parent.mkdir(parents=True, exist_ok=True)
    fix_path.write_text(json.dumps(fixture), encoding="utf-8")
    print("OK", PROTOCOL, "obs", OBS_DIM, "actions", N_ACTIONS, "smoke_return", manifest["mean_return"])


if __name__ == "__main__":
    main()
