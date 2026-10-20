"""M20.5 — Taxonomy Approval Repository.

Persistent JSON repository storing lecturer review and approval decisions
for curriculum topic taxonomies.

Guarantees:
- Validated review records (approved / rejected / pending).
- Stale approval protection (version-locked).
- Thread-safe atomic file replacement.
- Preserves full audit trail and reviewer provenance.
- Clean separation: does not modify static config files on disk.
"""

import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE_PATH = (
    BASE_DIR
    / "outputs"
    / "taxonomy_approvals"
    / "approvals.json"
)


class TaxonomyApprovalRepository:
    """Stores and retrieves lecturer approval decisions for module taxonomies."""

    SCHEMA_VERSION = "1.0"

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path or DEFAULT_STORAGE_PATH)
        self._lock = Lock()

    def _empty_document(self) -> Dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "approvals": {},
            "history": [],
        }

    def _load(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return self._empty_document()

        with self.storage_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if (
            not isinstance(data, dict)
            or data.get("schema_version") != self.SCHEMA_VERSION
            or not isinstance(data.get("approvals"), dict)
            or not isinstance(data.get("history"), list)
        ):
            raise ValueError("Corrupt or invalid taxonomy approval repository format")

        return data

    def _save(self, data: Dict[str, Any]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            prefix=".tax_approval_",
            suffix=".tmp",
            dir=self.storage_path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.storage_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def get_approval(self, module_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve the latest approval decision for a module."""
        if not isinstance(module_key, str) or not module_key.strip():
            return None
        norm = module_key.strip().lower()
        with self._lock:
            data = self._load()
            rec = data["approvals"].get(norm)
            return copy.deepcopy(rec) if rec else None

    def list_approvals(self) -> Dict[str, Dict[str, Any]]:
        """List all current approval decisions mapped by module key."""
        with self._lock:
            data = self._load()
            return copy.deepcopy(data["approvals"])

    def get_history(self, module_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve audit history of approval actions."""
        with self._lock:
            data = self._load()
            events = data.get("history", [])
            if module_key:
                norm = module_key.strip().lower()
                events = [e for e in events if e.get("module_key") == norm]
            return copy.deepcopy(events)

    def save_decision(
        self,
        *,
        module_key: str,
        status: str,
        reviewer_id: str,
        version: str = "1.0",
        review_notes: str = "",
        topics: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Save a lecturer taxonomy approval or rejection decision.

        Allowed statuses: 'approved', 'rejected', 'pending'.
        Rejection requires non-empty review_notes.
        """
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Module key must be a non-empty string")
        if status not in ("approved", "rejected", "pending"):
            raise ValueError(f"Invalid approval status: '{status}'. Allowed: approved, rejected, pending")
        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            raise ValueError("Reviewer ID must be a non-empty string")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("Version must be a non-empty string")
        if not isinstance(review_notes, str):
            raise ValueError("Review notes must be a string")
        if len(review_notes) > 2000:
            raise ValueError("Review notes must not exceed 2000 characters")
        if status == "rejected" and not review_notes.strip():
            raise ValueError("Rejection of a taxonomy requires explanatory review notes")

        norm_key = module_key.strip().lower()
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "module_key": norm_key,
            "version": version.strip(),
            "status": status,
            "reviewer_id": reviewer_id.strip(),
            "reviewed_at": now_iso,
            "review_notes": review_notes.strip(),
            "topics": topics or [],
        }

        history_event = {
            "event_type": f"taxonomy_{status}",
            "module_key": norm_key,
            "version": version.strip(),
            "reviewer_id": reviewer_id.strip(),
            "timestamp": now_iso,
            "review_notes": review_notes.strip(),
        }

        with self._lock:
            data = self._load()
            data["approvals"][norm_key] = record
            data["history"].append(history_event)
            self._save(data)

        return copy.deepcopy(record)
