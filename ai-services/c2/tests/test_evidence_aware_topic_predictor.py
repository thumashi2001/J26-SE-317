
"""M12.1 - Evidence-aware topic predictor tests."""

from copy import deepcopy

from services.evidence_aware_topic_predictor import (
    EvidenceAwareTopicPredictor,
)


def example_analysis():
    return {
        "module_key": "database_systems",
        "total_questions": 20,
        "distinct_papers": 4,
        "distinct_years": ["2022", "2023"],
        "prediction_ready": True,
        "limitations": [],
        "topics": {
            "verified_classified_questions": 18,
            "without_verified_topic": 2,
            "statistics": [
                {
                    "topic_id": "sql",
                    "question_count": 12,
                    "extracted_marks": 60,
                },
                {
                    "topic_id": "indexing",
                    "question_count": 6,
                    "extracted_marks": 30,
                },
            ],
        },
        "excluded": {
            "synthetic_questions": 10,
            "other_source_questions": 0,
        },
    }


class FakeAnalyzer:
    def __init__(self, result):
        self.result = result

    def analyze(self, module_key):
        return deepcopy(self.result)


def predict(result=None):
    return EvidenceAwareTopicPredictor(
        analyzer=FakeAnalyzer(
            result if result is not None
            else example_analysis()
        )
    ).predict("database_systems")


def test_sufficient_evidence_allows_ranking():
    result = predict()
    assert result["prediction_ready"] is True
    assert result["status"] == "historical_ranking_available"
    assert len(result["study_priorities"]) == 2


def test_ranking_uses_verified_topic_counts():
    result = predict()
    assert result["study_priorities"][0]["topic_id"] == "sql"
    assert result["study_priorities"][0]["rank"] == 1
    assert result["study_priorities"][0][
        "share_of_verified_questions"
    ] == round(12 / 18, 4)


def test_no_future_probabilities():
    result = predict()
    assert result["future_exam_probabilities_available"] is False


def test_insufficient_papers_blocks_ranking():
    analysis = example_analysis()
    analysis["distinct_papers"] = 1
    analysis["prediction_ready"] = False

    result = predict(analysis)

    assert result["prediction_ready"] is False
    assert result["study_priorities"] == []


def test_low_verification_coverage_blocks_ranking():
    analysis = example_analysis()
    analysis["topics"]["verified_classified_questions"] = 5
    analysis["topics"]["without_verified_topic"] = 15

    result = predict(analysis)

    assert result["prediction_ready"] is False
    assert result["study_priorities"] == []
    assert result["historical_evidence"][
        "verified_topic_coverage"
    ] == 0.25


def test_zero_questions_handled():
    analysis = example_analysis()
    analysis["total_questions"] = 0
    analysis["distinct_papers"] = 0
    analysis["distinct_years"] = []
    analysis["prediction_ready"] = False
    analysis["topics"] = {
        "verified_classified_questions": 0,
        "without_verified_topic": 0,
        "statistics": [],
    }

    result = predict(analysis)

    assert result["prediction_ready"] is False
    assert result["topic_statistics"] == []
    assert result["historical_evidence"][
        "verified_topic_coverage"
    ] == 0.0


def test_synthetic_questions_are_not_used_in_ranking():
    result = predict()

    assert result["historical_evidence"][
        "excluded_synthetic_questions"
    ] == 10
    assert result["historical_evidence"][
        "authentic_questions"
    ] == 20


def test_original_analysis_not_mutated():
    analysis = example_analysis()
    original = deepcopy(analysis)

    predict(analysis)

    assert analysis == original
