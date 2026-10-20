"""Tests against the real imported SE simulation MaskablePPO (seed 0)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from services.inference.se_sim_loader import (
    EXPECTED_DEMO_HASH,
    SeSimValidationError,
    SeSimulationPolicy,
    default_se_bundle_dir,
)
from training_se.catalogue import N_TOPICS, ORDERED_TOPICS, catalogue_hash
from training_se.observation import OBS_DIM, build_observation

BUNDLE = default_se_bundle_dir()
EXPORT = BUNDLE / "export_bundle"


def _obs_full(mastery_val: float = 0.35) -> tuple[list[float], list[bool]]:
    mastery = np.full(N_TOPICS, mastery_val, dtype=np.float32)
    avail = np.ones(N_TOPICS, dtype=np.float32)
    obs = build_observation(
        mastery,
        avail,
        elapsed_env_steps=2,
        max_episode_steps=30,
        prior_strength=0.4,
        mastery_threshold=0.8,
    )
    mask = ((avail > 0.5) & (mastery < 0.8)).astype(bool).tolist()
    return obs.tolist(), mask


@pytest.fixture(scope="module")
def se_policy() -> SeSimulationPolicy:
    if not EXPORT.is_dir():
        pytest.skip(f"SE bundle not imported at {BUNDLE}")
    p = SeSimulationPolicy(BUNDLE, seed=0)
    if not p.ready:
        pytest.skip(f"SE model not ready: {p.load_error}")
    return p


@pytest.fixture(scope="module")
def client(se_policy: SeSimulationPolicy):
    import app.main as main

    if not main.se_policy.ready:
        pytest.skip(f"App SE policy not ready: {main.se_policy.load_error}")
    return TestClient(main.app)


def test_import_checksums_and_demo_hash():
    from scripts.import_se_simulation_bundle import (
        verify_export_manifest,
        verify_models,
        verify_run_metadata,
    )

    if not BUNDLE.is_dir():
        pytest.skip("bundle not extracted")
    verify_export_manifest(BUNDLE)
    verify_run_metadata(BUNDLE)
    verify_models(BUNDLE)
    p = SeSimulationPolicy(BUNDLE, seed=0)
    assert p.ready
    assert p.seed == 0
    assert p.model_hash == EXPECTED_DEMO_HASH
    assert p.catalogue_hash_loaded == catalogue_hash()


def test_valid_prediction(se_policy: SeSimulationPolicy):
    obs, mask = _obs_full()
    out = se_policy.predict(
        observation=obs,
        action_mask=mask,
        protocol="se-path-sim-v0",
        catalogue_hash_client=catalogue_hash(),
    )
    assert 0 <= out.action_index < N_TOPICS
    assert out.topic_id == ORDERED_TOPICS[out.action_index]
    assert out.simulation_only is True
    assert out.synthetic is True
    assert out.domain == "se_simulation"
    assert out.model_hash == EXPECTED_DEMO_HASH
    assert "confidence" not in out.as_dict()
    assert "readiness" not in out.as_dict()


def test_masked_unavailable_never_selected(se_policy: SeSimulationPolicy):
    mastery = np.full(N_TOPICS, 0.4, dtype=np.float32)
    avail = np.zeros(N_TOPICS, dtype=np.float32)
    avail[2] = avail[5] = 1.0
    obs = build_observation(
        mastery, avail, elapsed_env_steps=1, max_episode_steps=30,
        prior_strength=0.4, mastery_threshold=0.8,
    ).tolist()
    mask = [False] * N_TOPICS
    mask[2] = mask[5] = True
    for _ in range(8):
        out = se_policy.predict(observation=obs, action_mask=mask)
        assert out.action_index in (2, 5)


def test_malformed_rejected(se_policy: SeSimulationPolicy):
    obs, mask = _obs_full()
    with pytest.raises(SeSimValidationError, match="shape"):
        se_policy.predict(observation=[0.1] * 10, action_mask=mask)
    bad = list(obs)
    bad[0] = float("nan")
    with pytest.raises(SeSimValidationError, match="NaN|Inf"):
        se_policy.predict(observation=bad, action_mask=mask)
    # unavailable with nonzero mastery
    mastery = np.zeros(N_TOPICS, dtype=np.float32)
    avail = np.zeros(N_TOPICS, dtype=np.float32)
    avail[0] = 1.0
    mastery[1] = 0.5  # unavailable but nonzero — builder zeros it; craft raw
    raw = build_observation(
        mastery, avail, elapsed_env_steps=0, max_episode_steps=30,
        prior_strength=0.4, mastery_threshold=0.8,
    ).copy()
    raw[1] = 0.5  # force inconsistent
    raw[12 + 1] = 0.0
    with pytest.raises(SeSimValidationError, match="unavailable"):
        se_policy.predict(observation=raw.tolist(), action_mask=[True] + [False] * 11)


def test_all_invalid_and_catalogue_mismatch(se_policy: SeSimulationPolicy):
    obs, _ = _obs_full()
    with pytest.raises(SeSimValidationError, match="all-invalid"):
        se_policy.predict(observation=obs, action_mask=[False] * N_TOPICS)
    with pytest.raises(SeSimValidationError, match="catalogue_hash"):
        se_policy.predict(
            observation=obs,
            action_mask=[True] * N_TOPICS,
            catalogue_hash_client="0" * 64,
        )
    # mask True on unavailable
    mastery = np.full(N_TOPICS, 0.3, dtype=np.float32)
    avail = np.zeros(N_TOPICS, dtype=np.float32)
    avail[0] = 1.0
    obs2 = build_observation(
        mastery, avail, elapsed_env_steps=0, max_episode_steps=30,
        prior_strength=0.4, mastery_threshold=0.8,
    ).tolist()
    mask = [True] * N_TOPICS  # illegal: others unavailable
    with pytest.raises(SeSimValidationError, match="unavailable"):
        se_policy.predict(observation=obs2, action_mask=mask)


def test_repeatability(se_policy: SeSimulationPolicy):
    obs, mask = _obs_full(0.42)
    a = se_policy.predict(observation=obs, action_mask=mask, deterministic=True)
    b = se_policy.predict(observation=obs, action_mask=mask, deterministic=True)
    assert a.action_index == b.action_index
    assert a.topic_id == b.topic_id


def test_http_se_and_research(client: TestClient):
    h = client.get("/health")
    assert h.status_code == 200
    body = h.json()
    assert body["se_simulation_ready"] is True

    r = client.get("/v1/se-simulation/ready")
    assert r.status_code == 200
    assert r.json()["seed"] == 0
    assert r.json()["model_hash"] == EXPECTED_DEMO_HASH

    obs, mask = _obs_full()
    pred = client.post(
        "/v1/se-simulation/predict",
        json={
            "observation": obs,
            "action_mask": mask,
            "protocol": "se-path-sim-v0",
            "catalogue_hash": catalogue_hash(),
        },
    )
    assert pred.status_code == 200
    data = pred.json()
    assert data["simulation_only"] is True
    assert data["topic_id"] in ORDERED_TOPICS
    print("ACTUAL_SE_PREDICTION", json.dumps(data))

    # Research readiness must still answer (may be 503 if ASSISTments bundle absent —
    # but endpoint must not crash)
    research = client.get("/ready")
    assert research.status_code in (200, 503)


def test_missing_se_model_503(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    p = SeSimulationPolicy(empty, seed=0, require_expected_hash=False)
    assert p.ready is False
    from fastapi.testclient import TestClient
    import app.main as main

    # Swap only SE policy for this check
    old = main.se_policy
    main.se_policy = p
    try:
        c = TestClient(main.app)
        assert c.get("/v1/se-simulation/ready").status_code == 503
        # health still ok
        assert c.get("/health").status_code == 200
    finally:
        main.se_policy = old
