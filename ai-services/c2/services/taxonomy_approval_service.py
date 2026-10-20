"""M20.5 — Taxonomy Approval Service.

Manages academic lecturer review, approval, and verification workflows
for module curriculum topic taxonomies.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.taxonomy_approval_repository import TaxonomyApprovalRepository

BASE_DIR = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = BASE_DIR / "config" / "curriculum_taxonomies.json"
MODULES_PATH = BASE_DIR / "config" / "modules.json"

CANONICAL_MODULE_ALIASES = {
    "case_studies_in_software_engineering": "case_studies_software_engineering",
    "software_engineering_process_and_quality_management": "software_engineering_process_quality_management",
}


class TaxonomyApprovalService:
    """Manages academic lecturer review and approval of curriculum taxonomies."""

    def __init__(
        self,
        repository: Optional[TaxonomyApprovalRepository] = None,
        curriculum_path: Optional[Path] = None,
        modules_path: Optional[Path] = None,
    ):
        self.repository = repository or TaxonomyApprovalRepository()
        self.curriculum_path = Path(curriculum_path or CURRICULUM_PATH)
        self.modules_path = Path(modules_path or MODULES_PATH)
        self._curriculum_cache: Optional[Dict[str, Any]] = None

    def _load_curriculum(self) -> Dict[str, Any]:
        if self._curriculum_cache is not None:
            return self._curriculum_cache

        if not self.curriculum_path.exists():
            raise FileNotFoundError(f"Curriculum taxonomy file not found at {self.curriculum_path}")

        with self.curriculum_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        modules_map = {}
        for mod in data.get("modules", []):
            key = mod.get("module_key")
            modules_map[key] = mod
            for alias in mod.get("aliases", []):
                modules_map[alias] = mod
        self._curriculum_cache = modules_map
        return modules_map

    def canonicalize_module_key(self, key_or_code: str) -> str:
        norm = key_or_code.strip().lower()
        norm = CANONICAL_MODULE_ALIASES.get(norm, norm)
        curriculum = self._load_curriculum()
        if norm in curriculum:
            return curriculum[norm]["module_key"]
        return norm

    def get_taxonomy(self, module_key: str) -> Dict[str, Any]:
        """Get the full taxonomy details and approval status for a module."""
        canonical_key = self.canonicalize_module_key(module_key)
        curriculum = self._load_curriculum()
        if canonical_key not in curriculum:
            raise ValueError(f"Unknown module key: '{module_key}'")

        mod_data = curriculum[canonical_key]
        approval = self.repository.get_approval(canonical_key)

        is_approved = bool(
            approval
            and approval.get("status") == "approved"
            and approval.get("version") == mod_data.get("version", "1.0")
        )

        return {
            "module_key": canonical_key,
            "module_name": mod_data.get("module_name", canonical_key),
            "module_code": mod_data.get("module_code", ""),
            "version": mod_data.get("version", "1.0"),
            "verification_status": "verified" if is_approved else "unverified",
            "is_approved": is_approved,
            "question_reviews_unlocked": is_approved,
            "approval_record": approval,
            "topics": mod_data.get("topics", []),
        }

    def list_taxonomies(self) -> List[Dict[str, Any]]:
        """List all 8 module taxonomies and their current approval status."""
        curriculum = self._load_curriculum()
        unique_keys = []
        seen = set()
        for k, v in curriculum.items():
            canon = v["module_key"]
            if canon not in seen:
                seen.add(canon)
                unique_keys.append(canon)

        return [self.get_taxonomy(k) for k in unique_keys]

    def is_taxonomy_approved(self, module_key: str) -> bool:
        """Check if a module taxonomy has been approved by a lecturer."""
        try:
            tax = self.get_taxonomy(module_key)
            return tax["is_approved"]
        except ValueError:
            return False

    def review_taxonomy(
        self,
        *,
        module_key: str,
        status: str,
        reviewer_id: str,
        review_notes: str = "",
        version: str = "1.0",
    ) -> Dict[str, Any]:
        """Record a lecturer approval or rejection decision for a module taxonomy."""
        canonical_key = self.canonicalize_module_key(module_key)
        curriculum = self._load_curriculum()
        if canonical_key not in curriculum:
            raise ValueError(f"Unknown module key: '{module_key}'")

        mod_data = curriculum[canonical_key]
        expected_version = mod_data.get("version", "1.0")

        if version != expected_version:
            raise ValueError(
                f"Taxonomy version mismatch for {canonical_key}. "
                f"Expected '{expected_version}', got '{version}'"
            )

        # Include canonical topics in the persistent approval record
        topics_payload = mod_data.get("topics", []) if status == "approved" else []

        saved = self.repository.save_decision(
            module_key=canonical_key,
            status=status,
            reviewer_id=reviewer_id,
            version=version,
            review_notes=review_notes,
            topics=topics_payload,
        )

        return self.get_taxonomy(canonical_key)
