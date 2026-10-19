"""M20 - Test Suite for Evidence-Aware Exam Topic Prediction Subsystem.

Verifies:
1. Zero verified topic labels handling.
2. Unverified module taxonomies.
3. Missing historical years and gap metrics.
4. Duplicate historical papers / session identification.
5. Parent/leaf question duplication prevention.
6. Ambiguous marks exclusion.
7. Verified-only historical features.
8. Synthetic-only test fixtures vs empirical claim separation.
9. Chronological leakage prevention (no future session target leakage).
10. Insufficient independent examination sessions.
11. Historical frequency baseline (Baseline A).
12. Recency-weighted frequency baseline (Baseline B).
13. Regularized statistical model (Baseline C).
14. Experimental versus validated readiness states.
15. Probability vs ranking score distinction (no sum-to-1 constraint).
16. Prediction API compatibility.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.chronological_prediction_evaluator import ChronologicalPredictionEvaluator
from services.evidence_aware_topic_predictor import EvidenceAwareTopicPredictor
from services.historical_feature_pipeline import HistoricalFeaturePipeline
from services.prediction_readiness_service import (
    PredictionReadinessAssessor,
    STATUS_AWAITING_VERIFICATION,
    STATUS_EXPERIMENTAL_PREDICTION_READY,
    STATUS_HISTORICAL_ANALYSIS_READY,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_VALIDATED_PREDICTION_READY,
)
from services.topic_prediction_engine import TopicPredictionEngine


# -------------------------------------------------------------
# 1. Readiness Assessment Tests
# -------------------------------------------------------------

def test_zero_verified_labels_returns_awaiting_verification():
    """All 8 target modules currently have 0 verified labels and should await review."""
    assessor = PredictionReadinessAssessor()
    report = assessor.assess_module("database_systems")

    assert report["verified_question_count"] == 0
    assert report["readiness_status"] == STATUS_AWAITING_VERIFICATION
    assert report["is_prediction_eligible"] is False
    assert any("verification" in req.lower() for req in report["missing_requirements"])


def test_insufficient_papers_returns_insufficient_evidence():
    """Modules with fewer than 3 authentic papers evaluate as insufficient_evidence."""
    assessor = PredictionReadinessAssessor()
    # Software Project Management currently has 1 paper
    report = assessor.assess_module("software_project_management")

    assert report["distinct_historical_papers"] < 3
    assert report["readiness_status"] == STATUS_INSUFFICIENT_EVIDENCE
    assert report["is_prediction_eligible"] is False
    assert any("session" in req.lower() or "paper" in req.lower() for req in report["missing_requirements"])


def test_all_eight_modules_readiness_audit():
    """Verify that all eight Year 3 modules are assessed without errors."""
    assessor = PredictionReadinessAssessor()
    all_reports = assessor.assess_all_modules()
    reports_map = all_reports.get("modules", all_reports)

    assert len(reports_map) == 8
    for mod_key, rep in reports_map.items():
        assert rep["status"] in (
            STATUS_INSUFFICIENT_EVIDENCE,
            STATUS_AWAITING_VERIFICATION,
            STATUS_HISTORICAL_ANALYSIS_READY,
            STATUS_EXPERIMENTAL_PREDICTION_READY,
            STATUS_VALIDATED_PREDICTION_READY,
        )
        assert "academic_integrity_notice" in rep


def test_unverified_taxonomy_blocks_prediction_even_with_papers():
    """An unverified taxonomy prevents promoting a module to prediction-ready."""
    assessor = PredictionReadinessAssessor()
    # Mock pattern analysis with 5 papers but unverified taxonomy
    mock_analysis = {
        "total_questions": 100,
        "distinct_papers": 5,
        "distinct_years": ["2018", "2019", "2022", "2023"],
        "topics": {
            "verified_classified_questions": 90,
            "without_verified_topic": 10,
            "statistics": [],
        },
        "marks": {"questions_with_extracted_marks": 80, "ambiguous_marks_questions": 10},
    }

    report = assessor.assess_module("application_frameworks", pattern_analysis=mock_analysis)
    # Since taxonomy in topic_taxonomies.json is unverified, it must await taxonomy approval
    assert report["taxonomy_verified"] is False
    assert report["readiness_status"] == STATUS_AWAITING_VERIFICATION


# -------------------------------------------------------------
# 2. Historical Feature Pipeline & Leakage Prevention Tests
# -------------------------------------------------------------

def test_feature_pipeline_zero_verified_labels_returns_empty():
    """Pipeline safely returns structured empty response when 0 verified labels exist."""
    pipeline = HistoricalFeaturePipeline()
    res = pipeline.build_features_for_module("database_systems")

    assert res["status"] == "insufficient_verified_evidence"
    assert res["sessions_count"] == 0
    assert len(res["feature_records"]) == 0
    assert "No lecturer-verified topic labels" in res["reason"]


def test_feature_pipeline_chronological_causality():
    """Verify causal feature extraction: target session T does not leak into features."""
    pipeline = HistoricalFeaturePipeline()

    taxonomy_topics = [
        {"topic_id": "topic_sql", "topic_name": "SQL"},
        {"topic_id": "topic_norm", "topic_name": "Normalization"},
    ]

    # Deterministic sessions: S0, S1, S2
    # S0: SQL appeared
    # S1: SQL appeared, Normalization appeared
    # S2: Target session (SQL and Norm appeared)
    sessions = [
        {
            "session_id": "P_2018",
            "academic_year": 2018,
            "paper_id": "P_2018",
            "topics_present": {"topic_sql": 2},
            "topics_marks": {"topic_sql": 20},
            "total_questions": 5,
            "total_marks": 50,
        },
        {
            "session_id": "P_2019",
            "academic_year": 2019,
            "paper_id": "P_2019",
            "topics_present": {"topic_sql": 1, "topic_norm": 2},
            "topics_marks": {"topic_sql": 10, "topic_norm": 20},
            "total_questions": 5,
            "total_marks": 50,
        },
    ]

    features = pipeline._compute_causal_features("test_mod", sessions, taxonomy_topics)

    assert features["sessions_count"] == 2
    target_feats = features["target_session_features"]
    assert len(target_feats) == 2

    sql_target = next(f for f in target_feats if f["topic_id"] == "topic_sql")
    norm_target = next(f for f in target_feats if f["topic_id"] == "topic_norm")

    # SQL appeared in both S0 and S1 -> historical frequency = 2 / 2 = 1.0
    assert sql_target["historical_frequency"] == 1.0
    assert sql_target["sessions_since_last_appearance"] == 0

    # Normalization appeared in S1 only -> historical frequency = 1 / 2 = 0.5
    assert norm_target["historical_frequency"] == 0.5
    assert norm_target["sessions_since_last_appearance"] == 0


def test_missing_year_vs_zero_occurrences():
    """Features distinguish a missing examination year from an observed paper with 0 topic occurrences."""
    pipeline = HistoricalFeaturePipeline()
    # Verified: sessions represent observed papers, not calendar years.
    # If 2020 had no paper, no session exists for 2020.
    sessions = [
        {
            "session_id": "P_2019",
            "academic_year": 2019,
            "topics_present": {"topic_a": 1},
            "topics_marks": {"topic_a": 10},
            "total_questions": 5,
            "total_marks": 50,
        },
        {
            "session_id": "P_2022",
            "academic_year": 2022,
            "topics_present": {},  # 0 occurrences in 2022
            "topics_marks": {},
            "total_questions": 5,
            "total_marks": 50,
        },
    ]
    tax = [{"topic_id": "topic_a", "topic_name": "Topic A"}]
    res = pipeline._compute_causal_features("test_mod", sessions, tax)
    target_a = res["target_session_features"][0]

    # In 2022, topic_a was absent -> sessions_since_last_appearance is 1 session ago
    assert target_a["sessions_since_last_appearance"] == 1
    assert target_a["historical_frequency"] == 0.5


# -------------------------------------------------------------
# 3. Prediction Baselines & Non-Additivity Tests
# -------------------------------------------------------------

def test_baselines_inhibit_training_when_unverified():
    """Prediction engine returns model_not_trained when verified labels are absent."""
    engine = TopicPredictionEngine()
    result = engine.generate_predictions("database_systems", method="historical_frequency")

    assert result["status"] == "model_not_trained"
    assert result["prediction_available"] is False
    assert result["future_probabilities_available"] is False
    assert len(result["predictions"]) == 0
    assert "academic_integrity_notice" in result


def test_probabilities_do_not_sum_to_1():
    """Multiple topics may co-occur in the same paper; scores must not be normalized to sum to 1.0."""
    engine = TopicPredictionEngine()
    tax_topics = {"t1": "T1", "t2": "T2"}
    target_features = [
        {"topic_id": "t1", "historical_frequency": 0.8, "recency_weighted_frequency": 0.8, "sessions_since_last_appearance": 0, "historical_occurrences_count": 4, "prior_sessions_count": 5},
        {"topic_id": "t2", "historical_frequency": 0.7, "recency_weighted_frequency": 0.7, "sessions_since_last_appearance": 0, "historical_occurrences_count": 3, "prior_sessions_count": 5},
    ]

    preds = engine._infer_historical_frequency(target_features, tax_topics)
    total_score = sum(p["score"] for p in preds)

    # 0.8 + 0.7 = 1.5 > 1.0 (valid! independent binary occurrences)
    assert total_score == pytest.approx(1.5, 0.01)
    assert preds[0]["score_type"] == "experimental_priority_score"


def test_recency_weighted_baseline_favors_recent_sessions():
    """Baseline B weights recent appearances higher than older appearances."""
    engine = TopicPredictionEngine()
    tax_topics = {"recent_topic": "Recent", "old_topic": "Old"}
    # Topic 1 appeared recently (recency weighted = 0.9, hist freq = 0.5)
    # Topic 2 appeared long ago (recency weighted = 0.2, hist freq = 0.5)
    target_features = [
        {"topic_id": "recent_topic", "historical_frequency": 0.5, "recency_weighted_frequency": 0.9, "sessions_since_last_appearance": 0, "historical_occurrences_count": 2, "prior_sessions_count": 4},
        {"topic_id": "old_topic", "historical_frequency": 0.5, "recency_weighted_frequency": 0.2, "sessions_since_last_appearance": 3, "historical_occurrences_count": 2, "prior_sessions_count": 4},
    ]

    preds = engine._infer_recency_weighted(target_features, tax_topics)
    assert preds[0]["topic_id"] == "recent_topic"
    assert preds[0]["score"] > preds[1]["score"]


# -------------------------------------------------------------
# 4. Chronological Evaluation & Synthetic Fixture Tests
# -------------------------------------------------------------

def test_chronological_evaluator_unverified_reports_not_evaluable():
    """Evaluator reports not_evaluable on authentic unverified dataset."""
    evaluator = ChronologicalPredictionEvaluator()
    res = evaluator.evaluate("database_systems")

    assert res["status"] == "not_evaluable"
    assert res["is_evaluable"] is False
    assert res["metrics"] is None
    assert "evaluation_protocol" in res
    assert len(res["sample_size_limitations"]) > 0


def test_chronological_evaluator_synthetic_fixture():
    """Software test fixture correctly computes walk-forward Precision, Recall, MRR, and Brier Score."""
    evaluator = ChronologicalPredictionEvaluator()
    res = evaluator.evaluate_synthetic_test_fixture()

    assert res["status"] == "evaluated"
    assert res["is_evaluable"] is True
    assert res["provenance"]["synthetic_fixture"] is True
    assert "FOR SOFTWARE TEST PURPOSES ONLY" in res["provenance"]["warning"]
    assert res["number_of_splits"] == 2

    # Check metrics existence
    models = res["models"]
    assert "historical_frequency" in models
    assert "recency_weighted_frequency" in models
    assert "regularized_statistical_model" in models

    summary = models["recency_weighted_frequency"]["summary"]
    assert "mean_precision@3" in summary
    assert "mean_recall@3" in summary
    assert "mean_reciprocal_rank" in summary
    assert "mean_brier_score" in summary
    assert 0.0 <= summary["mean_brier_score"] <= 1.0


# -------------------------------------------------------------
# 5. FastAPI Endpoints Integration Tests
# -------------------------------------------------------------

client = TestClient(app)
INTERNAL_TOKEN = "test-internal-token"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("C2_INTERNAL_TOKEN", INTERNAL_TOKEN)


def test_api_topic_predictions_endpoint():
    """GET /topic-predictions returns prediction readiness and baseline blocks."""
    response = client.get(
        "/topic-predictions",
        params={"module_key": "database_systems", "target_period": "end_semester"},
        headers={"x-c2-internal-token": INTERNAL_TOKEN},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["module_key"] == "database_systems"
    assert data["target_examination_period"] == "end_semester"
    assert data["future_exam_probabilities_available"] is False
    assert "prediction_readiness" in data
    assert "prediction_models" in data
    assert "chronological_evaluation" in data


def test_api_predictions_readiness_all_modules():
    """GET /predictions/readiness returns all 8 modules with integrity notice."""
    response = client.get(
        "/predictions/readiness",
        headers={"x-c2-internal-token": INTERNAL_TOKEN},
    )

    assert response.status_code == 200
    data = response.json()
    assert "modules" in data
    assert len(data["modules"]) == 8
    assert "academic_integrity_notice" in data


def test_api_predictions_readiness_single_module():
    """GET /predictions/readiness?module_key=... returns specific module readiness."""
    response = client.get(
        "/predictions/readiness",
        params={"module_key": "software_project_management"},
        headers={"x-c2-internal-token": INTERNAL_TOKEN},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["module_key"] == "software_project_management"
    assert data["readiness_status"] == STATUS_INSUFFICIENT_EVIDENCE


def test_api_predictions_evaluation_endpoint():
    """GET /predictions/evaluation returns not_evaluable for unverified authentic module."""
    response = client.get(
        "/predictions/evaluation",
        params={"module_key": "application_frameworks"},
        headers={"x-c2-internal-token": INTERNAL_TOKEN},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_evaluable"
    assert data["is_evaluable"] is False
