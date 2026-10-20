"""Short se-path-multi-v2 smoke. Does not run the 80_000-step training."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from catalogues.c1_practice_full_2026_10 import N_TOPICS, ORDERED_TOPICS, catalogue_hash

from .serving import MultiValidationError, assess_artifact, predict_with_model
from .baselines import WeakestMulti
from .contract import N_ACTIONS, OBS_DIM, PROTOCOL, action_mask, build_observation, encode_action
from .environment import MultiActionSimEnvV2
from .evaluate import load_model
from .objective import SMOKE_TIMESTEPS, TRAINING_REVISION, coverage_complete
from .train_rl import train_maskable_ppo


def _ceiling(kind: str) -> float:
    env = MultiActionSimEnvV2(semester="Y3S1", seed=0)
    env.reset()
    assert env.state is not None
    env.state.mastery[:] = 0.0
    env.state.available[:] = 0.0
    env.state.mastery[0] = 1.0
    env.state.available[0] = 1.0
    _obs, reward, _done, info = env.step(encode_action(kind, 0))
    if abs(float(info["actual_mastery_delta"])) > 1e-8:
        raise RuntimeError("ceiling case changed mastery")
    if abs(float(info["components"]["correctness_bonus"])) > 0.0:
        raise RuntimeError("correctness bonus returned")
    return float(reward)


def _supported_types() -> None:
    mastery = np.full(N_TOPICS, 0.4, dtype=np.float32)
    available = np.zeros(N_TOPICS, dtype=np.float32)
    available[:8] = 1.0
    mask = action_mask(semester="Y3S1", available=available, mastery=mastery)
    kinds = set()
    for action in np.flatnonzero(mask):
        from .contract import decode_action

        kind, _topic = decode_action(int(action))
        kinds.add(kind)
    if kinds != {"practice", "revision", "quiz"}:
        raise RuntimeError(f"expected practice, revision and quiz; got {kinds}")
    if mask[3 * N_TOPICS :].any():
        raise RuntimeError("coding mask is not empty")
    rule = WeakestMulti()
    seen = []
    for _ in range(3):
        action = rule.action(mastery, mask)
        from .contract import decode_action

        seen.append(decode_action(action)[0])
    if seen != ["practice", "revision", "quiz"]:
        raise RuntimeError(f"weakest_multi cycle was {seen}")


def _fixture() -> None:
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
    payload = {
        "protocol": PROTOCOL,
        "catalogue_hash": catalogue_hash(),
        "mastery": mastery.tolist(),
        "available": available.tolist(),
        "elapsed_env_steps": 0,
        "observation": [float(x) for x in obs.tolist()],
        "obs_dim": OBS_DIM,
        "n_actions": N_ACTIONS,
        "topic0": ORDERED_TOPICS[0],
    }
    path = Path(__file__).resolve().parent / "fixtures" / "obs_case.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    if obs.shape != (OBS_DIM,):
        raise RuntimeError("observation width changed")


def main() -> None:
    if _ceiling("revision") != 0.0 or _ceiling("quiz") != 0.0 or _ceiling("practice") != 0.0:
        raise SystemExit("clipped mastery was still rewarded")
    _supported_types()
    _fixture()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = (
        Path(__file__).resolve().parents[2]
        / "experiments"
        / "smoke_runs"
        / "se_path_multi_v2"
        / f"{TRAINING_REVISION}_{stamp}"
    )
    for seed in (0, 1, 2):
        folder = out / f"seed_{seed}"
        trained = train_maskable_ppo(folder, timesteps=SMOKE_TIMESTEPS, seed=seed)
        if trained["activation_allowed"] is not False:
            raise SystemExit("smoke training set activation_allowed")
        coverage = trained["semester_coverage"]
        if not coverage_complete(coverage):
            raise SystemExit(f"seed {seed} missed a semester: {coverage}")
        reloaded = load_model(folder / "maskable_ppo_final.zip")
        env = MultiActionSimEnvV2(semester="Y3S2" if seed % 2 == 0 else "Y3S1", seed=2 + seed)
        obs = env.reset()
        mask = env.mask()
        live = predict_with_model(trained["model"], obs, mask)
        loaded = predict_with_model(reloaded, obs, mask)
        if live["action_index"] != loaded["action_index"]:
            raise SystemExit(f"seed {seed} reload changed the action")
        if live["action_type"] not in ("practice", "revision", "quiz") or not mask[live["action_index"]]:
            raise SystemExit(f"seed {seed} selected an ineligible action")
        if assess_artifact(folder)["ready"]:
            raise SystemExit("smoke artifact was marked ready")
        del trained["model"]
        print(
            "coverage",
            "seed",
            seed,
            "Y3S1_episodes",
            coverage["Y3S1"]["episodes"],
            "Y3S1_steps",
            coverage["Y3S1"]["steps"],
            "Y3S2_episodes",
            coverage["Y3S2"]["episodes"],
            "Y3S2_steps",
            coverage["Y3S2"]["steps"],
        )
    empty = np.zeros(N_ACTIONS, dtype=bool)
    try:
        predict_with_model(reloaded, obs, empty)
    except MultiValidationError:
        pass
    else:
        raise SystemExit("all-invalid mask was accepted")
    print("OK", PROTOCOL, "obs", OBS_DIM, "actions", N_ACTIONS, "smoke_not_activated", TRAINING_REVISION)


if __name__ == "__main__":
    main()
