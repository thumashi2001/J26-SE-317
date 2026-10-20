"""M21 — Isolated Lecturer-Approved Generated Question Repository.

Strict Research Integrity Constraints:
- Saves lecturer-approved generated questions in a completely separate storage location.
- Explicitly marked as `is_authentic: False`.
- Never relabeled as authentic past papers.
- Strictly isolated from M20 historical exam prediction evidence pipelines.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE_PATH = (
    PROJECT_ROOT / "datasets" / "generated_questions" / "lecturer_approved_questions.json"
)


class GeneratedQuestionRepository:
    """Manages persistent storage for lecturer-approved generated questions."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path or DEFAULT_STORAGE_PATH)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_empty()

    def _save_empty(self) -> None:
        payload = {
            "schema_version": "1.0",
            "description": "Lecturer-reviewed and approved generated examination questions.",
            "provenance": "M21 Bloom's Taxonomy-Controlled Generation System",
            "is_authentic_evidence": False,
            "questions": [],
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _read_data(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            self._save_empty()
        with open(self.storage_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_data(self, data: Dict[str, Any]) -> None:
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list_approved_questions(self, module_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all approved generated questions, optionally filtered by module."""
        data = self._read_data()
        questions = data.get("questions", [])
        if module_key:
            return [q for q in questions if q.get("module_key") == module_key]
        return questions

    def get_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get an approved question by its unique identifier."""
        data = self._read_data()
        for q in data.get("questions", []):
            if q.get("question_id") == question_id:
                return q
        return None

    def save_approved_question(
        self,
        question_data: Dict[str, Any],
        reviewer_id: str,
        review_notes: str = "",
    ) -> Dict[str, Any]:
        """Save a lecturer-approved question to the repository with full provenance."""
        data = self._read_data()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Enforce strict research integrity flags
        record = {
            **question_data,
            "approval_status": "approved",
            "reviewer_id": reviewer_id,
            "review_notes": review_notes.strip() if review_notes else "Approved by lecturer.",
            "approved_at": now_iso,
            "is_authentic": False,  # MUST NEVER be True
            "provenance": "m21_bloom_controlled_generation",
        }

        # Update if exists, or append
        existing_idx = next(
            (i for i, q in enumerate(data.get("questions", [])) if q.get("question_id") == record["question_id"]),
            None,
        )

        if existing_idx is not None:
            data["questions"][existing_idx] = record
        else:
            data["questions"].insert(0, record)

        data["total_approved"] = len(data["questions"])
        data["last_updated"] = now_iso
        self._write_data(data)
        return record

    def save_rejected_question(
        self,
        question_data: Dict[str, Any],
        reviewer_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Audit rejected candidate generation attempts."""
        rejected_path = self.storage_path.parent / "rejected_generation_audit.json"
        now_iso = datetime.now(timezone.utc).isoformat()

        existing = []
        if rejected_path.exists():
            try:
                with open(rejected_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        audit_entry = {
            "question_id": question_data.get("question_id"),
            "module_key": question_data.get("module_key"),
            "topic_id": question_data.get("topic_id"),
            "bloom_level": question_data.get("bloom_level"),
            "reviewer_id": reviewer_id,
            "rejection_reason": reason,
            "rejected_at": now_iso,
            "question_text": question_data.get("question_text"),
        }

        existing.insert(0, audit_entry)
        with open(rejected_path, "w", encoding="utf-8") as f:
            json.dump(existing[:100], f, indent=2)

        return audit_entry
