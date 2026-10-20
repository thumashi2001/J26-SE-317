"""Tests for AuthenticTopicClassifierEvaluator."""

import pytest
from services.authentic_topic_classifier_evaluator import AuthenticTopicClassifierEvaluator


def test_evaluator_returns_not_evaluable_when_zero_labels():
    evaluator = AuthenticTopicClassifierEvaluator()
    res = evaluator.evaluate(verified_labels=[])
    assert res["status"] == "not_evaluable"
    assert res["evaluable"] is False
    assert res["total_verified_labels"] == 0
    assert "Insufficient" in res["reason"]
    assert res["metrics"] is None


def test_evaluator_filters_out_non_approved_decisions():
    class DummyRepo:
        def get_all_reviews(self):
            return [
                {"question_id": "q1", "decision": "rejected", "topic_id": "topic_a"},
                {"question_id": "q2", "decision": "deferred", "topic_id": "topic_b"},
                {"question_id": "q3", "decision": "pending", "topic_id": "topic_c"},
            ]

    evaluator = AuthenticTopicClassifierEvaluator(reviews_repo=DummyRepo())
    res = evaluator.evaluate()
    assert res["status"] == "not_evaluable"
    assert res["total_verified_labels"] == 0


def test_evaluator_computes_accuracy_and_recall_on_verified_labels():
    verified_labels = [
        {"question_id": "q1", "module_key": "database_systems", "topic_id": "sql_queries", "decision": "approved"},
        {"question_id": "q2", "module_key": "database_systems", "topic_id": "transactions", "decision": "approved"},
        {"question_id": "q3", "module_key": "database_systems", "topic_id": "indexing", "decision": "approved"},
        {"question_id": "q4", "module_key": "database_systems", "topic_id": "nosql", "decision": "approved"},
    ]

    classifications = [
        # q1: top-1 correct, in top-3
        {
            "question_id": "q1",
            "candidate_topics": [{"topic_id": "sql_queries"}, {"topic_id": "transactions"}],
            "abstained": False,
        },
        # q2: top-1 wrong, but in top-3
        {
            "question_id": "q2",
            "candidate_topics": [{"topic_id": "sql_queries"}, {"topic_id": "transactions"}, {"topic_id": "indexing"}],
            "abstained": False,
        },
        # q3: top-1 wrong, not in top-3
        {
            "question_id": "q3",
            "candidate_topics": [{"topic_id": "sql_queries"}, {"topic_id": "transactions"}],
            "abstained": False,
        },
        # q4: abstained
        {
            "question_id": "q4",
            "candidate_topics": [],
            "abstained": True,
        },
    ]

    evaluator = AuthenticTopicClassifierEvaluator()
    res = evaluator.evaluate(verified_labels=verified_labels, classifications=classifications)

    assert res["status"] == "evaluated"
    assert res["evaluable"] is True
    assert res["total_verified_labels"] == 4

    metrics = res["metrics"]
    # 1 out of 4 correct top-1: 0.25
    assert metrics["top1_accuracy"] == 0.25
    # q1 (hit) and q2 (hit): 2 out of 4 in top-3: 0.50
    assert metrics["top3_candidate_recall"] == 0.50
    # q4 abstained: 1 out of 4: 0.25
    assert metrics["abstention_rate"] == 0.25

    # Check per-module stats
    assert "database_systems" in metrics["per_module"]
    db_stats = metrics["per_module"]["database_systems"]
    assert db_stats["total_verified"] == 4
    assert db_stats["top1_accuracy"] == 0.25

    # Check error analysis
    errors = res["error_analysis"]
    assert errors["total_errors"] == 3
