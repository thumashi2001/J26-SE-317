"""Real-model checks for SE supervised simulation inference (no retrain)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from scripts.import_se_supervised_bundle import (
    BUNDLE_STEM,
    EXPECTED_MANIFEST_COUNT,
    import_bundle,
    verify_export_manifest,
)
from services.inference.se_supervised_loader import (
    EXPECTED_EXAM_NAME,
    EXPECTED_PASS_NAME,
    EXPECTED_RESPONSE_NAME,
    SeSupervisedLoadError,
    SeSupervisedPolicy,
    SeSupervisedValidationError,
)

ZIP_PATH = C4_ROOT / "runtime-artifacts" / f"{BUNDLE_STEM}.zip"
IMPORT_DIR = C4_ROOT / "runtime-artifacts" / "se_supervised_sim_v0" / BUNDLE_STEM


@pytest.fixture(scope="module")
def bundle_dir():
    if not ZIP_PATH.is_file() and not (IMPORT_DIR / "export_bundle" / "manifest.json").is_file():
        pytest.skip(f"Bundle ZIP/import missing: expected {ZIP_PATH}")
    if ZIP_PATH.is_file():
        return import_bundle(ZIP_PATH, C4_ROOT / "runtime-artifacts")
    verify_export_manifest(IMPORT_DIR)
    return IMPORT_DIR


@pytest.fixture(scope="module")
def policy(bundle_dir):
    p = SeSupervisedPolicy(bundle_dir)
    if not p.ready:
        pytest.fail(f"Failed to load supervised models: {p._error}")
    return p


def _sample_response_features(policy: SeSupervisedPolicy) -> dict[str, float]:
    row = {name: 0.0 for name in policy.feature_names_response}
    row["difficulty"] = 0.0
    row["topic_prior_attempts"] = 4.0
    row["topic_prior_correct"] = 2.0
    row["topic_prior_accuracy"] = 0.5
    row["topic_prior_streak"] = 1.0
    row["global_prior_attempts"] = 12.0
    row["global_prior_accuracy"] = 0.5
    row["learner_step"] = 12.0
    row["topic_oh_normalization"] = 1.0
    return row


def _sample_exam_features(policy: SeSupervisedPolicy) -> dict[str, float]:
    row = {name: 0.0 for name in policy.feature_names_exam}
    # Mild practice across a few topics
    for topic in (
        "usability_heuristics",
        "normalization",
        "risk_management",
        "agile_planning",
    ):
        row[f"topic_attempts_{topic}"] = 5.0
        row[f"topic_accuracy_{topic}"] = 0.6
    row["global_attempts"] = 20.0
    row["global_accuracy"] = 0.55
    row["mean_topic_accuracy"] = 0.6
    row["n_topics_practiced"] = 4.0
    row["practice_span_hours"] = 48.0
    row["last_topic_index"] = 3.0
    return row


def test_checksums_and_import(bundle_dir):
    verify_export_manifest(bundle_dir)
    man = json.loads((bundle_dir / "export_bundle" / "manifest.json").read_text(encoding="utf-8"))
    assert len(man) == EXPECTED_MANIFEST_COUNT


def test_selected_models_and_versions(policy, bundle_dir):
    assert policy.response_model_name == EXPECTED_RESPONSE_NAME
    assert policy.exam_model_name == EXPECTED_EXAM_NAME
    assert policy.pass_model_name == EXPECTED_PASS_NAME
    assert policy.pass_threshold == 0.55
    versions = policy.runtime_versions
    assert versions.get("protocol") == "se-supervised-sim-v0"
    assert versions.get("synthetic") is True
    assert versions.get("real_exam_validation") is False
    # Training pins recorded; local pins are not silently replaced.
    assert "sklearn" in versions and "numpy" in versions
    # ASSISTments / SE path trees untouched
    assert "se_path_sim_v0" not in str(bundle_dir)
    assert "maskable_ppo" not in str(bundle_dir)


def test_valid_predictions_all_three(policy):
    r = policy.predict_response(_sample_response_features(policy))
    assert r["selected_model"] == EXPECTED_RESPONSE_NAME
    assert 0.0 <= r["p_correct"] <= 1.0
    assert r["domain"] == "se_simulation"
    assert r["synthetic"] is True
    assert r["simulation_only"] is True
    assert r["real_exam_validation"] is False
    assert r["model_hash"]
    assert "accuracy" not in r  # do not describe AUC as accuracy

    e = policy.predict_exam_score(_sample_exam_features(policy))
    assert e["selected_model"] == EXPECTED_EXAM_NAME
    assert isinstance(e["exam_score_raw"], float)
    assert math.isfinite(e["exam_score_raw"])
    assert "exam_score_clipped_display" in e
    assert "clipping_applied" in e
    # If raw outside [0,1], clipping flag must be true and display bounded
    if e["exam_score_raw"] < 0 or e["exam_score_raw"] > 1:
        assert e["clipping_applied"] is True
    assert 0.0 <= e["exam_score_clipped_display"] <= 1.0

    p = policy.predict_pass(_sample_exam_features(policy))
    assert p["selected_model"] == EXPECTED_PASS_NAME
    assert 0.0 <= p["p_pass"] <= 1.0
    assert p["pass_threshold"] == 0.55


def test_save_load_consistency(policy):
    feats_r = _sample_response_features(policy)
    feats_e = _sample_exam_features(policy)
    a = policy.predict_response(feats_r)
    b = policy.predict_response(feats_r)
    assert a["p_correct"] == b["p_correct"]
    ea = policy.predict_exam_score(feats_e)
    eb = policy.predict_exam_score(feats_e)
    assert ea["exam_score_raw"] == eb["exam_score_raw"]
    pa = policy.predict_pass(feats_e)
    pb = policy.predict_pass(feats_e)
    assert pa["p_pass"] == pb["p_pass"]


def test_malformed_rejection(policy):
    with pytest.raises(SeSupervisedValidationError, match="Missing"):
        policy.predict_response({"difficulty": 0.1})
    bad = _sample_response_features(policy)
    bad["topic_prior_accuracy"] = float("nan")
    with pytest.raises(SeSupervisedValidationError, match="finite"):
        policy.predict_response(bad)
    bad2 = _sample_response_features(policy)
    bad2["topic_oh_normalization"] = 0.0  # none selected
    with pytest.raises(SeSupervisedValidationError, match="one-hot"):
        policy.predict_response(bad2)
    exam = _sample_exam_features(policy)
    exam["global_accuracy"] = 1.5
    with pytest.raises(SeSupervisedValidationError):
        policy.predict_exam_score(exam)


def test_missing_model_readiness_503_isolated(tmp_path, bundle_dir):
    empty = SeSupervisedPolicy(tmp_path / "missing_bundle")
    assert empty.ready is False
    info = empty.readiness()
    assert info["ready"] is False

    # Existing services still construct independently
    from services.inference.loader import MaskablePpoResearchPolicy
    from services.inference.se_sim_loader import SeSimulationPolicy

    # Constructing should not raise even if supervised is missing
    _ = MaskablePpoResearchPolicy()
    _ = SeSimulationPolicy()
    with pytest.raises(SeSupervisedLoadError):
        empty.predict_response(_sample_response_features(
            SeSupervisedPolicy(bundle_dir)
        ))


def test_http_endpoints(policy, bundle_dir, monkeypatch):
    monkeypatch.setenv("C4_SE_SUPERVISED_BUNDLE_DIR", str(bundle_dir))
    # Reload app modules with env pointing at imported bundle
    import importlib
    import app.main as main_mod

    importlib.reload(main_mod)
    client = TestClient(main_mod.app)

    ready = client.get("/v1/se-supervised-simulation/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["ready"] is True
    assert body["models"]["response"]["name"] == EXPECTED_RESPONSE_NAME

    r = client.post(
        "/v1/se-supervised-simulation/response",
        json={"features": _sample_response_features(policy), "protocol": "se-supervised-sim-v0"},
    )
    assert r.status_code == 200
    assert "p_correct" in r.json()

    e = client.post(
        "/v1/se-supervised-simulation/exam-score",
        json={"features": _sample_exam_features(policy)},
    )
    assert e.status_code == 200
    assert "exam_score_raw" in e.json()

    p = client.post(
        "/v1/se-supervised-simulation/pass",
        json={"features": _sample_exam_features(policy)},
    )
    assert p.status_code == 200
    assert p.json()["pass_threshold"] == 0.55

    bad = client.post(
        "/v1/se-supervised-simulation/response",
        json={"features": {"difficulty": 0.0}},
    )
    assert bad.status_code == 400

    # Regression: existing endpoint families still registered
    health = client.get("/health")
    assert health.status_code == 200
    h = health.json()
    assert "assistments_research_ready" in h
    assert "se_simulation_ready" in h
    assert "se_supervised_simulation_ready" in h

    # Research / SE path readiness must not 500 due to supervised presence
    # (503 is allowed if those bundles are absent locally)
    for path in ("/v1/research/catalogue", "/v1/se-simulation/ready"):
        resp = client.get(path)
        assert resp.status_code in (200, 503)


def test_http_missing_supervised_503(monkeypatch, tmp_path):
    monkeypatch.setenv("C4_SE_SUPERVISED_BUNDLE_DIR", str(tmp_path / "none"))
    import importlib
    import app.main as main_mod

    importlib.reload(main_mod)
    client = TestClient(main_mod.app)
    resp = client.get("/v1/se-supervised-simulation/ready")
    assert resp.status_code == 503
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["se_supervised_simulation_ready"] is False
