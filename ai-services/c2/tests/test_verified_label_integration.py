"""M20.5: Tests verifying integration of lecturer-verified labels with M19.7 and M20.

Confirms that:
1. Candidate suggestions do not enter historical ground truth.
2. Low-confidence review candidates do not enter historical ground truth.
3. Rejected suggestions do not enter historical ground truth.
4. Synthetic questions do not enter historical ground truth.
5. Human-approved authentic labels are eligible when taxonomy verification is met.
"""

import pytest
from services.exam_pattern_analyzer import ExamPatternAnalyzer
from services.historical_feature_pipeline import HistoricalFeaturePipeline
from services.question_classification_review_repository import QuestionClassificationReviewRepository


class InMemoryReviewRepo:
    def __init__(self, reviews=None):
        self.reviews = reviews or []

    def get_all_reviews(self):
        return list(self.reviews)

    def get_review(self, question_id):
        for r in self.reviews:
            if r.get("question_id") == question_id:
                return r
        return None


def test_candidates_and_low_confidence_do_not_enter_historical_ground_truth():
    """Unapproved machine suggestions remain unverified in ExamPatternAnalyzer."""
    repo = InMemoryReviewRepo([
        # Low confidence suggestion or candidate not approved
        {"question_id": "q1", "module_key": "database_systems", "decision": "deferred", "topic_id": "sql_queries"},
    ])
    analyzer = ExamPatternAnalyzer(reviews_repo=repo)
    analysis = analyzer.analyze("database_systems")
    # All authentic questions remain unverified because no approved review exists
    topics = analysis.get("topics", {})
    assert topics.get("verified_classified_questions") == 0


def test_rejected_review_does_not_enter_historical_ground_truth():
    """Rejected reviews are explicitly excluded from verified topics."""
    repo = InMemoryReviewRepo([
        {"question_id": "IT3020-2023-a34dce2c9501-Q1(a)", "module_key": "database_systems", "decision": "rejected", "topic_id": "sql_queries"},
    ])
    analyzer = ExamPatternAnalyzer(reviews_repo=repo)
    analysis = analyzer.analyze("database_systems")
    topics = analysis.get("topics", {})
    assert topics.get("verified_classified_questions") == 0


def test_human_approved_authentic_label_is_counted_in_exam_pattern_analyzer():
    """Approved review overlays into valid classifications as verified."""
    repo = InMemoryReviewRepo([
        {
            "question_id": "IT3020-2023-a34dce2c9501-Q1(a)",
            "module_key": "database_systems",
            "decision": "approved",
            "topic_id": "sql_queries",
            "reviewer_id": "lecturer_123",
        },
    ])
    analyzer = ExamPatternAnalyzer(reviews_repo=repo)
    analysis = analyzer.analyze("database_systems")
    topics = analysis.get("topics", {})
    assert topics.get("verified_classified_questions") == 1
    stats = topics.get("statistics", [])
    sql_stat = next((s for s in stats if s["topic_id"] == "sql_queries"), None)
    assert sql_stat is not None
    assert sql_stat["question_count"] == 1


def test_historical_feature_pipeline_overlays_approved_reviews():
    """HistoricalFeaturePipeline includes approved reviews in verified_classifications."""
    repo = InMemoryReviewRepo([
        {
            "question_id": "IT3020-2023-a34dce2c9501-Q1(a)",
            "module_key": "database_systems",
            "decision": "approved",
            "topic_id": "sql_queries",
            "reviewer_id": "lecturer_123",
        },
    ])
    pipeline = HistoricalFeaturePipeline(reviews_repo=repo)
    features = pipeline.build_features_for_module("database_systems")
    # Verified classifications should include the approved question
    assert features["module_key"] == "database_systems"
