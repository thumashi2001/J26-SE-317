"""Isolated se-supervised-sim-v1 inference tests against the imported full-run export."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from catalogues.c1_practice_full_2026_10 import ORDERED_TOPICS, catalogue_hash  # noqa: E402
from services.inference.se_supervised_v1_loader import (  # noqa: E402
    EXPECTED_CATALOGUE_HASH,
    EXPECTED_EXAM_NAME,
    EXPECTED_PASS_NAME,
    EXPECTED_RESPONSE_NAME,
    SeSupervisedV1LoadError,
    SeSupervisedV1Policy,
    SeSupervisedV1ValidationError,
    default_se_supervised_v1_bundle_dir,
)

BUNDLE = default_se_supervised_v1_bundle_dir()
EXPORT = BUNDLE / "export_bundle"


@pytest.fixture(scope="module")
def policy():
    if not (EXPORT / "manifest.json").is_file():
        pytest.skip(f"Supervised v1 bundle missing at {BUNDLE}")
    p = SeSupervisedV1Policy(BUNDLE)
    if not p.ready:
        pytest.fail(f"Failed to load supervised v1: {p._error}")
    return p


@pytest.fixture(scope="module")
def client(policy):
    import app.main as main

    if not main.se_supervised_v1.ready:
        pytest.skip(f"App supervised v1 not ready: {main.se_supervised_v1._error}")
    return TestClient(main.app)


def _sample_response_features(policy: SeSupervisedV1Policy) -> dict[str, float]:
    row = {name: 0.0 for name in policy.feature_names_response}
    row["difficulty"] = 0.0
    row["topic_prior_attempts"] = 4.0
    row["topic_prior_correct"] = 2.0
    row["topic_prior_accuracy"] = 0.5
    row["topic_prior_streak"] = 1.0
    row["global_prior_attempts"] = 12.0
    row["global_prior_accuracy"] = 0.5
    row["learner_step"] = 12.0
    row[f"topic_oh_{ORDERED_TOPICS[0]}"] = 1.0
    return row


def _sample_exam_features(policy: SeSupervisedV1Policy) -> dict[str, float]:
    row = {name: 0.0 for name in policy.feature_names_exam}
    for topic in ORDERED_TOPICS[:4]:
        row[f"topic_attempts_{topic}"] = 5.0
        row[f"topic_accuracy_{topic}"] = 0.6
    row["global_attempts"] = 20.0
    row["global_accuracy"] = 0.55
    row["mean_topic_accuracy"] = 0.6
    row["n_topics_practiced"] = 4.0
    row["practice_span_hours"] = 48.0
    row["last_topic_index"] = 3.0
    return row


def test_manifest_contract(policy: SeSupervisedV1Policy):
    man = json.loads((EXPORT / "manifest.json").read_text(encoding="utf-8"))
    assert "models/response_selected.joblib" in man
    assert policy.response_model_name == EXPECTED_RESPONSE_NAME
    assert policy.exam_model_name == EXPECTED_EXAM_NAME
    assert policy.pass_model_name == EXPECTED_PASS_NAME
    assert policy.pass_threshold == 0.55
    assert policy.classification_prob_threshold == 0.5
    assert len(policy.feature_names_response) == 54
    assert len(policy.feature_names_exam) == 98
    assert policy.catalogue_hash_loaded == EXPECTED_CATALOGUE_HASH == catalogue_hash()
    markers = json.loads((EXPORT / "DOMAIN_MARKERS.json").read_text(encoding="utf-8"))
    assert markers["protocol"] == "se-supervised-sim-v1"
    assert markers["simulation_only"] is True
    assert markers["real_exam_validation"] is False


def test_valid_predictions(policy: SeSupervisedV1Policy):
    resp = policy.predict_response(_sample_response_features(policy))
    assert 0.0 <= resp["p_correct"] <= 1.0
    assert resp["protocol"] == "se-supervised-sim-v1"
    assert resp["simulation_only"] is True
    assert resp["real_exam_validation"] is False
    assert resp["selected_model"] == EXPECTED_RESPONSE_NAME

    exam = policy.predict_exam_score(_sample_exam_features(policy))
    assert "exam_score_raw" in exam
    assert "exam_score_clipped_display" in exam
    assert exam["real_exam_validation"] is False

    pas = policy.predict_pass(_sample_exam_features(policy))
    assert 0.0 <= pas["p_pass"] <= 1.0
    assert pas["pass_threshold"] == 0.55
    assert pas["classification_prob_threshold"] == 0.5


def test_malformed_features_rejected(policy: SeSupervisedV1Policy):
    feats = _sample_response_features(policy)
    del feats[next(iter(feats))]
    with pytest.raises(SeSupervisedV1ValidationError, match="Missing"):
        policy.predict_response(feats)
    with pytest.raises(SeSupervisedV1ValidationError, match="length|Missing"):
        policy.predict_response([0.1] * 10)
    bad = _sample_response_features(policy)
    bad["topic_prior_accuracy"] = float("nan")
    with pytest.raises(SeSupervisedV1ValidationError, match="finite"):
        policy.predict_response(bad)


def test_missing_bundle_isolation(tmp_path: Path):
    p = SeSupervisedV1Policy(tmp_path / "missing")
    assert not p.ready
    with pytest.raises(SeSupervisedV1LoadError):
        p.predict_response({})


def test_api_endpoints(client: TestClient, policy: SeSupervisedV1Policy):
    ready = client.get("/v1/se-supervised-simulation-v1/ready")
    assert ready.status_code == 200
    assert ready.json()["ready"] is True
    resp = client.post(
        "/v1/se-supervised-simulation-v1/response",
        json={
            "features": _sample_response_features(policy),
            "protocol": "se-supervised-sim-v1",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["p_correct"] is not None
    exam = client.post(
        "/v1/se-supervised-simulation-v1/exam-score",
        json={"features": _sample_exam_features(policy)},
    )
    assert exam.status_code == 200
    assert "exam_score_raw" in exam.json()
    pas = client.post(
        "/v1/se-supervised-simulation-v1/pass",
        json={"features": _sample_exam_features(policy)},
    )
    assert pas.status_code == 200
    assert pas.json()["pass_threshold"] == 0.55


def test_v0_supervised_route_still_present(client: TestClient):
    # Route exists; 503 is OK if v0 bundle missing, but not 404.
    r = client.get("/v1/se-supervised-simulation/ready")
    assert r.status_code in (200, 503)
