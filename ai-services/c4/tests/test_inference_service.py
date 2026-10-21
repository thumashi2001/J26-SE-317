"""Tests against the real bundled MaskablePPO demo checkpoint (seed 2).

Software fixtures elsewhere demonstrate functionality, not SE model validity.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from services.inference.loader import (
    EXPECTED_DEMO_HASH,
    MaskablePpoResearchPolicy,
    PredictionValidationError,
    default_bundle_dir,
)

BUNDLE = default_bundle_dir()
CATALOGUE = json.loads((BUNDLE / "artifacts" / "skill_catalogue.json").read_text(encoding="utf-8"))
SKILL_IDS = [str(s) for s in CATALOGUE["skills"]]
N = len(SKILL_IDS)
OBS_DIM = N + 4


def _valid_obs(rng: np.random.Generator | None = None) -> list[float]:
    rng = rng or np.random.default_rng(0)
    mastery = rng.uniform(0.05, 0.75, size=N).astype(np.float32)
    mean_m = float(mastery.mean())
    frac = float((mastery >= 0.8).mean())
    step_frac = 0.1
    prior = 0.4
    return np.concatenate([mastery, [mean_m, frac, step_frac, prior]]).astype(np.float32).tolist()


def _full_mask() -> list[bool]:
    return [True] * N


@pytest.fixture(scope="module")
def policy() -> MaskablePpoResearchPolicy:
    if not BUNDLE.is_dir():
        pytest.skip(f"Research bundle not present at {BUNDLE}")
    p = MaskablePpoResearchPolicy(BUNDLE, seed=2)
    if not p.ready:
        pytest.skip(f"Model not ready: {p.load_error}")
    return p


@pytest.fixture(scope="module")
def client(policy: MaskablePpoResearchPolicy):
    # Import after policy check; app loads its own singleton — ensure same bundle.
    import app.main as main

    if not main.policy.ready:
        pytest.skip(f"App policy not ready: {main.policy.load_error}")
    return TestClient(main.app)


def test_bundle_manifest_checksums():
    from scripts.import_research_bundle import verify_manifest

    verify_manifest(BUNDLE)


def test_demo_checkpoint_hash_is_seed_2(policy: MaskablePpoResearchPolicy):
    assert policy.seed == 2
    assert policy.model_hash == EXPECTED_DEMO_HASH
    assert policy.skill_ids == SKILL_IDS


def test_valid_inference(policy: MaskablePpoResearchPolicy):
    obs = _valid_obs()
    mask = _full_mask()
    out = policy.predict(
        observation=obs,
        action_mask=mask,
        skill_ids=SKILL_IDS,
        protocol="c4-env-eval-v1.1",
    )
    assert 0 <= out.action_index < N
    assert out.skill_id == SKILL_IDS[out.action_index]
    assert out.algorithm == "maskable_ppo"
    assert out.seed == 2
    assert out.protocol == "c4-env-eval-v1.1"
    assert out.model_hash == EXPECTED_DEMO_HASH


def test_masked_action_never_selected(policy: MaskablePpoResearchPolicy):
    obs = _valid_obs(np.random.default_rng(7))
    # Only actions 4 and 5 valid
    mask = [False] * N
    mask[4] = True
    mask[5] = True
    for _ in range(10):
        out = policy.predict(observation=obs, action_mask=mask, deterministic=True)
        assert out.action_index in (4, 5)
        assert mask[out.action_index] is True


def test_all_invalid_mask_rejected(policy: MaskablePpoResearchPolicy):
    with pytest.raises(PredictionValidationError, match="all-invalid"):
        policy.predict(observation=_valid_obs(), action_mask=[False] * N)


def test_malformed_observation_rejected(policy: MaskablePpoResearchPolicy):
    with pytest.raises(PredictionValidationError, match="shape"):
        policy.predict(observation=[0.1, 0.2], action_mask=_full_mask())
    bad = _valid_obs()
    bad[0] = float("nan")
    with pytest.raises(PredictionValidationError, match="non-finite"):
        policy.predict(observation=bad, action_mask=_full_mask())
    bad2 = _valid_obs()
    bad2[1] = 1.5
    with pytest.raises(PredictionValidationError, match=r"\[0, 1\]"):
        policy.predict(observation=bad2, action_mask=_full_mask())


def test_incompatible_catalogue_rejected(policy: MaskablePpoResearchPolicy):
    wrong = list(SKILL_IDS)
    wrong[0] = "SE_TOPIC_FAKE"
    with pytest.raises(PredictionValidationError, match="catalogue"):
        policy.predict(
            observation=_valid_obs(),
            action_mask=_full_mask(),
            skill_ids=wrong,
        )


def test_repeatability_fixed_obs_mask(policy: MaskablePpoResearchPolicy):
    obs = _valid_obs(np.random.default_rng(42))
    mask = [False] * N
    mask[0] = True
    mask[3] = True
    mask[9] = True
    a = policy.predict(observation=obs, action_mask=mask, deterministic=True)
    b = policy.predict(observation=obs, action_mask=mask, deterministic=True)
    assert a.action_index == b.action_index
    assert a.skill_id == b.skill_id


def test_http_health_ready_predict(client: TestClient):
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"

    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["seed"] == 2
    assert body["model_hash"] == EXPECTED_DEMO_HASH

    obs = _valid_obs()
    resp = client.post(
        "/v1/research/predict",
        json={
            "observation": obs,
            "action_mask": _full_mask(),
            "skill_ids": SKILL_IDS,
            "protocol": "c4-env-eval-v1.1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skill_id"] in SKILL_IDS
    assert "confidence" not in data
    assert data["model_hash"] == EXPECTED_DEMO_HASH


def test_http_malformed_rejected(client: TestClient):
    resp = client.post(
        "/v1/research/predict",
        json={"observation": [1.0], "action_mask": _full_mask()},
    )
    assert resp.status_code == 400


def test_missing_model_not_ready(tmp_path: Path):
    empty = tmp_path / "empty_bundle"
    empty.mkdir()
    p = MaskablePpoResearchPolicy(empty, seed=2, require_expected_hash=False)
    assert p.ready is False
    assert p.load_error
    with pytest.raises(Exception):
        p.predict(observation=_valid_obs(), action_mask=_full_mask())
