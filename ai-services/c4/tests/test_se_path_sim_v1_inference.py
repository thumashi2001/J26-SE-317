"""Isolated se-path-sim-v1 inference tests against the imported full-run export."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from catalogues.c1_practice_full_2026_10 import (  # noqa: E402
    N_TOPICS,
    ORDERED_TOPICS,
    Y3S2_INDICES,
    catalogue_hash,
    semester_eligibility_mask,
)
from services.inference.se_sim_v1_loader import (  # noqa: E402
    DEFAULT_DEMO_SEED,
    EXPECTED_CATALOGUE_HASH,
    EXPECTED_DEMO_HASH,
    SePathSimulationV1Policy,
    SeSimV1LoadError,
    SeSimV1ValidationError,
    default_se_path_v1_bundle_dir,
    select_demo_seed_from_selection_val,
)
from training_se_v1.observation import OBS_DIM, build_observation  # noqa: E402

BUNDLE = default_se_path_v1_bundle_dir()
EXPORT = BUNDLE / "export_bundle"


def _obs_for_semester(semester: str, mastery_val: float = 0.35):
    mastery = np.full(N_TOPICS, mastery_val, dtype=np.float32)
    avail = np.asarray(semester_eligibility_mask(semester), dtype=np.float32)
    # Zero mastery outside semester (unavailable)
    mastery = np.where(avail > 0.5, mastery, 0.0).astype(np.float32)
    obs = build_observation(
        mastery,
        avail,
        elapsed_env_steps=2,
        max_episode_steps=40,
        prior_strength=0.4,
        mastery_threshold=0.8,
    )
    semester_ok = avail > 0.5
    mask = (semester_ok & (mastery < 0.8)).astype(bool)
    if not mask.any() and semester_ok.any():
        mask = semester_ok.copy()
    return obs.tolist(), mask.tolist()


@pytest.fixture(scope="module")
def path_v1_policy() -> SePathSimulationV1Policy:
    if not EXPORT.is_dir():
        pytest.skip(f"SE path v1 bundle not imported at {BUNDLE}")
    p = SePathSimulationV1Policy(BUNDLE, seed=DEFAULT_DEMO_SEED)
    if not p.ready:
        pytest.skip(f"SE path v1 not ready: {p.load_error}")
    return p


@pytest.fixture(scope="module")
def client(path_v1_policy: SePathSimulationV1Policy):
    import app.main as main

    if not main.se_path_v1.ready:
        pytest.skip(f"App path v1 not ready: {main.se_path_v1.load_error}")
    return TestClient(main.app)


def test_manifest_contract_and_demo_selection():
    if not EXPORT.is_dir():
        pytest.skip("bundle missing")
    man = json.loads((EXPORT / "manifest.json").read_text(encoding="utf-8"))
    assert man["protocol"] == "se-path-sim-v1"
    assert man["catalogue_hash"] == EXPECTED_CATALOGUE_HASH
    assert man["synthetic"] is True
    assert man["domain"] == "se_simulation"
    cat = json.loads((EXPORT / "topic_catalogue.json").read_text(encoding="utf-8"))
    assert cat["n_topics"] == 46
    assert len(cat["y3s1_topics"]) == 28
    assert len(cat["y3s2_topics"]) == 18
    assert cat["sha256"] == catalogue_hash() == EXPECTED_CATALOGUE_HASH
    obs = json.loads((EXPORT / "observation_schema.json").read_text(encoding="utf-8"))
    assert obs["dim"] == OBS_DIM == 96
    assert obs["n_actions"] == 46
    sel = json.loads((EXPORT / "selection_val.json").read_text(encoding="utf-8"))
    seed, evidence = select_demo_seed_from_selection_val(sel)
    assert seed == DEFAULT_DEMO_SEED == 2
    assert evidence["selected_seed"] == 2
    p = SePathSimulationV1Policy(BUNDLE)
    assert p.ready
    assert p.seed == 2
    assert p.model_hash == EXPECTED_DEMO_HASH


def test_valid_prediction(path_v1_policy: SePathSimulationV1Policy):
    obs, mask = _obs_for_semester("Y3S1")
    out = path_v1_policy.predict(
        observation=obs,
        action_mask=mask,
        semester="Y3S1",
        protocol="se-path-sim-v1",
        catalogue_hash_client=catalogue_hash(),
    )
    assert 0 <= out.action_index < N_TOPICS
    assert out.topic_id == ORDERED_TOPICS[out.action_index]
    assert semester_eligibility_mask("Y3S1")[out.action_index]
    assert out.simulation_only is True
    assert out.synthetic is True
    assert out.domain == "se_simulation"
    assert out.protocol == "se-path-sim-v1"
    assert out.model_hash == EXPECTED_DEMO_HASH
    assert out.seed == 2


def test_semester_and_availability_masking(path_v1_policy: SePathSimulationV1Policy):
    obs, mask = _obs_for_semester("Y3S1")
    # Force-true on a Y3S2 index must be rejected
    bad = list(mask)
    for i in Y3S2_INDICES:
        bad[i] = True
        break
    with pytest.raises(SeSimV1ValidationError, match="not eligible"):
        path_v1_policy.predict(observation=obs, action_mask=bad, semester="Y3S1")

    # Valid Y3S2-only mask
    obs2, mask2 = _obs_for_semester("Y3S2")
    y3s2_ok = semester_eligibility_mask("Y3S2")
    for _ in range(5):
        out = path_v1_policy.predict(
            observation=obs2, action_mask=mask2, semester="Y3S2"
        )
        assert y3s2_ok[out.action_index] is True
        assert out.action_index in Y3S2_INDICES


def test_all_invalid_rejected(path_v1_policy: SePathSimulationV1Policy):
    obs, _ = _obs_for_semester("Y3S1")
    with pytest.raises(SeSimV1ValidationError, match="all-invalid"):
        path_v1_policy.predict(
            observation=obs, action_mask=[False] * N_TOPICS, semester="Y3S1"
        )


def test_malformed_observation_rejected(path_v1_policy: SePathSimulationV1Policy):
    obs, mask = _obs_for_semester("Y3S1")
    with pytest.raises(SeSimV1ValidationError, match="shape"):
        path_v1_policy.predict(
            observation=[0.1] * 10, action_mask=mask, semester="Y3S1"
        )
    bad = list(obs)
    bad[0] = float("nan")
    with pytest.raises(SeSimV1ValidationError, match="NaN|Inf"):
        path_v1_policy.predict(observation=bad, action_mask=mask, semester="Y3S1")
    with pytest.raises(SeSimV1ValidationError, match="catalogue_hash"):
        path_v1_policy.predict(
            observation=obs,
            action_mask=mask,
            semester="Y3S1",
            catalogue_hash_client="0" * 64,
        )


def test_missing_bundle_isolation(tmp_path: Path):
    p = SePathSimulationV1Policy(tmp_path / "missing", require_expected_hash=False)
    assert not p.ready
    assert p.load_error
    with pytest.raises(SeSimV1LoadError):
        obs, mask = _obs_for_semester("Y3S1")
        p.predict(observation=obs, action_mask=mask, semester="Y3S1")


def test_api_ready_and_predict(client: TestClient):
    r = client.get("/v1/se-path-simulation-v1/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["seed"] == 2
    assert body["model_hash"] == EXPECTED_DEMO_HASH
    cat = client.get("/v1/se-path-simulation-v1/catalogue")
    assert cat.status_code == 200
    assert cat.json()["obs_dim"] == 96
    obs, mask = _obs_for_semester("Y3S1")
    pred = client.post(
        "/v1/se-path-simulation-v1/predict",
        json={
            "observation": obs,
            "action_mask": mask,
            "semester": "Y3S1",
            "protocol": "se-path-sim-v1",
            "catalogue_hash": catalogue_hash(),
        },
    )
    assert pred.status_code == 200
    data = pred.json()
    assert data["protocol"] == "se-path-sim-v1"
    assert data["simulation_only"] is True


def test_v0_endpoints_unaffected(client: TestClient):
    # v0 ready may or may not be up depending on local import; must not 500
    r = client.get("/health")
    assert r.status_code == 200
    h = r.json()
    assert "se_path_simulation_v1_ready" in h
    assert "se_simulation_ready" in h
    # Wrong protocol on v1 must 400, not affect v0 routes existence
    obs, mask = _obs_for_semester("Y3S1")
    bad = client.post(
        "/v1/se-path-simulation-v1/predict",
        json={
            "observation": obs,
            "action_mask": mask,
            "semester": "Y3S1",
            "protocol": "se-path-sim-v0",
        },
    )
    assert bad.status_code == 400
