import json
import sys
from pathlib import Path
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.batch_topic_classifier import BatchTopicClassifier
from services.topic_classification_validator import TopicClassificationValidator
from services.exam_pattern_analyzer import ExamPatternAnalyzer
from services.evidence_aware_topic_predictor import EvidenceAwareTopicPredictor


class DummyM17PredictionService:
    def __init__(self, low_conf=False, conf_value=0.25):
        self.low_conf = low_conf
        self.conf_value = conf_value

    def predict(self, module_key, question_text, threshold=0.38):
        if self.low_conf:
            return {
                "abstained": True,
                "confidence_score": self.conf_value,
                "abstention_threshold": threshold,
                "candidate_topic": "topic_a",
                "provisional_topic_id": "provisional_topic_a",
                "model_type": "svm",
            }
        return {
            "abstained": False,
            "confidence_score": 0.85,
            "abstention_threshold": threshold,
            "candidate_topic": "topic_a",
            "provisional_topic_id": "provisional_topic_a",
            "model_type": "svm",
        }


class MockTaxonomyForEvidence:
    def __init__(self, status="unverified"):
        self.status = status

    def get_module_taxonomy(self, module_key):
        if module_key != "software_project_management":
            return None
        return {
            "module_key": "software_project_management",
            "verification_status": self.status,
            "topics": [
                {
                    "topic_id": "spm_agile",
                    "topic_name": "Agile Methodologies",
                    "subtopics": ["Scrum", "Sprint Planning"],
                },
                {
                    "topic_id": "spm_estimation",
                    "topic_name": "Cost & Effort Estimation",
                    "subtopics": ["COCOMO", "Function Points"],
                },
            ],
        }

    def is_module_ready(self, module_key):
        return self.status == "verified" and module_key == "software_project_management"


class MockReviewRepository:
    def __init__(self, reviews=None):
        self._reviews = reviews or {}

    def get_review(self, question_id):
        return self._reviews.get(question_id)


def make_analyzer_fixture(tmp_path, questions, classifications):
    questions_path = tmp_path / "questions.json"
    classifications_path = tmp_path / "classifications.json"
    modules_path = tmp_path / "modules.json"

    questions_path.write_text(json.dumps(questions), encoding="utf-8")

    classifications_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "results": classifications,
        }),
        encoding="utf-8",
    )

    modules_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "modules": [
                {
                    "module_key": "software_project_management",
                    "module_code": "SE3080",
                    "module_name": "Software Project Management",
                },
                {
                    "module_key": "database_systems",
                    "module_code": "IT3020",
                    "module_name": "Database Systems",
                },
            ],
        }),
        encoding="utf-8",
    )

    return ExamPatternAnalyzer(
        questions_path=questions_path,
        classifications_path=classifications_path,
        modules_path=modules_path,
    )


# -------------------------------------------------------------
# Phase 7 Regression Tests
# -------------------------------------------------------------

def test_authentic_only_batch_classification():
    """Verify that synthetic questions are strictly excluded when authentic_only=True."""
    taxonomy = MockTaxonomyForEvidence(status="verified")
    validator = TopicClassificationValidator(taxonomy=taxonomy)
    batch = BatchTopicClassifier(
        classifier=DummyM17PredictionService(low_conf=False),
        validator=validator,
        authentic_only=True,
    )

    questions = [
        {
            "question_id": "AUTH-01",
            "module_key": "software_project_management",
            "question_text": "Describe Agile sprint ceremonies.",
            "source_type": "authentic",
        },
        {
            "question_id": "SYNTH-01",
            "module_key": "software_project_management",
            "question_text": "Calculate function points for project X.",
            "source_type": "synthetic",
        },
    ]

    result = batch.classify_questions(questions)
    summary = result["summary"]
    results = result["results"]

    # Only 1 question (the authentic one) should be in results
    assert summary["synthetic_excluded"] == 1
    assert len(results) == 1
    assert results[0]["question_id"] == "AUTH-01"


def test_m17_model_abstention():
    """Verify conservative model abstention sets unclassified and confidence_score=None."""
    taxonomy = MockTaxonomyForEvidence(status="verified")
    validator = TopicClassificationValidator(taxonomy=taxonomy)
    batch = BatchTopicClassifier(
        classifier=DummyM17PredictionService(low_conf=True, conf_value=0.22),
        validator=validator,
        authentic_only=True,
    )

    questions = [
        {
            "question_id": "AUTH-LOWCONF",
            "module_key": "software_project_management",
            "question_text": "General question with ambiguous topic wording.",
            "source_type": "authentic",
        }
    ]

    result = batch.classify_questions(questions)
    assert len(result["results"]) == 1
    rec = result["results"][0]

    assert rec["classification"]["classification_method"] == "unclassified"
    assert rec["classification"]["topic_id"] is None
    # Must be None to satisfy TopicClassificationValidator
    assert rec["classification"]["confidence_score"] is None
    assert rec["valid"] is True


def test_preservation_of_lecturer_review_decisions():
    """Verify that existing lecturer-verified classifications are not overwritten by model predictions."""
    taxonomy = MockTaxonomyForEvidence(status="verified")
    validator = TopicClassificationValidator(taxonomy=taxonomy)
    review_repo = MockReviewRepository({
        "AUTH-REV-01": {
            "decision": "approved",
            "topic_id": "spm_agile",
            "subtopic": "Scrum",
            "reviewer_id": "lecturer_sliit_01",
            "reviewed_at": "2026-03-01T10:00:00Z",
            "review_notes": "Confirmed topic alignment with SPM Week 3 syllabus.",
        }
    })
    batch = BatchTopicClassifier(
        classifier=DummyM17PredictionService(low_conf=False),
        validator=validator,
        review_repository=review_repo,
        authentic_only=True,
    )

    question = {
        "question_id": "AUTH-REV-01",
        "module_key": "software_project_management",
        "question_text": "Describe Agile sprint planning.",
        "source_type": "authentic",
    }

    result = batch.classify_questions([question])
    rec = result["results"][0]

    assert rec["classification"]["verification_status"] == "verified"
    assert rec["classification"]["topic_id"] == "spm_agile"
    assert rec["classification"]["review_metadata"]["reviewer_id"] == "lecturer_sliit_01"


def test_idempotent_classification_reruns():
    """Verify rerun produces exact same output."""
    taxonomy = MockTaxonomyForEvidence(status="verified")
    validator = TopicClassificationValidator(taxonomy=taxonomy)
    batch = BatchTopicClassifier(
        classifier=DummyM17PredictionService(low_conf=True),
        validator=validator,
    )

    questions = [
        {
            "question_id": "AUTH-IDEM-01",
            "module_key": "software_project_management",
            "question_text": "Explain earned value analysis.",
            "source_type": "authentic",
        }
    ]

    run1 = batch.classify_questions(questions)
    run2 = batch.classify_questions(questions)

    assert run1["summary"] == run2["summary"]
    assert run1["results"][0]["classification"]["topic_id"] == run2["results"][0]["classification"]["topic_id"]
    assert run1["results"][0]["classification"]["classification_method"] == run2["results"][0]["classification"]["classification_method"]


def test_unverified_taxonomy_approval_restrictions():
    """Verify unverified taxonomies are locked and cannot be marked as ready."""
    unverified_tax = MockTaxonomyForEvidence(status="unverified")
    assert unverified_tax.is_module_ready("software_project_management") is False

    verified_tax = MockTaxonomyForEvidence(status="verified")
    assert verified_tax.is_module_ready("software_project_management") is True


def test_parent_leaf_question_double_count_prevention(tmp_path):
    """Verify that parent questions with child subquestions are not counted twice."""
    # Question hierarchy: Parent Q1 (20 marks) with children Q1(a) (10 marks) and Q1(b) (10 marks)
    questions = [
        {
            "question_id": "SE3080-Q1",
            "module_code": "SE3080",
            "question_text": "Answer both subquestions below.",
            "marks": 20,
            "marks_status": "extracted",
            "parent_id": None,
            "paper_id": "PAPER-2022",
            "calendar_year": 2022,
            "source_type": "authentic",
        },
        {
            "question_id": "SE3080-Q1(a)",
            "module_code": "SE3080",
            "question_text": "Explain Scrum.",
            "marks": 10,
            "marks_status": "extracted",
            "parent_id": "SE3080-Q1",
            "paper_id": "PAPER-2022",
            "calendar_year": 2022,
            "source_type": "authentic",
        },
        {
            "question_id": "SE3080-Q1(b)",
            "module_code": "SE3080",
            "question_text": "Explain Sprint Backlog.",
            "marks": 10,
            "marks_status": "extracted",
            "parent_id": "SE3080-Q1",
            "paper_id": "PAPER-2022",
            "calendar_year": 2022,
            "source_type": "authentic",
        },
    ]

    classifications = [
        {
            "question_id": "SE3080-Q1(a)",
            "valid": True,
            "classification": {
                "question_id": "SE3080-Q1(a)",
                "module_key": "software_project_management",
                "topic_id": "spm_agile",
                "verification_status": "verified",
            },
        },
        {
            "question_id": "SE3080-Q1(b)",
            "valid": True,
            "classification": {
                "question_id": "SE3080-Q1(b)",
                "module_key": "software_project_management",
                "topic_id": "spm_agile",
                "verification_status": "verified",
            },
        },
    ]

    analyzer = make_analyzer_fixture(tmp_path, questions, classifications)
    stats = analyzer.analyze("software_project_management")

    assert stats["total_questions"] == 2  # Only the 2 leaf questions counted!
    assert stats["marks"]["sum_of_extracted_question_marks"] == 20.0  # Not 40.0!


def test_distinct_paper_counting(tmp_path):
    """Verify distinct paper IDs are counted correctly."""
    questions = [
        {"question_id": "Q1", "module_code": "SE3080", "paper_id": "P1", "calendar_year": 2021, "source_type": "authentic"},
        {"question_id": "Q2", "module_code": "SE3080", "paper_id": "P1", "calendar_year": 2021, "source_type": "authentic"},
        {"question_id": "Q3", "module_code": "SE3080", "paper_id": "P2", "calendar_year": 2022, "source_type": "authentic"},
    ]

    analyzer = make_analyzer_fixture(tmp_path, questions, [])
    stats = analyzer.analyze("software_project_management")

    assert stats["distinct_papers"] == 2
    assert set(stats["distinct_years"]) == {"2021", "2022"}
    assert len(stats["papers_inventory"]) == 2


def test_year_based_historical_trends_and_missing_years(tmp_path):
    """Verify year occurrences populate 0 for administered years with zero occurrences, and track unavailable years."""
    questions = [
        {
            "question_id": "Q1",
            "module_code": "SE3080",
            "paper_id": "P2020",
            "calendar_year": 2020,
            "source_type": "authentic",
        },
        {
            "question_id": "Q2",
            "module_code": "SE3080",
            "paper_id": "P2022",
            "calendar_year": 2022,
            "source_type": "authentic",
        },
    ]

    classifications = [
        {
            "question_id": "Q1",
            "valid": True,
            "classification": {
                "question_id": "Q1",
                "module_key": "software_project_management",
                "topic_id": "topic_a",
                "verification_status": "verified",
            },
        },
        {
            "question_id": "Q2",
            "valid": True,
            "classification": {
                "question_id": "Q2",
                "module_key": "software_project_management",
                "topic_id": "topic_b",
                "verification_status": "verified",
            },
        },
    ]

    analyzer = make_analyzer_fixture(tmp_path, questions, classifications)
    stats = analyzer.analyze("software_project_management")

    # 2021 was between 2020 and 2022 and had no papers
    assert "2021" in stats["unavailable_years"]

    topic_a = next(t for t in stats["topics"]["statistics"] if t["topic_id"] == "topic_a")
    # For topic_a: 1 in 2020, explicitly 0 in 2022
    assert topic_a["yearly_occurrences"]["2020"] == 1
    assert topic_a["yearly_occurrences"]["2022"] == 0


def test_ambiguous_marks_exclusion(tmp_path):
    """Verify that ambiguous/null marks are excluded from mark sums."""
    questions = [
        {"question_id": "Q1", "module_code": "SE3080", "marks": 15, "marks_status": "extracted", "paper_id": "P1", "source_type": "authentic"},
        {"question_id": "Q2", "module_code": "SE3080", "marks": None, "marks_status": "missing", "paper_id": "P1", "source_type": "authentic"},
        {"question_id": "Q3", "module_code": "SE3080", "marks": "ambiguous", "marks_status": "unverified", "paper_id": "P1", "source_type": "authentic"},
    ]

    analyzer = make_analyzer_fixture(tmp_path, questions, [])
    stats = analyzer.analyze("software_project_management")

    assert stats["marks"]["sum_of_extracted_question_marks"] == 15.0
    assert stats["marks"]["ambiguous_marks_questions"] == 2


def test_verified_vs_provisional_evidence_separation(tmp_path):
    """Verify provisional classifications are not merged into verified historical topic evidence."""
    questions = [
        {"question_id": "Q1", "module_code": "SE3080", "paper_id": "P1", "source_type": "authentic"},
        {"question_id": "Q2", "module_code": "SE3080", "paper_id": "P1", "source_type": "authentic"},
    ]

    classifications = [
        {
            "question_id": "Q1",
            "valid": True,
            "classification": {
                "question_id": "Q1",
                "module_key": "software_project_management",
                "topic_id": "topic_verified",
                "verification_status": "verified",
                "classification_method": "verified",
            },
        },
        {
            "question_id": "Q2",
            "valid": True,
            "classification": {
                "question_id": "Q2",
                "module_key": "software_project_management",
                "topic_id": "provisional_topic_x",
                "verification_status": "unverified",
                "classification_method": "m17_provisional",
            },
        },
    ]

    analyzer = make_analyzer_fixture(tmp_path, questions, classifications)
    stats = analyzer.analyze("software_project_management")

    assert stats["topics"]["verified_classified_questions"] == 1
    assert stats["topics"]["provisional_classified_questions"] == 1

    # topic_statistics must only include verified topics
    assert len(stats["topics"]["statistics"]) == 1
    assert stats["topics"]["statistics"][0]["topic_id"] == "topic_verified"

    # provisional_statistics contains provisional topics
    assert len(stats["topics"]["provisional_statistics"]) == 1
    assert stats["topics"]["provisional_statistics"][0]["topic_id"] == "provisional_topic_x"


def test_no_fabricated_probabilities(tmp_path):
    """Verify that topic predictions never output future probabilities."""
    analyzer = make_analyzer_fixture(tmp_path, [], [])
    predictor = EvidenceAwareTopicPredictor(analyzer=analyzer)
    result = predictor.predict("software_project_management")

    assert result["future_exam_probabilities_available"] is False
    assert "probability" not in result
    assert "predicted_percentage" not in result
    assert "disclaimer" in result
    assert "historical_evidence" in result


def test_module_isolation(tmp_path):
    """Verify module isolation in pattern analyzer."""
    questions = [
        {"question_id": "DB1", "module_code": "IT3020", "paper_id": "P1", "source_type": "authentic"},
        {"question_id": "SPM1", "module_code": "SE3080", "paper_id": "P2", "source_type": "authentic"},
    ]

    analyzer = make_analyzer_fixture(tmp_path, questions, [])
    db_stats = analyzer.analyze("database_systems")
    spm_stats = analyzer.analyze("software_project_management")

    assert db_stats["total_questions"] == 1
    assert spm_stats["total_questions"] == 1
