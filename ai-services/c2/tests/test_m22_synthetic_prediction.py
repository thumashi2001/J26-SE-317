"""M22.2: Test Suite for Synthetic Experimental Topic Prediction Backend.

Verifies:
1. Deterministic synthetic exam history construction.
2. Baselines A, B, C execution on synthetic sequence.
3. Walk-forward chronological evaluation (Precision@3, Recall@3, MRR, Brier Score).
4. FastAPI endpoint /topic-predictions with experimental_demo=true.
5. FastAPI endpoint /topic-predictions/experimental-demo.
6. Preservation of authentic gating when experimental_demo=false.
"""

import os
import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.synthetic_topic_prediction_service import SyntheticTopicPredictionService


@pytest.fixture
def auth_header():
    token = os.environ.get("C2_INTERNAL_TOKEN", "test_internal_token")
    return {"x-c2-internal-token": token}


@pytest.fixture
def test_client():
    return TestClient(app)


def test_synthetic_exam_history_construction():
    service = SyntheticTopicPredictionService()
    history = service.build_synthetic_exam_history("software_architecture")

    assert history["module_key"] == "software_architecture"
    assert history["module_name"] == "Software Architecture"
    assert len(history["topics"]) >= 5
    assert len(history["sessions"]) == 5

    years = [s["academic_year"] for s in history["sessions"]]
    assert years == [2019, 2020, 2021, 2022, 2023]

    for s in history["sessions"]:
        assert s["total_marks"] == 100
        assert len(s["topics_present"]) >= 3
        assert sum(s["topic_marks"].values()) == 100


def test_synthetic_demonstration_executes_all_three_baselines():
    service = SyntheticTopicPredictionService()
    result = service.generate_experimental_demonstration("software_architecture")

    assert result["provenance"] == "synthetic_experimental_demonstration"
    assert result["is_experimental_demonstration"] is True
    assert "ACADEMIC RESEARCH DEMONSTRATION ONLY" in result["disclaimer"]
    assert "awaiting_lecturer_verification" in result["academic_integrity_notice"]
    assert result["synthetic_session_count"] == 5

    methods = result["methods"]
    assert "baseline_a" in methods
    assert "baseline_b" in methods
    assert "baseline_c" in methods

    # Verify predictions format
    for m_key in ["baseline_a", "baseline_b", "baseline_c"]:
        preds = methods[m_key]["predictions"]
        assert len(preds) == 5
        ranks = [p["rank"] for p in preds]
        assert ranks == [1, 2, 3, 4, 5]
        for p in preds:
            assert "topic_id" in p
            assert "topic_name" in p
            assert 0.0 <= p["score"] <= 1.0


def test_chronological_walk_forward_evaluation_metrics():
    service = SyntheticTopicPredictionService()
    result = service.generate_experimental_demonstration("software_architecture")

    eval_data = result["chronological_evaluation"]
    assert eval_data["protocol"] == "walk_forward_chronological_split"
    assert eval_data["total_sessions"] == 5
    assert eval_data["eligible_evaluation_splits"] == 3
    assert len(eval_data["splits_evaluated"]) == 3

    # Check walk-forward splits isolate future from past
    for split in eval_data["splits_evaluated"]:
        assert split["test_academic_year"] not in split["train_academic_years"]
        assert all(yr < split["test_academic_year"] for yr in split["train_academic_years"])

    metrics = eval_data["comparative_metrics"]
    for m_key in ["historical_frequency", "recency_weighted_frequency", "regularized_statistical_model"]:
        summary = metrics[m_key]
        assert "mean_precision@3" in summary
        assert "mean_recall@3" in summary
        assert "mean_reciprocal_rank" in summary
        assert "mean_brier_score" in summary
        assert 0.0 <= summary["mean_precision@3"] <= 1.0
        assert 0.0 <= summary["mean_recall@3"] <= 1.0


def test_api_topic_predictions_with_experimental_demo_param(test_client, auth_header):
    response = test_client.get(
        "/topic-predictions?module_key=software_architecture&experimental_demo=true",
        headers=auth_header,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provenance"] == "synthetic_experimental_demonstration"
    assert data["module_key"] == "software_architecture"
    assert "baseline_a" in data["methods"]
    assert "baseline_b" in data["methods"]
    assert "baseline_c" in data["methods"]
    assert data["chronological_evaluation"]["eligible_evaluation_splits"] == 3


def test_api_dedicated_experimental_demo_route(test_client, auth_header):
    response = test_client.get(
        "/topic-predictions/experimental-demo?module_key=database_systems",
        headers=auth_header,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provenance"] == "synthetic_experimental_demonstration"
    assert data["module_key"] == "database_systems"
    assert data["module_name"] == "Database Systems"
    assert data["synthetic_session_count"] == 5


def test_api_authentic_route_preserves_gating(test_client, auth_header):
    """When experimental_demo=false, authentic zero verified labels must still gate predictions."""
    response = test_client.get(
        "/topic-predictions?module_key=software_architecture",
        headers=auth_header,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("prediction_ready") is False
    assert data.get("status") == "insufficient_evidence"
    assert data.get("future_exam_probabilities_available") is False
    assert data.get("provenance") != "synthetic_experimental_demonstration"
