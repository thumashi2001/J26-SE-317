
import json
import tempfile
import unittest
from pathlib import Path

from services.question_classification_review_repository import (
    QuestionClassificationReviewRepository,
)
from services.question_classification_review_service import (
    QuestionClassificationReviewService,
)


class TestQuestionClassificationReviewService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.questions_path = self.root / "questions.json"
        self.modules_path = self.root / "modules.json"
        self.taxonomy_path = self.root / "taxonomies.json"
        self.reviews_path = self.root / "reviews.json"
        self.classifications_path = (
            self.root / "topic_classifications.json"
        )

        self.modules = {
            "schema_version": "1.0",
            "modules": [
                {
                    "module_key": "database_systems",
                    "module_code": "IT3020",
                    "module_name": "Database Systems",
                },
                {
                    "module_key": "software_architecture",
                    "module_code": "SE3020",
                    "module_name": "Software Architecture",
                },
            ],
        }

        self.taxonomies = {
            "schema_version": "1.0",
            "taxonomies": [
                {
                    "module_key": "database_systems",
                    "verification_status": "unverified",
                    "topics": [
                        {
                            "topic_id": "indexing",
                            "topic_name": "Database Indexing",
                            "subtopics": ["B-Tree", "Hash"],
                        }
                    ],
                },
                {
                    "module_key": "software_architecture",
                    "verification_status": "verified",
                    "topics": [
                        {
                            "topic_id": "patterns",
                            "topic_name": "Architectural Patterns",
                            "subtopics": [
                                "Layered",
                                "Microservices",
                            ],
                        }
                    ],
                },
            ],
        }

        self.questions = [
            {
                "question_id": "Q-AUTH-1",
                "paper_id": "P-2023",
                "module_code": "IT3020",
                "module_name": "Database Systems",
                "calendar_year": 2023,
                "semester": "1",
                "question_number": 1,
                "part_id": "Q1(a)",
                "question_text": "Explain B-tree indexes.",
                "marks": 5,
                "source_type": "authentic",
                "source_filename": "paper2023.pdf",
            },
            {
                "question_id": "Q-AUTH-2",
                "paper_id": "P-2023",
                "module_code": "IT3020",
                "module_name": "Database Systems",
                "calendar_year": 2023,
                "semester": "1",
                "question_number": 2,
                "part_id": "Q2",
                "question_text": "Write a query.",
                "marks": 10,
                "source_type": "authentic",
                "source_filename": "paper2023.pdf",
            },
            {
                "question_id": "Q-AUTH-3",
                "paper_id": "P-SE-2023",
                "module_code": "SE3020",
                "module_name": "Software Architecture",
                "calendar_year": 2023,
                "semester": "2",
                "question_number": 1,
                "part_id": "Q1",
                "question_text": (
                    "Compare layered vs microservices architecture."
                ),
                "marks": 15,
                "source_type": "authentic",
                "source_filename": "arch2023.pdf",
            },
            {
                "question_id": "Q-SYNTH-1",
                "paper_id": "P-SYNTH",
                "module_code": "IT3020",
                "module_name": "Database Systems",
                "calendar_year": 2024,
                "semester": "1",
                "question_number": 1,
                "part_id": "Q1",
                "question_text": "Synthetic mock question.",
                "marks": 5,
                "source_type": "synthetic",
                "source_filename": "synthetic.json",
            },
        ]

        self.classifications = {
            "schema_version": "1.0",
            "results": [
                {
                    "question_id": "Q-AUTH-1",
                    "valid": True,
                    "classification": {
                        "question_id": "Q-AUTH-1",
                        "module_key": "database_systems",
                        "topic_id": "indexing",
                        "subtopic": "B-Tree",
                        "classification_method": "rule_based",
                        "confidence_score": 0.85,
                        "verification_status": "unverified",
                    },
                },
                {
                    "question_id": "Q-AUTH-3",
                    "valid": True,
                    "classification": {
                        "question_id": "Q-AUTH-3",
                        "module_key": "software_architecture",
                        "topic_id": "patterns",
                        "subtopic": "Microservices",
                        "classification_method": "rule_based",
                        "confidence_score": 0.92,
                        "verification_status": "unverified",
                    },
                },
            ],
        }

        self.modules_path.write_text(
            json.dumps(self.modules),
            encoding="utf-8",
        )
        self.taxonomy_path.write_text(
            json.dumps(self.taxonomies),
            encoding="utf-8",
        )
        self.questions_path.write_text(
            json.dumps(self.questions),
            encoding="utf-8",
        )
        self.classifications_path.write_text(
            json.dumps(self.classifications),
            encoding="utf-8",
        )

        self.repository = QuestionClassificationReviewRepository(
            self.reviews_path
        )

        self.service = QuestionClassificationReviewService(
            questions_path=self.questions_path,
            modules_path=self.modules_path,
            taxonomy_path=self.taxonomy_path,
            repository=self.repository,
            classifications_path=self.classifications_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_excludes_synthetic_questions(self):
        result = self.service.list_review_candidates(
            include_reviewed=True
        )

        self.assertEqual(result["total"], 3)

        question_ids = [
            question["question_id"]
            for question in result["questions"]
        ]

        self.assertNotIn("Q-SYNTH-1", question_ids)
        self.assertIn("Q-AUTH-1", question_ids)
        self.assertIn("Q-AUTH-2", question_ids)
        self.assertIn("Q-AUTH-3", question_ids)

    def test_module_filter_and_statistics(self):
        result = self.service.list_review_candidates(
            module_key="database_systems",
            include_reviewed=True,
        )

        self.assertEqual(
            result["module_key"],
            "database_systems",
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["statistics"]["total"], 2)
        self.assertEqual(result["statistics"]["pending"], 2)
        self.assertEqual(result["statistics"]["approved"], 0)
        self.assertEqual(result["statistics"]["rejected"], 0)
        self.assertFalse(
            result["taxonomy_status"]["is_verified"]
        )

    def test_cannot_approve_when_taxonomy_unverified(self):
        candidates = self.service.list_review_candidates(
            module_key="database_systems",
            include_reviewed=True,
        )

        question = next(
            item
            for item in candidates["questions"]
            if item["question_id"] == "Q-AUTH-1"
        )

        self.assertFalse(question["can_approve"])
        self.assertFalse(question["taxonomy_verified"])

        with self.assertRaises(ValueError) as context:
            self.service.review(
                question_id="Q-AUTH-1",
                module_key="database_systems",
                topic_id="indexing",
                decision="approved",
                reviewer_id="lecturer_1",
                review_notes="Approved",
            )

        self.assertIn(
            "taxonomy is not verified",
            str(context.exception),
        )

    def test_reject_authentic_question_with_notes(self):
        saved = self.service.review(
            question_id="Q-AUTH-1",
            module_key="database_systems",
            topic_id="indexing",
            decision="rejected",
            reviewer_id="lecturer_1",
            review_notes=(
                "Topic classification is imprecise; "
                "relates to query execution."
            ),
        )

        self.assertEqual(saved["decision"], "rejected")
        self.assertEqual(saved["reviewer_id"], "lecturer_1")

        unreviewed = self.service.list_review_candidates(
            module_key="database_systems",
            include_reviewed=False,
        )

        self.assertEqual(unreviewed["total"], 1)
        self.assertEqual(
            unreviewed["statistics"]["pending"],
            1,
        )
        self.assertEqual(
            unreviewed["statistics"]["rejected"],
            1,
        )

        all_candidates = self.service.list_review_candidates(
            module_key="database_systems",
            include_reviewed=True,
        )

        question = next(
            item
            for item in all_candidates["questions"]
            if item["question_id"] == "Q-AUTH-1"
        )

        self.assertEqual(
            question["verification_status"],
            "rejected",
        )
        self.assertIsNotNone(question["review"])
        self.assertEqual(
            question["review"]["decision"],
            "rejected",
        )

    def test_rejection_requires_notes(self):
        with self.assertRaises(ValueError) as context:
            self.service.review(
                question_id="Q-AUTH-1",
                module_key="database_systems",
                topic_id="indexing",
                decision="rejected",
                reviewer_id="lecturer_1",
                review_notes="",
            )

        self.assertIn(
            "requires review notes",
            str(context.exception),
        )

    def test_approve_allowed_when_taxonomy_verified(self):
        candidates = self.service.list_review_candidates(
            module_key="software_architecture",
            include_reviewed=True,
        )

        question = next(
            item
            for item in candidates["questions"]
            if item["question_id"] == "Q-AUTH-3"
        )

        self.assertTrue(question["can_approve"])
        self.assertTrue(question["taxonomy_verified"])

        saved = self.service.review(
            question_id="Q-AUTH-3",
            module_key="software_architecture",
            topic_id="patterns",
            decision="approved",
            reviewer_id="lecturer_1",
            review_notes="Accurate classification",
        )

        self.assertEqual(saved["decision"], "approved")

        refreshed = self.service.list_review_candidates(
            module_key="software_architecture",
            include_reviewed=True,
        )

        reviewed_question = next(
            item
            for item in refreshed["questions"]
            if item["question_id"] == "Q-AUTH-3"
        )

        self.assertEqual(
            reviewed_question["verification_status"],
            "verified",
        )
        self.assertFalse(reviewed_question["can_approve"])

    # M15.3.2: Backend review integrity regression tests

    def test_cannot_review_unclassified_question(self):
        for decision, notes in (
            ("approved", "Looks correct"),
            ("rejected", "Incorrect topic"),
        ):
            with self.subTest(decision=decision):
                with self.assertRaises(ValueError) as context:
                    self.service.review(
                        question_id="Q-AUTH-2",
                        module_key="database_systems",
                        topic_id="indexing",
                        decision=decision,
                        reviewer_id="lecturer_1",
                        review_notes=notes,
                    )

                self.assertIn(
                    "no proposed topic classification",
                    str(context.exception),
                )

        self.assertIsNone(
            self.repository.get_review("Q-AUTH-2")
        )

    def test_rejects_mismatched_proposed_topic(self):
        with self.assertRaises(ValueError) as context:
            self.service.review(
                question_id="Q-AUTH-1",
                module_key="database_systems",
                topic_id="wrong_topic",
                decision="rejected",
                reviewer_id="lecturer_1",
                review_notes="Incorrect classification",
            )

        self.assertIn(
            "does not match the stored",
            str(context.exception),
        )

        self.assertIsNone(
            self.repository.get_review("Q-AUTH-1")
        )

    def test_null_topic_proposal_cannot_be_reviewed(self):
        self.classifications["results"].append({
            "question_id": "Q-AUTH-2",
            "valid": True,
            "classification": {
                "question_id": "Q-AUTH-2",
                "module_key": "database_systems",
                "topic_id": None,
                "subtopic": None,
                "classification_method": "unclassified",
                "confidence_score": None,
                "verification_status": "unverified",
            },
        })

        self.classifications_path.write_text(
            json.dumps(self.classifications),
            encoding="utf-8",
        )

        candidates = self.service.list_review_candidates(
            module_key="database_systems",
            include_reviewed=True,
        )

        question = next(
            item
            for item in candidates["questions"]
            if item["question_id"] == "Q-AUTH-2"
        )

        self.assertIsNone(
            question["proposed_classification"]["topic_id"]
        )
        self.assertFalse(question["can_approve"])

        with self.assertRaises(ValueError) as context:
            self.service.review(
                question_id="Q-AUTH-2",
                module_key="database_systems",
                topic_id="indexing",
                decision="rejected",
                reviewer_id="lecturer_1",
                review_notes="Not a valid proposal",
            )

        self.assertIn(
            "no proposed topic classification",
            str(context.exception),
        )

    def test_duplicate_lecturer_review_is_blocked(self):
        first_review = self.service.review(
            question_id="Q-AUTH-1",
            module_key="database_systems",
            topic_id="indexing",
            decision="rejected",
            reviewer_id="lecturer_1",
            review_notes="Topic needs correction",
        )

        self.assertEqual(
            first_review["decision"],
            "rejected",
        )

        with self.assertRaises(ValueError) as context:
            self.service.review(
                question_id="Q-AUTH-1",
                module_key="database_systems",
                topic_id="indexing",
                decision="rejected",
                reviewer_id="lecturer_2",
                review_notes="Second review attempt",
            )

        self.assertIn(
            "already has a review decision",
            str(context.exception),
        )
        self.assertEqual(
            len(self.repository.list_reviews()),
            1,
        )

    def test_unclassified_string_is_not_a_valid_topic(self):
        self.classifications["results"][0][
            "classification"
        ]["topic_id"] = "unclassified"

        self.classifications_path.write_text(
            json.dumps(self.classifications),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError) as context:
            self.service.review(
                question_id="Q-AUTH-1",
                module_key="database_systems",
                topic_id="indexing",
                decision="rejected",
                reviewer_id="lecturer_1",
                review_notes="No genuine topic proposal",
            )

        self.assertIn(
            "no proposed topic classification",
            str(context.exception),
        )

    def test_duplicate_classification_proposals_are_blocked(self):
        duplicate = {
            "question_id": "Q-AUTH-1",
            "valid": True,
            "classification": {
                "question_id": "Q-AUTH-1",
                "module_key": "database_systems",
                "topic_id": "indexing",
                "classification_method": "rule_based",
                "verification_status": "unverified",
            },
        }

        self.classifications["results"].append(duplicate)

        self.classifications_path.write_text(
            json.dumps(self.classifications),
            encoding="utf-8",
        )

        with self.assertRaises(ValueError) as context:
            self.service.review(
                question_id="Q-AUTH-1",
                module_key="database_systems",
                topic_id="indexing",
                decision="rejected",
                reviewer_id="lecturer_1",
                review_notes="Ambiguous proposal",
            )

        self.assertIn(
            "no proposed topic classification",
            str(context.exception),
        )

    def test_pagination(self):
        page1 = self.service.list_review_candidates(
            page=1,
            page_size=2,
            include_reviewed=True,
        )

        self.assertEqual(len(page1["questions"]), 2)
        self.assertEqual(page1["total_pages"], 2)

        page2 = self.service.list_review_candidates(
            page=2,
            page_size=2,
            include_reviewed=True,
        )

        self.assertEqual(len(page2["questions"]), 1)


if __name__ == "__main__":
    unittest.main()
