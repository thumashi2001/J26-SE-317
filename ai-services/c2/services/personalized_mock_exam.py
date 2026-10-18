
"""M12.2.1 - Read-only authentic-question practice mock generation."""

import hashlib
import json
import random

from services.student_question_bank import StudentQuestionBank


class PersonalizedMockExam:
    MAX_QUESTIONS = 30
    MAX_TARGET_MARKS = 200

    def __init__(self, question_bank=None):
        self.bank = (
            question_bank
            if question_bank is not None
            else StudentQuestionBank()
        )

    def _load_module_questions(self, module_key):
        """Read all repository pages without changing stored data."""
        records = []
        page = 1

        while True:
            result = self.bank.list_questions(
                module_key=module_key,
                page=page,
                page_size=100,
            )

            if not isinstance(result, dict):
                raise ValueError("Invalid question bank response")

            batch = result.get("questions")

            if not isinstance(batch, list):
                raise ValueError("Invalid question list")

            records.extend(batch)

            total = result.get("total")
            if (
                isinstance(total, bool)
                or not isinstance(total, int)
                or total < 0
            ):
                raise ValueError("Invalid question count")

            if len(records) >= total:
                break

            if not batch:
                raise ValueError("Incomplete question bank pagination")

            page += 1

        return records

    @staticmethod
    def _eligible(question, module_key):
        if not isinstance(question, dict):
            return False

        marks = question.get("marks")
        question_id = question.get("question_id")
        question_text = question.get("question_text")

        return (
            question.get("module_key") == module_key
            and question.get("source_type") == "authentic"
            and isinstance(question_id, str)
            and bool(question_id.strip())
            and isinstance(question_text, str)
            and bool(question_text.strip())
            and not isinstance(marks, bool)
            and isinstance(marks, (int, float))
            and marks > 0
            and marks == int(marks)
            and question.get("marks_status") == "extracted"
        )

    def generate(
        self,
        module_key,
        target_marks=100,
        max_questions=20,
        preferred_topics=None,
        difficulty=None,
        seed=42,
    ):
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Valid module_key required")

        if (
            isinstance(target_marks, bool)
            or not isinstance(target_marks, int)
            or not 1 <= target_marks <= self.MAX_TARGET_MARKS
        ):
            raise ValueError("Invalid target_marks")

        if (
            isinstance(max_questions, bool)
            or not isinstance(max_questions, int)
            or not 1 <= max_questions <= self.MAX_QUESTIONS
        ):
            raise ValueError("Invalid max_questions")

        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")

        if preferred_topics is None:
            preferred_topics = []

        if (
            not isinstance(preferred_topics, list)
            or len(preferred_topics) > 30
            or any(
                not isinstance(topic, str) or not topic.strip()
                for topic in preferred_topics
            )
        ):
            raise ValueError("Invalid preferred_topics")

        if difficulty is not None and (
            not isinstance(difficulty, str)
            or not difficulty.strip()
        ):
            raise ValueError("Invalid difficulty")

        preferred_topics = list(dict.fromkeys(preferred_topics))

        raw_questions = self._load_module_questions(module_key)

        unique = {}
        for question in raw_questions:
            if self._eligible(question, module_key):
                unique.setdefault(question["question_id"], question)

        candidates = list(unique.values())

        # Only verified classifications may drive topic personalization.
        def verified_topic(question):
            if question.get("verification_status") == "verified":
                return question.get("topic_id")
            return None

        def matches_preferences(question):
            topic_match = (
                not preferred_topics
                or verified_topic(question) in preferred_topics
            )
            difficulty_match = (
                difficulty is None
                or question.get("difficulty") == difficulty
            )
            return topic_match and difficulty_match

        # Preferences are priorities, not mandatory restrictions.
        preferred = [
            question for question in candidates
            if matches_preferences(question)
        ]
        remaining = [
            question for question in candidates
            if not matches_preferences(question)
        ]

        rng = random.Random(seed)
        rng.shuffle(preferred)
        rng.shuffle(remaining)

        selected = []
        selected_marks = 0
        preferred_selected = 0

        for group_index, group in enumerate((preferred, remaining)):
            for question in group:
                if len(selected) >= max_questions:
                    break

                marks = int(question["marks"])

                # Do not modify extracted question marks.
                if selected_marks + marks > target_marks:
                    continue

                selected.append({
                    "question_id": question["question_id"],
                    "question_text": question["question_text"],
                    "marks": marks,
                    "topic_id": verified_topic(question),
                    "difficulty": question.get("difficulty"),
                    "source_type": "authentic",
                })

                selected_marks += marks

                if group_index == 0 and (
                    preferred_topics or difficulty is not None
                ):
                    preferred_selected += 1

        status = (
            "complete"
            if selected_marks == target_marks
            else "partial"
        )

        fingerprint = json.dumps(
            {
                "module_key": module_key,
                "seed": seed,
                "target_marks": target_marks,
                "max_questions": max_questions,
                "preferred_topics": preferred_topics,
                "difficulty": difficulty,
                "question_ids": [
                    question["question_id"] for question in selected
                ],
            },
            sort_keys=True,
        )

        mock_id = (
            "MOCK-"
            + hashlib.sha256(
                fingerprint.encode("utf-8")
            ).hexdigest()[:16]
        )

        limitations = []

        if status == "partial":
            limitations.append(
                "Available eligible questions could not fill "
                "the requested marks total."
            )

        if preferred_topics or difficulty is not None:
            limitations.append(
                "Requested preferences are prioritized but "
                "other eligible questions may be used."
            )

        limitations.append(
            "This is a practice question selection, not a "
            "verified official examination structure."
        )

        return {
            "mock_id": mock_id,
            "module_key": module_key,
            "status": status,
            "practice_only": True,
            "official_exam_structure_verified": False,
            "source_filter": "authentic",
            "target_marks": target_marks,
            "total_marks": selected_marks,
            "question_count": len(selected),
            "eligible_question_count": len(candidates),
            "preferred_question_count": preferred_selected,
            "personalization": {
                "preferred_topics": preferred_topics,
                "difficulty": difficulty,
                "method": "user_selected_preferences",
                "c1_diagnostic_integrated": False,
            },
            "questions": selected,
            "limitations": limitations,
        }
