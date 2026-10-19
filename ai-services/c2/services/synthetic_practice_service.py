"""Synthetic Practice Service — C2 Student Exam Intelligence.

Provides practice examination generation from the M16 synthetic question bank
across all eight supported Year 3 Software Engineering modules.

Safeguards:
- Never mixes synthetic questions with the authentic question repository.
- Never fabricates marks, difficulty ratings, or verified topic classifications.
- Questions are explicitly flagged with source_type='synthetic',
  verification_status='unverified', and marks=None (unassessed).
"""

import hashlib
import json
import random
from pathlib import Path

C2_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_M16_DIR = C2_ROOT / "datasets" / "synthetic" / "m16" / "per_module"

MODULE_NAMES = {
    "application_frameworks": "Application Frameworks",
    "case_studies_software_engineering": "Case Studies in Software Engineering",
    "database_systems": "Database Systems",
    "distributed_systems": "Distributed Systems",
    "software_architecture": "Software Architecture",
    "software_engineering_process_quality_management": "Software Engineering Process & Quality Management",
    "software_project_management": "Software Project Management",
    "user_experience_engineering": "User Experience Engineering",
}

VALID_MODULE_KEYS = set(MODULE_NAMES.keys())


class SyntheticPracticeService:
    """Generates synthetic practice question sets for student exam intelligence."""

    def __init__(self, synthetic_dir=None):
        self.synthetic_dir = Path(synthetic_dir or SYNTHETIC_M16_DIR)

    def load_module_questions(self, module_key: str) -> list[dict]:
        """Load questions from the module's M16 synthetic dataset file."""
        if not isinstance(module_key, str) or module_key not in VALID_MODULE_KEYS:
            raise ValueError(f"Unsupported module key: {module_key}")

        file_path = self.synthetic_dir / f"{module_key}.json"
        if not file_path.exists():
            raise FileNotFoundError(
                f"Synthetic dataset file not found for module '{module_key}' at {file_path}"
            )

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        questions = data.get("questions", [])
        if not isinstance(questions, list):
            raise ValueError(f"Corrupt synthetic dataset for module '{module_key}'")

        return questions

    def generate_practice_paper(
        self,
        module_key: str,
        question_count: int = 5,
        seed: int = 42,
    ) -> dict:
        """Generate a synthetic practice paper with unassessed marks and unverified status."""
        if not isinstance(module_key, str) or module_key not in VALID_MODULE_KEYS:
            raise ValueError(f"Unsupported module key: {module_key}")

        if not isinstance(question_count, int) or question_count < 1 or question_count > 20:
            raise ValueError("question_count must be an integer between 1 and 20")

        if not isinstance(seed, int):
            raise ValueError("seed must be an integer")

        pool = self.load_module_questions(module_key)
        module_name = MODULE_NAMES.get(module_key, module_key.replace("_", " ").title())

        if not pool:
            return {
                "paper_id": f"SYN-EMPTY-{module_key.upper()}",
                "module_key": module_key,
                "module_name": module_name,
                "practice_mode": "synthetic_experimental",
                "source_type": "synthetic",
                "verification_status": "unverified",
                "question_count": 0,
                "total_marks": None,
                "has_unassessed_marks": True,
                "questions": [],
                "disclaimer": "No synthetic questions available for this module.",
                "limitations": ["No synthetic questions found."],
            }

        rng = random.Random(seed)
        k = min(question_count, len(pool))
        # Deterministically sample k questions
        sample_indices = sorted(rng.sample(range(len(pool)), k))
        sampled_raw = [pool[i] for i in sample_indices]

        sampled_questions = []
        for index, q in enumerate(sampled_raw, start=1):
            q_id = q.get("question_id") or f"SYN-{module_key.upper()}-{index:03d}"
            sampled_questions.append({
                "question_id": q_id,
                "module_key": module_key,
                "module_name": module_name,
                "question_text": q.get("question_text", ""),
                "topic": q.get("topic"),
                "topic_id": q.get("topic_id"),
                "bloom_level": q.get("bloom_level"),
                "difficulty": q.get("difficulty", "unassessed"),
                "marks": None,  # Strictly None: never fabricate numeric marks!
                "marks_status": "unassessed",
                "source_type": "synthetic",
                "verification_status": "unverified",
                "academic_quality_status": q.get("academic_quality_status", "not_evaluated"),
                "human_review_status": q.get("human_review_status", "pending"),
                "provisional_topic": q.get("provisional_topic", True),
                "generation_mode": q.get("generation_mode", "development_fixture"),
            })

        digest_payload = f"{module_key}|{seed}|{len(sampled_questions)}"
        digest = hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()[:8].upper()
        paper_id = f"SYN-PRACTICE-{module_key.upper()}-{digest}"

        return {
            "paper_id": paper_id,
            "module_key": module_key,
            "module_name": module_name,
            "practice_mode": "synthetic_experimental",
            "source_type": "synthetic",
            "verification_status": "unverified",
            "academic_review_status": "unverified",
            "question_count": len(sampled_questions),
            "total_marks": None,  # Marks are unassessed
            "has_unassessed_marks": True,
            "seed": seed,
            "questions": sampled_questions,
            "disclaimer": (
                "Synthetic Practice Questions are drawn from the M16 development dataset. "
                "They are NOT authentic past-paper questions and have not been verified by lecturers."
            ),
            "limitations": [
                "Questions are generated synthetically and have not undergone academic review.",
                "Marks and difficulties are unassessed to avoid fabricating academic assessment criteria.",
                "Topic classifications are provisional development labels, not verified syllabus mappings.",
                "This paper is for practice only and is not a prediction of examination questions.",
            ],
        }
