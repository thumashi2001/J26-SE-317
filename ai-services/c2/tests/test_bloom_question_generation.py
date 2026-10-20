"""Unit and integration tests for M21 Bloom's Taxonomy Question Generation System."""

import tempfile
import unittest
from pathlib import Path

from services.bloom_question_generator import BloomQuestionGenerator
from services.bloom_question_validator import BloomQuestionValidator
from services.generated_question_repository import GeneratedQuestionRepository
from services.bloom_classifier_experiment import run_bloom_classification_experiment


class TestBloomQuestionGeneration(unittest.TestCase):
    def setUp(self):
        self.generator = BloomQuestionGenerator()
        self.validator = BloomQuestionValidator()

    def test_database_systems_normalization_apply_generation(self):
        """Verify the required Viva baseline: Database Systems, Normalization, Apply, 10 marks."""
        q = self.generator.generate_question(
            module_key="database_systems",
            topic_id="database_normalization_and_schema_design",
            bloom_level="apply",
            difficulty="medium",
            question_type="structured",
            marks=10,
        )

        self.assertIsNotNone(q)
        self.assertTrue(q["question_id"].startswith("GEN-SE3060-"))
        self.assertEqual(q["bloom_level"], "apply")
        self.assertEqual(q["module_key"], "database_systems")
        self.assertEqual(q["marks"], 10)
        self.assertFalse(q["is_authentic"])  # Research integrity safeguard

        # Check subquestions marks summation
        subquestions = q.get("subquestions", [])
        self.assertTrue(len(subquestions) >= 2)
        total_sub_marks = sum(sq["marks"] for sq in subquestions)
        self.assertEqual(total_sub_marks, 10)

        # Check validation report
        val = q.get("validation", {})
        self.assertTrue(val.get("is_valid"))
        self.assertEqual(val["curriculum_alignment"]["status"], "pass")
        self.assertEqual(val["bloom_alignment"]["status"], "pass")
        self.assertIn("apply", val["bloom_alignment"]["requested_bloom"])

    def test_cognitive_differentiation_across_bloom_levels(self):
        """Verify changing Bloom level produces meaningfully distinct cognitive operations."""
        levels = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        detected_verbs_by_level = {}

        for lvl in levels:
            q = self.generator.generate_question(
                module_key="database_systems",
                topic_id="database_normalization_and_schema_design",
                bloom_level=lvl,
                difficulty="medium",
                question_type="structured",
                marks=10,
            )
            val = q["validation"]
            verbs = val["bloom_alignment"]["detected_verbs"]
            detected_verbs_by_level[lvl] = verbs
            self.assertTrue(len(verbs) > 0, f"Expected action verbs for level '{lvl}'")

        # Verify action verbs are level-appropriate
        self.assertTrue(
            any(v in ["define", "list", "state"] for v in detected_verbs_by_level["remember"])
        )
        self.assertTrue(
            any(v in ["explain", "describe", "contrast"] for v in detected_verbs_by_level["understand"])
        )
        self.assertTrue(
            any(v in ["apply", "decompose", "write", "demonstrate"] for v in detected_verbs_by_level["apply"])
        )
        self.assertTrue(
            any(v in ["analyze", "deconstruct", "diagnose"] for v in detected_verbs_by_level["analyze"])
        )
        self.assertTrue(
            any(v in ["evaluate", "critique", "justify", "defend"] for v in detected_verbs_by_level["evaluate"])
        )
        self.assertTrue(
            any(v in ["design", "construct", "formulate"] for v in detected_verbs_by_level["create"])
        )

    def test_invalid_parameters_rejected(self):
        """Verify that invalid modules, Bloom levels, or negative marks raise ValueError."""
        with self.assertRaises(ValueError):
            self.generator.generate_question(
                module_key="invalid_unknown_module",
                topic_id="some_topic",
            )

        with self.assertRaises(ValueError):
            self.generator.generate_question(
                module_key="database_systems",
                topic_id="database_normalization_and_schema_design",
                bloom_level="synthesize_magic",  # invalid
            )

        with self.assertRaises(ValueError):
            self.generator.generate_question(
                module_key="database_systems",
                topic_id="database_normalization_and_schema_design",
                marks=-5,  # negative
            )

    def test_all_eight_modules_supported(self):
        """Verify topic listing and generation succeeds for all 8 Year 3 SE modules."""
        modules = [
            "database_systems",
            "software_architecture",
            "software_engineering_process_quality_management",
            "case_studies_software_engineering",
            "application_frameworks",
            "distributed_systems",
            "software_project_management",
            "user_experience_engineering",
        ]


        for mod_key in modules:
            topics = self.generator.get_module_topics(mod_key)
            self.assertTrue(len(topics) > 0, f"No topics found for module '{mod_key}'")
            first_topic = topics[0]["topic_id"]

            q = self.generator.generate_question(
                module_key=mod_key,
                topic_id=first_topic,
                bloom_level="apply",
                marks=10,
            )
            self.assertEqual(q["module_key"], mod_key)
            self.assertFalse(q["is_authentic"])
            self.assertEqual(q["marks"], 10)

    def test_isolated_repository_persistence(self):
        """Verify approved questions are persisted separately with strict research safeguards."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "test_approved_questions.json"
            repo = GeneratedQuestionRepository(storage_path=tmp_path)

            q_data = {
                "question_id": "GEN-SE3060-test1234",
                "question_text": "Sample normalization question statement.",
                "module_key": "database_systems",
                "topic_id": "database_normalization_and_schema_design",
                "bloom_level": "apply",
                "marks": 10,
            }

            saved = repo.save_approved_question(
                question_data=q_data,
                reviewer_id="lecturer_se_317",
                review_notes="Curriculum compliant 3NF exercise.",
            )

            self.assertEqual(saved["approval_status"], "approved")
            self.assertEqual(saved["reviewer_id"], "lecturer_se_317")
            self.assertFalse(saved["is_authentic"])  # STRICT SAFEGUARD

            # Verify persistence upon reading back
            loaded = repo.list_approved_questions(module_key="database_systems")
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["question_id"], "GEN-SE3060-test1234")
            self.assertFalse(loaded[0]["is_authentic"])

    def test_bloom_classifier_experiment_execution(self):
        """Verify Bloom classifier experiment executes, writes report, and reports honest metrics."""
        report = run_bloom_classification_experiment()
        self.assertIn("overall_metrics", report)
        self.assertGreater(report["overall_metrics"]["accuracy"], 0.20)
        self.assertIn("per_class_metrics", report)
        self.assertIn("confusion_matrix", report)
        # Check authentic evaluation status
        self.assertEqual(report["authentic_evaluation"]["status"], "not_evaluable")
        self.assertEqual(report["authentic_evaluation"]["authentic_verified_bloom_labels"], 0)


if __name__ == "__main__":
    unittest.main()
