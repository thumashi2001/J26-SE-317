"""Tests for M16 synthetic question development generation."""

import unittest

from services.m16_question_generator import M16QuestionGenerator


class TestM16QuestionGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.generator = M16QuestionGenerator()

    def test_generates_eight_modules_and_800_questions(self):
        result = self.generator.generate(seed=42, max_per_module=100)
        self.assertEqual(len(result["modules"]), 8)
        self.assertEqual(result["total_questions"], 800)
        for module in result["modules"]:
            self.assertEqual(module["question_count"], 100)
            self.assertTrue(module["target_reached"])

    def test_respects_max_per_module(self):
        result = self.generator.generate(seed=42, max_per_module=50)
        self.assertEqual(result["total_questions"], 400)
        for module in result["modules"]:
            self.assertEqual(module["question_count"], 50)
            self.assertTrue(module["target_reached"])

    def test_reports_shortfall_when_target_exceeds_available(self):
        result = self.generator.generate(seed=42, max_per_module=150)
        self.assertEqual(result["total_questions"], 800)
        for module in result["modules"]:
            self.assertEqual(module["question_count"], 100)
            self.assertFalse(module["target_reached"])
            self.assertEqual(module["available_candidate_count"], 100)

    def test_deterministic_generation(self):
        first = self.generator.generate(seed=42)
        second = self.generator.generate(seed=42)
        self.assertEqual(first, second)

    def test_different_seeds_produce_different_order(self):
        first = self.generator.generate(seed=42, max_per_module=50)
        second = self.generator.generate(seed=999, max_per_module=50)
        first_ids = [q["question_id"] for q in first["modules"][0]["questions"]]
        second_ids = [q["question_id"] for q in second["modules"][0]["questions"]]
        self.assertNotEqual(first_ids, second_ids)

    def test_unique_ids_and_text(self):
        result = self.generator.generate(seed=42)

        questions = [
            question
            for module in result["modules"]
            for question in module["questions"]
        ]

        ids = [q["question_id"] for q in questions]
        texts = [
            " ".join(q["question_text"].casefold().split())
            for q in questions
        ]

        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(texts), len(set(texts)))

    def test_provenance_is_unverified_synthetic(self):
        result = self.generator.generate(seed=42)

        for module in result["modules"]:
            for question in module["questions"]:
                self.assertEqual(
                    question["source_type"], "synthetic"
                )
                self.assertEqual(
                    question["verification_status"], "unverified"
                )
                self.assertEqual(
                    question["label_source"], "synthetic_generation"
                )
                self.assertEqual(
                    question["generation_mode"], "development_fixture"
                )
                self.assertTrue(question.get("provisional_topic"))
                self.assertIn("scenario_group_id", question)
                self.assertIn("task_group_id", question)
                self.assertIn("template_family_id", question)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.generator.generate(seed=True)

        with self.assertRaises(ValueError):
            self.generator.generate(seed="42")

        with self.assertRaises(ValueError):
            self.generator.generate(max_per_module=0)

        with self.assertRaises(ValueError):
            self.generator.generate(max_per_module=-10)

        with self.assertRaises(ValueError):
            self.generator.generate(max_per_module=True)


if __name__ == "__main__":
    unittest.main()
