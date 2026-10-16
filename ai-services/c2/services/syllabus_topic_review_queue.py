
import copy
import hashlib
import json
import re
from pathlib import Path

from services.syllabus_topic_review_repository import (
    SyllabusTopicReviewRepository,
)


class SyllabusTopicReviewQueue:
    """
    Prepare paginated syllabus topic review queues.

    Candidate ranking determines review priority only.
    It never determines verification status.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, reports_dir=None, repository=None):
        if reports_dir is None:
            reports_dir = (
                Path(__file__).resolve().parents[1]
                / "outputs"
                / "syllabus_reviews"
            )

        self.reports_dir = Path(reports_dir)

        if repository is None:
            repository = SyllabusTopicReviewRepository()

        self.repository = repository

    @staticmethod
    def candidate_id(module_key, candidate_name):
        """
        Create a stable ID for a module/candidate-name pair.

        IDs do not depend on rank, so ranking changes will
        not invalidate existing review decisions.
        """
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Invalid module key")

        if not isinstance(candidate_name, str) or not candidate_name.strip():
            raise ValueError("Invalid candidate name")

        normalized = re.sub(
            r"\s+",
            " ",
            candidate_name.strip().casefold(),
        )

        value = f"{module_key.strip()}:{normalized}"

        digest = hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()[:20]

        return f"{module_key.strip()}:{digest}"

    def _load_report(self, module_key):
        if not isinstance(module_key, str) or not re.fullmatch(
            r"[a-z][a-z0-9_]*",
            module_key,
        ):
            raise ValueError("Invalid module key")

        path = self.reports_dir / f"{module_key}_review_report.json"

        if not path.exists():
            raise FileNotFoundError(
                f"Review report not found for {module_key}"
            )

        with path.open("r", encoding="utf-8") as file:
            report = json.load(file)

        if (
            not isinstance(report, dict)
            or report.get("schema_version") != self.SCHEMA_VERSION
            or report.get("module_key") != module_key
            or not isinstance(report.get("review_candidates"), list)
            or not isinstance(report.get("excluded_candidates"), list)
        ):
            raise ValueError("Invalid review report structure")

        return report

    def get_queue(
        self,
        module_key,
        page=1,
        page_size=25,
        include_reviewed=False,
    ):
        """
        Return a paginated review queue for one module.

        Reviewed candidates are omitted unless requested.
        """
        if (
            not isinstance(page, int)
            or isinstance(page, bool)
            or page < 1
        ):
            raise ValueError("page must be a positive integer")

        if (
            not isinstance(page_size, int)
            or isinstance(page_size, bool)
            or not 1 <= page_size <= 100
        ):
            raise ValueError("page_size must be between 1 and 100")

        report = self._load_report(module_key)

        saved_reviews = {
            review["candidate_id"]: review
            for review in self.repository.list_reviews(module_key)
        }

        queue = []

        for candidate in report["review_candidates"]:
            if not isinstance(candidate, dict):
                raise ValueError("Invalid candidate record")

            if candidate.get("module_key") != module_key:
                raise ValueError("Candidate module mismatch")

            name = candidate.get("candidate_name")

            candidate_id = self.candidate_id(module_key, name)

            saved_review = saved_reviews.get(candidate_id)

            if saved_review is not None:
                if (
                    saved_review["candidate_name"] != name
                    or saved_review["sources"] != candidate.get("sources")
                ):
                    raise ValueError(
                        "Saved review does not match report evidence"
                    )

            if (
                saved_review is not None
                and saved_review["review_decision"] != "pending"
                and not include_reviewed
            ):
                continue

            item = copy.deepcopy(candidate)
            item["candidate_id"] = candidate_id

            if saved_review is not None:
                item["review_decision"] = saved_review[
                    "review_decision"
                ]
                item["verification_status"] = saved_review[
                    "verification_status"
                ]
                item["review_notes"] = saved_review[
                    "review_notes"
                ]
                item["reviewer_id"] = saved_review[
                    "reviewer_id"
                ]
                item["reviewed_at"] = saved_review[
                    "reviewed_at"
                ]
            else:
                item["review_decision"] = "pending"
                item["verification_status"] = "unverified"
                item["review_notes"] = ""
                item["reviewer_id"] = None
                item["reviewed_at"] = None

            queue.append(item)

        queue.sort(
            key=lambda item: (
                -item["ranking_score"],
                item["rank"],
                item["candidate_id"],
            )
        )

        total = len(queue)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "schema_version": self.SCHEMA_VERSION,
            "module_key": module_key,
            "page": page,
            "page_size": page_size,
            "total_candidates": total,
            "total_pages": (
                (total + page_size - 1) // page_size
            ),
            "candidates": queue[start:end],
        }

    def get_excluded_candidates(self, module_key):
        """
        Return administrative exclusions for separate inspection.

        Excluded candidates are not automatically rejected.
        """
        report = self._load_report(module_key)

        excluded = []

        for candidate in report["excluded_candidates"]:
            item = copy.deepcopy(candidate)

            item["candidate_id"] = self.candidate_id(
                module_key,
                item["candidate_name"],
            )

            item["review_decision"] = "pending"
            item["verification_status"] = "unverified"

            excluded.append(item)

        return {
            "schema_version": self.SCHEMA_VERSION,
            "module_key": module_key,
            "excluded_candidate_count": len(excluded),
            "candidates": excluded,
        }
