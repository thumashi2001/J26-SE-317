
import tempfile
import unittest
from pathlib import Path

from services.question_classification_review_repository import (
    QuestionClassificationReviewRepository,
)


class TestQuestionClassificationReviewRepository(
    unittest.TestCase
):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.repository = (
            QuestionClassificationReviewRepository(
                Path(self.temp_dir.name) / "reviews.json"
            )
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def sample_review(self, **overrides):
        record = {
            "question_id": "IT3020-2023-Q1a",
            "module_key": "database_systems",
            "topic_id": "example_topic",
            "decision": "approved",
            "reviewer_id": "lecturer_001",
            "review_notes": "",
        }

        record.update(overrides)
        return record

    def test_empty_repository(self):
        self.assertEqual(
            self.repository.list_reviews(),
            [],
        )

    def test_saves_approved_review(self):
        saved = self.repository.save_review(
            self.sample_review()
        )

        self.assertEqual(
            saved["decision"],
            "approved",
        )

        self.assertEqual(
            saved["reviewer_id"],
            "lecturer_001",
        )

        self.assertIn(
            "reviewed_at",
            saved,
        )

    def test_retrieves_review(self):
        self.repository.save_review(
            self.sample_review()
        )

        result = self.repository.get_review(
            "IT3020-2023-Q1a"
        )

        self.assertIsNotNone(result)

    def test_rejects_duplicate_decisions(self):
        self.repository.save_review(
            self.sample_review()
        )

        with self.assertRaises(ValueError):
            self.repository.save_review(
                self.sample_review()
            )

    def test_rejection_requires_notes(self):
        with self.assertRaises(ValueError):
            self.repository.save_review(
                self.sample_review(
                    decision="rejected",
                    review_notes="",
                )
            )

    def test_rejects_invalid_decision(self):
        with self.assertRaises(ValueError):
            self.repository.save_review(
                self.sample_review(
                    decision="automatically_verified"
                )
            )

    def test_filters_reviews_by_module(self):
        self.repository.save_review(
            self.sample_review()
        )

        self.assertEqual(
            len(
                self.repository.list_reviews(
                    "database_systems"
                )
            ),
            1,
        )

        self.assertEqual(
            self.repository.list_reviews(
                "application_frameworks"
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
