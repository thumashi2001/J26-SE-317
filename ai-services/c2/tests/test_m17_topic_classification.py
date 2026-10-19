"""Unit and integration tests for M17 Topic Classification.

Tests dataset integrity, deterministic training, baseline comparison,
abstention behavior, artifact persistence, API integration, and authentic data isolation.
Uses small synthetic fixtures for fast execution.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure ai-services/c2 is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.m17_model_evaluator import M17ModelEvaluator
from services.m17_topic_classifier_trainer import (
    M17DatasetIntegrityError,
    M17TopicClassifierTrainer,
    normalize_text,
)
from services.m17_topic_prediction_service import (
    M17TopicPredictionService,
    ModelNotFoundError,
)

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mini_train_questions():
    """Small fixture of synthetic questions across 2 topics for 1 module."""
    questions = []
    # Topic 1: Database Indexing
    for i in range(10):
        questions.append({
            "question_id": f"SYN-MINI-DB-IDX-{i}",
            "module_key": "database_systems",
            "topic": "Database Indexing",
            "question_text": f"Scenario {i}: B-tree indexing and query optimization on clustered primary index.\nTask: Evaluate index scan vs table scan disk I/O.",
            "source_type": "synthetic",
            "verification_status": "unverified",
            "scenario_group_id": f"database_systems:indexing:{i}",
            "template_family_id": "db_idx_analyze_t1",
        })
    # Topic 2: Concurrency Control
    for i in range(10):
        questions.append({
            "question_id": f"SYN-MINI-DB-CC-{i}",
            "module_key": "database_systems",
            "topic": "Concurrency Control",
            "question_text": f"Scenario {i}: High volume concurrent transaction processing with deadlock detection.\nTask: Compare two-phase locking with strict 2PL.",
            "source_type": "synthetic",
            "verification_status": "unverified",
            "scenario_group_id": f"database_systems:concurrency:{i}",
            "template_family_id": "db_cc_analyze_t1",
        })
    return questions


@pytest.fixture
def mini_val_questions():
    """Small validation fixture with disjoint scenarios."""
    return [
        {
            "question_id": "SYN-MINI-VAL-IDX-0",
            "module_key": "database_systems",
            "topic": "Database Indexing",
            "question_text": "Scenario 99: Clustered index maintenance during heavy write loads.\nTask: Evaluate index fragmentation and re-indexing costs.",
            "source_type": "synthetic",
            "verification_status": "unverified",
            "scenario_group_id": "database_systems:indexing:val_0",
            "template_family_id": "db_idx_analyze_t1",
        },
        {
            "question_id": "SYN-MINI-VAL-CC-0",
            "module_key": "database_systems",
            "topic": "Concurrency Control",
            "question_text": "Scenario 99: Banking transfer deadlock and serializability anomalies.\nTask: Analyze snapshot isolation vs serializable locking.",
            "source_type": "synthetic",
            "verification_status": "unverified",
            "scenario_group_id": "database_systems:concurrency:val_0",
            "template_family_id": "db_cc_analyze_t1",
        },
    ]


# -----------------------------------------------------------------------------
# 1. Dataset Integrity & Loading Tests
# -----------------------------------------------------------------------------

def test_normalize_text():
    assert normalize_text("  Scenario:  A database  lock \n\n ") == "scenario: a database lock"
    with pytest.raises(ValueError):
        normalize_text("")
    with pytest.raises(ValueError):
        normalize_text(None)


def test_load_split_rejects_non_synthetic(tmp_path):
    bad_data = {
        "source_type": "authentic",  # Forbidden in M17 training
        "verification_status": "unverified",
        "provisional_topics": True,
        "questions": [{"question_id": "Q1", "module_key": "database_systems", "topic": "T1", "question_text": "txt"}],
    }
    p = tmp_path / "train.json"
    p.write_text(json.dumps(bad_data), encoding="utf-8")

    trainer = M17TopicClassifierTrainer(data_dir=tmp_path)
    with pytest.raises(M17DatasetIntegrityError, match="Only synthetic development data may be loaded"):
        trainer.load_split("train")


def test_load_split_rejects_verified_data(tmp_path):
    bad_data = {
        "source_type": "synthetic",
        "verification_status": "verified",  # Must remain unverified
        "provisional_topics": True,
        "questions": [{"question_id": "Q1", "module_key": "database_systems", "topic": "T1", "question_text": "txt"}],
    }
    p = tmp_path / "train.json"
    p.write_text(json.dumps(bad_data), encoding="utf-8")

    trainer = M17TopicClassifierTrainer(data_dir=tmp_path)
    with pytest.raises(M17DatasetIntegrityError, match="Expected 'unverified'"):
        trainer.load_split("train")


def test_split_integrity_detects_leakage():
    trainer = M17TopicClassifierTrainer()

    train_data = {
        "questions": [
            {"question_id": "Q1", "scenario_group_id": "S1", "template_family_id": "T1", "module_key": "database_systems", "topic": "T1", "question_text": "txt"}
        ]
    }
    val_data = {
        "questions": [
            {"question_id": "Q1", "scenario_group_id": "S2", "template_family_id": "T2", "module_key": "database_systems", "topic": "T1", "question_text": "txt"}
        ]
    }
    test_data = {"questions": []}

    # Duplicate question ID across train and val
    with pytest.raises(M17DatasetIntegrityError, match="Question ID overlap"):
        trainer.validate_split_integrity(train_data, val_data, test_data)


def test_split_integrity_detects_scenario_leakage():
    trainer = M17TopicClassifierTrainer()

    train_data = {
        "questions": [
            {"question_id": "Q1", "scenario_group_id": "SHARED_SCENARIO", "template_family_id": "T1", "module_key": "database_systems", "topic": "T1", "question_text": "txt"}
        ]
    }
    val_data = {
        "questions": [
            {"question_id": "Q2", "scenario_group_id": "SHARED_SCENARIO", "template_family_id": "T2", "module_key": "database_systems", "topic": "T1", "question_text": "txt"}
        ]
    }
    test_data = {"questions": []}

    with pytest.raises(M17DatasetIntegrityError, match="Scenario group overlap"):
        trainer.validate_split_integrity(train_data, val_data, test_data)


# -----------------------------------------------------------------------------
# 2. Deterministic Training & Baseline Comparison Tests
# -----------------------------------------------------------------------------

def test_deterministic_training_logistic_regression(mini_train_questions):
    trainer = M17TopicClassifierTrainer()

    res1 = trainer.train_module(
        module_key="database_systems",
        questions=mini_train_questions,
        model_type="logistic_regression",
        seed=42,
    )
    res2 = trainer.train_module(
        module_key="database_systems",
        questions=mini_train_questions,
        model_type="logistic_regression",
        seed=42,
    )

    clf1 = res1["pipeline"].named_steps["clf"]
    clf2 = res2["pipeline"].named_steps["clf"]

    # Verify model parameters and coefficients are completely deterministic
    np.testing.assert_array_almost_equal(clf1.coef_, clf2.coef_)
    assert res1["classes"] == res2["classes"] == ["Concurrency Control", "Database Indexing"]


def test_train_module_linear_svc(mini_train_questions):
    trainer = M17TopicClassifierTrainer()

    res = trainer.train_module(
        module_key="database_systems",
        questions=mini_train_questions,
        model_type="linear_svc",
        seed=42,
    )
    assert res["model_type"] == "linear_svc"
    assert "pipeline" in res
    assert res["n_classes"] == 2


def test_baseline_model_comparison_on_validation(mini_train_questions, mini_val_questions):
    trainer = M17TopicClassifierTrainer()
    evaluator = M17ModelEvaluator()

    pkg_a = trainer.train_module("database_systems", mini_train_questions, "logistic_regression", seed=42)
    pkg_b = trainer.train_module("database_systems", mini_train_questions, "linear_svc", seed=42)

    val_a = evaluator.evaluate_single_module("database_systems", pkg_a, mini_val_questions)
    val_b = evaluator.evaluate_single_module("database_systems", pkg_b, mini_val_questions)

    assert val_a["accuracy"] == 1.0
    assert val_a["macro_f1"] == 1.0
    assert val_b["accuracy"] == 1.0
    assert val_b["macro_f1"] == 1.0

    # Test suite evaluation and tie-breaker
    suite_a = {"database_systems": pkg_a}
    suite_b = {"database_systems": pkg_b}

    eval_a = evaluator.evaluate_model_suite(suite_a, mini_val_questions)
    eval_b = evaluator.evaluate_model_suite(suite_b, mini_val_questions)

    winner, rationale = evaluator.select_best_model(eval_a, eval_b)
    # When scores tie, deterministic tie-breaker selects logistic_regression for calibrated probabilities
    assert winner == "logistic_regression"
    assert "deterministic tie-breaker" in rationale


# -----------------------------------------------------------------------------
# 3. Abstention & Prediction Service Tests
# -----------------------------------------------------------------------------

def test_abstention_curve_analysis():
    predictions = [
        {"confidence_score": 0.95, "correct": True, "score_type": "calibrated_probability"},
        {"confidence_score": 0.85, "correct": True, "score_type": "calibrated_probability"},
        {"confidence_score": 0.52, "correct": False, "score_type": "calibrated_probability"},
        {"confidence_score": 0.40, "correct": False, "score_type": "calibrated_probability"},
    ]

    curve = M17ModelEvaluator.analyze_abstention_curve(predictions, thresholds=[0.50, 0.80])
    assert len(curve) == 2
    # At threshold 0.50: retained = 3, abstained = 1, coverage = 3/4 = 0.75, acc = 2/3 = 0.6667
    assert curve[0]["threshold"] == 0.50
    assert curve[0]["retained_count"] == 3
    assert curve[0]["coverage"] == 0.75
    # At threshold 0.80: retained = 2, abstained = 2, coverage = 2/4 = 0.50, acc = 2/2 = 1.0
    assert curve[1]["threshold"] == 0.80
    assert curve[1]["retained_count"] == 2
    assert curve[1]["accuracy_retained"] == 1.0


def test_prediction_service_with_trained_artifact(mini_train_questions, tmp_path):
    trainer = M17TopicClassifierTrainer(models_dir=tmp_path)
    pkg = trainer.train_module("database_systems", mini_train_questions, "logistic_regression", seed=42)

    integrity_mock = {
        "counts": {"train": 20, "validation": 2, "test": 0, "total": 22},
        "scenario_isolation": {"train_scenarios": 20, "val_scenarios": 2, "test_scenarios": 0, "disjoint": True},
        "template_family_risk": {"risk_flagged": False},
        "status": "passed",
    }
    trainer.save_artifacts({"database_systems": pkg}, "logistic_regression", integrity_mock, output_dir=tmp_path, is_selected_production_candidate=True)

    predictor = M17TopicPredictionService(models_dir=tmp_path, default_threshold=0.55)

    # 1. High-confidence query -> classified
    res_high = predictor.predict(
        module_key="database_systems",
        question_text="Explain B-tree clustered index scans and disk block fetch optimization.",
    )
    assert res_high["module_key"] == "database_systems"
    assert res_high["predicted_topic"] == "Database Indexing"
    assert res_high["decision"] == "classified"
    assert res_high["abstained"] is False
    assert res_high["confidence_score"] >= 0.55
    assert res_high["score_type"] == "calibrated_probability"
    assert res_high["verification_status"] == "unverified"
    assert "synthetic" in res_high["disclaimer"].lower()

    # 2. Strict threshold test -> abstained
    res_abstained = predictor.predict(
        module_key="database_systems",
        question_text="Explain B-tree clustered index scans.",
        threshold=0.9999,
    )
    assert res_abstained["decision"] == "needs_review"
    assert res_abstained["predicted_topic"] == "unclassified"
    assert res_abstained["candidate_topic"] == "Database Indexing"
    assert res_abstained["abstained"] is True


def test_prediction_service_input_validation(tmp_path):
    predictor = M17TopicPredictionService(models_dir=tmp_path)

    # Invalid module key
    with pytest.raises(ValueError, match="Invalid module key"):
        predictor.predict("non_existent_module", "Explain something.")

    # Empty question text
    with pytest.raises(ValueError, match="Question text cannot be empty"):
        predictor.predict("database_systems", "   \n  ")

    # Missing model artifact raises ModelNotFoundError
    with pytest.raises(ModelNotFoundError):
        predictor.predict("database_systems", "Valid question text.")


def test_prediction_service_path_traversal_prevention(tmp_path):
    predictor = M17TopicPredictionService(models_dir=tmp_path)
    # Attempting to use a traversal sequence fails canonical validation
    with pytest.raises(ValueError, match="Invalid module key"):
        predictor.canonicalize_module_key("../../etc/passwd")


# -----------------------------------------------------------------------------
# 4. API Integration Tests
# -----------------------------------------------------------------------------

def test_api_classify_topic_endpoint_missing_token():
    client = TestClient(app)
    response = client.post(
        "/api/v1/experimental/classify-topic",
        json={"module_key": "database_systems", "question_text": "What is indexing?"},
    )
    # Internal token is required
    assert response.status_code in (401, 503)


def test_api_classify_topic_endpoint_invalid_module(monkeypatch):
    monkeypatch.setenv("C2_INTERNAL_TOKEN", "valid-test-token")
    client = TestClient(app)

    response = client.post(
        "/api/v1/experimental/classify-topic",
        json={"module_key": "invalid_module", "question_text": "What is indexing?"},
        headers={"x-c2-internal-token": "valid-test-token"},
    )
    assert response.status_code == 400
    assert "Invalid module" in response.json()["detail"]


def test_api_classify_topic_endpoint_missing_model(monkeypatch, tmp_path):
    monkeypatch.setenv("C2_INTERNAL_TOKEN", "valid-test-token")
    client = TestClient(app)

    # Patch experimental_topic_predictor models_dir to an empty directory
    with patch("api.main.experimental_topic_predictor.models_dir", tmp_path):
        response = client.post(
            "/api/v1/experimental/classify-topic",
            json={"module_key": "database_systems", "question_text": "What is indexing?"},
            headers={"x-c2-internal-token": "valid-test-token"},
        )
        assert response.status_code == 503
        assert "not available" in response.json()["detail"]


def test_api_classify_topic_endpoint_success(monkeypatch, mini_train_questions, tmp_path):
    monkeypatch.setenv("C2_INTERNAL_TOKEN", "valid-test-token")
    client = TestClient(app)

    # Train and save a mini model in tmp_path
    trainer = M17TopicClassifierTrainer(models_dir=tmp_path)
    pkg = trainer.train_module("database_systems", mini_train_questions, "logistic_regression", seed=42)
    trainer.save_artifacts(
        {"database_systems": pkg},
        "logistic_regression",
        {"status": "passed", "counts": {"train": 20, "validation": 0, "test": 0, "total": 20}, "scenario_isolation": {"train_scenarios": 20, "val_scenarios": 0, "test_scenarios": 0, "disjoint": True}, "template_family_risk": {"risk_flagged": False}},
        output_dir=tmp_path,
        is_selected_production_candidate=True,
    )

    with patch("api.main.experimental_topic_predictor.models_dir", tmp_path):
        response = client.post(
            "/api/v1/experimental/classify-topic",
            json={
                "module_key": "database_systems",
                "question_text": "Explain B-tree clustered index scans and page split disk I/O.",
                "abstention_threshold": 0.50,
            },
            headers={"x-c2-internal-token": "valid-test-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["module_key"] == "database_systems"
        assert data["predicted_topic"] == "Database Indexing"
        assert data["decision"] == "classified"
        assert data["confidence_score"] >= 0.50
        assert data["score_type"] == "calibrated_probability"
        assert data["verification_status"] == "unverified"
        assert "synthetic" in data["disclaimer"].lower()


def test_report_generation(tmp_path):
    evaluator = M17ModelEvaluator(reports_dir=tmp_path)

    val_mock = {
        "overall_macro_f1": 0.88,
        "overall_accuracy": 0.90,
        "overall_macro_precision": 0.89,
        "overall_macro_recall": 0.87,
        "overall_weighted_f1": 0.89,
        "total_inference_time_seconds": 0.05,
        "per_module": {
            "database_systems": {
                "macro_f1": 0.88,
                "accuracy": 0.90,
                "macro_precision": 0.89,
                "macro_recall": 0.87,
                "weighted_f1": 0.89,
            }
        },
    }
    test_mock = {
        "total_samples": 96,
        "overall_macro_f1": 0.86,
        "overall_accuracy": 0.88,
        "overall_macro_precision": 0.87,
        "overall_macro_recall": 0.85,
        "overall_weighted_f1": 0.87,
        "total_inference_time_seconds": 0.04,
        "per_module": {
            "database_systems": {
                "n_samples": 12,
                "macro_f1": 0.86,
                "accuracy": 0.88,
                "macro_precision": 0.87,
                "macro_recall": 0.85,
                "weighted_f1": 0.87,
                "per_topic": {},
                "confusion_matrix": [],
                "classes": ["Database Indexing", "Concurrency Control"],
            }
        },
    }
    curve_mock = [
        {"threshold": 0.55, "retained_count": 90, "abstained_count": 6, "coverage": 0.9375, "accuracy_retained": 0.92}
    ]
    integrity_mock = {
        "counts": {"train": 576, "validation": 128, "test": 96, "total": 800},
        "scenario_isolation": {"train_scenarios": 144, "val_scenarios": 32, "test_scenarios": 24, "disjoint": True},
        "template_family_risk": {
            "train_val_overlap_count": 100,
            "train_test_overlap_count": 84,
            "val_test_overlap_count": 48,
            "risk_flagged": True,
            "explanation": "Template overlap present.",
        },
        "status": "passed",
    }

    json_path, md_path = evaluator.generate_reports(
        baseline_a_val=val_mock,
        baseline_b_val=val_mock,
        selected_model_type="logistic_regression",
        selection_rationale="Tie-breaker selected logistic regression.",
        test_results=test_mock,
        abstention_curve=curve_mock,
        recommended_threshold=0.55,
        integrity_summary=integrity_mock,
    )

    assert json_path.exists()
    assert md_path.exists()

    report_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert report_json["academic_verification"]["authentic_examination_evaluation"] == "NOT PERFORMED"
    assert report_json["academic_verification"]["status"] == "unverified"
    assert report_json["baseline_comparison_validation"]["selected_model"] == "logistic_regression"

    md_content = md_path.read_text(encoding="utf-8")
    assert "Authentic Evaluation: **NOT PERFORMED**" in md_content
    assert "Template-Family Overlap" in md_content


def test_isolation_from_authentic_repositories(mini_train_questions, tmp_path):
    """Ensure training and prediction services never touch authentic datasets."""
    authentic_dir = PROJECT_ROOT / "datasets" / "authentic"
    processed_dir = PROJECT_ROOT / "datasets" / "processed"

    # Capture directory modification times before
    before_auth = authentic_dir.stat().st_mtime if authentic_dir.exists() else None
    before_proc = processed_dir.stat().st_mtime if processed_dir.exists() else None

    # Run training and prediction in isolated tmp_path
    trainer = M17TopicClassifierTrainer(models_dir=tmp_path)
    pkg = trainer.train_module("database_systems", mini_train_questions, "logistic_regression", seed=42)
    trainer.save_artifacts({"database_systems": pkg}, "logistic_regression", {"status": "passed"}, output_dir=tmp_path)

    predictor = M17TopicPredictionService(models_dir=tmp_path)
    res = predictor.predict("database_systems", "Analyze transaction locking protocols.")

    assert res["decision"] in ("classified", "needs_review")
    # Verify authentic directories were not modified
    if authentic_dir.exists():
        assert authentic_dir.stat().st_mtime == before_auth
    if processed_dir.exists():
        assert processed_dir.stat().st_mtime == before_proc
