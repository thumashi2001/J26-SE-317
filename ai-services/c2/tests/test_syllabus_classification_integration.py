
import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

# Add ai-services/c2 to Python's module search path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Import C2 services after configuring the path.
from services.topic_taxonomy import TopicTaxonomy
from services.topic_classifier import TopicClassifier
from services.topic_classification_validator import TopicClassificationValidator
from services.batch_topic_classifier import BatchTopicClassifier
from services.classification_report import ClassificationReport



def run_tests():
    print("\n--- M7.2.5 SYLLABUS CLASSIFICATION INTEGRATION TEST ---")

    sample_data = {
        "schema_version": "1.0",
        "taxonomies": [
            {
                "module_key": "database_systems",
                "verification_status": "verified",
                "topics": [
                    {
                        "topic_id": "DB_TEST_01",
                        "topic_name": "Database Normalization",
                        "subtopics": [
                            "First Normal Form",
                            "Second Normal Form",
                            "Third Normal Form"
                        ]
                    }
                ]
            }
        ]
    }

    original_data = deepcopy(sample_data)

    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_taxonomy.json"

        config_path.write_text(
            json.dumps(sample_data, indent=2),
            encoding="utf-8"
        )

        taxonomy = TopicTaxonomy(config_path=config_path)

        assert taxonomy.is_module_ready("database_systems")
        assert len(taxonomy.get_topics("database_systems")) == 1
        print("PASS: populated taxonomy loaded")

        classifier = TopicClassifier(
            taxonomy=taxonomy,
            min_confidence=0.2
        )

        validator = TopicClassificationValidator(
            taxonomy=taxonomy
        )

        matching_question = {
            "question_id": "M725-Q1",
            "module_key": "database_systems",
            "question_text": (
                "Explain Database Normalization and "
                "Third Normal Form."
            )
        }

        unmatched_question = {
            "question_id": "M725-Q2",
            "module_key": "database_systems",
            "question_text": (
                "Describe cloud deployment infrastructure."
            )
        }

        classified = classifier.classify(**matching_question)

        assert classified["topic_id"] == "DB_TEST_01"
        assert classified["classification_method"] == "rule_based"
        assert 0 <= classified["confidence_score"] <= 1
        print("PASS: matching topic classified")

        validation = validator.validate(classified)
        assert validation["valid"], validation["errors"]
        print("PASS: classified record validated")

        unclassified = classifier.classify(**unmatched_question)

        assert unclassified["topic_id"] is None
        assert unclassified["classification_method"] == "unclassified"
        print("PASS: unmatched question handled")

        batch = BatchTopicClassifier(
            classifier=classifier,
            validator=validator
        )

        questions = [
            matching_question,
            unmatched_question
        ]

        original_questions = deepcopy(questions)

        batch_result = batch.classify_questions(questions)
        summary = batch_result["summary"]

        assert summary["total_questions"] == 2
        assert summary["classified"] == 1
        assert summary["unclassified"] == 1
        assert summary["invalid"] == 0
        assert len(batch_result["results"]) == 2
        print("PASS: batch classification integration")

        assert (
            summary["classified"]
            + summary["unclassified"]
            + summary["invalid"]
            == summary["total_questions"]
        )
        print("PASS: classification summary consistency")

        coverage = (
            summary["classified"]
            / summary["total_questions"]
            * 100
        )

        assert coverage == 50.0
        print("PASS: classification coverage calculation")
        
        # M7.2.5: Test the actual M6.5 reporting service.
        report_generator = ClassificationReport()

        original_batch_result = deepcopy(batch_result)

        report = report_generator.generate(
            batch_result,
            questions=questions
        )

        assert report["schema_version"] == "1.0"
        assert isinstance(report["summary"], dict)
        assert isinstance(report["modules"], dict)
        assert isinstance(report["warnings"], list)
        print("PASS: classification report generated")

        report_summary = report["summary"]

        assert report_summary["total_questions"] == 2
        assert report_summary["classified"] == 1
        assert report_summary["unclassified"] == 1
        assert report_summary["invalid"] == 0
        print("PASS: report summary consistency")

        assert (
            report_summary["classification_coverage_percentage"]
            == 50.0
        )
        assert report_summary["unclassified_percentage"] == 50.0
        assert report_summary["invalid_percentage"] == 0.0
        print("PASS: report coverage percentages")

        module_report = report["modules"]["database_systems"]

        assert module_report["total_questions"] == 2
        assert module_report["classified"] == 1
        assert module_report["unclassified"] == 1
        assert module_report["invalid"] == 0
        assert (
            module_report["classification_coverage_percentage"]
            == 50.0
        )
        print("PASS: module-level coverage reporting")

        assert any(
            "unclassified" in warning.lower()
            for warning in report["warnings"]
        )
        print("PASS: classification warnings preserved")

        assert batch_result == original_batch_result
        assert questions == original_questions
        print("PASS: reporting does not modify source data")

        # Verify reporting also handles an empty batch.
        empty_report = report_generator.generate(
            {
                "summary": {
                    "total_questions": 0,
                    "classified": 0,
                    "unclassified": 0,
                    "invalid": 0
                },
                "results": []
            },
            questions=[]
        )

        assert empty_report["summary"]["total_questions"] == 0
        assert (
            empty_report["summary"][
                "classification_coverage_percentage"
            ] == 0.0
        )
        assert empty_report["modules"] == {}
        assert empty_report["warnings"]
        print("PASS: empty classification report handling")

        # Reject inconsistent question/result counts.
        try:
            report_generator.generate(
                batch_result,
                questions=[matching_question]
            )
        except ValueError:
            print("PASS: inconsistent report input rejected")
        else:
            raise AssertionError(
                "Expected mismatched question count to be rejected"
            )


        # Check that unverified topics cannot be classified.
        unverified_data = deepcopy(sample_data)
        unverified_data["taxonomies"][0][
            "verification_status"
        ] = "unverified"

        unverified_path = (
            Path(temp_dir) / "unverified_taxonomy.json"
        )

        unverified_path.write_text(
            json.dumps(unverified_data, indent=2),
            encoding="utf-8"
        )

        unverified_taxonomy = TopicTaxonomy(
            config_path=unverified_path
        )

        unverified_classifier = TopicClassifier(
            taxonomy=unverified_taxonomy,
            min_confidence=0.2
        )

        result = unverified_classifier.classify(
            **matching_question
        )

        assert result["classification_method"] == "unclassified"
        assert result["topic_id"] is None
        assert result["verification_status"] == "unverified"
        print("PASS: unverified taxonomy safeguards")

        # Ensure input data has not been modified.
        assert sample_data == original_data
        assert questions == original_questions

        saved_data = json.loads(
            config_path.read_text(encoding="utf-8")
        )

        assert saved_data == original_data
        print("PASS: original taxonomy and questions unchanged")

    print("\n--- CLASSIFICATION SUMMARY ---")
    print("Total questions:", summary["total_questions"])
    print("Classified:", summary["classified"])
    print("Unclassified:", summary["unclassified"])
    print("Invalid:", summary["invalid"])
    print(f"Classification coverage: {coverage:.1f}%")

    print("\nAll M7.2.5 integration tests passed.")


if __name__ == "__main__":
    run_tests()
