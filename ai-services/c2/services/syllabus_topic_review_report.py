
import copy
import json
from pathlib import Path


class SyllabusTopicReviewReport:
    """
    Prepare ranked syllabus topic candidates for manual review.

    This service does not automatically verify or approve topics.
    """

    SCHEMA_VERSION = "1.0"

    def build_module_report(self, module_data):
        if not isinstance(module_data, dict):
            raise ValueError("Module data must be a dictionary")

        module_key = module_data.get("module_key")
        candidates = module_data.get("candidates")
        excluded = module_data.get("excluded_candidates", [])

        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Missing module key")

        if not isinstance(candidates, list):
            raise ValueError("Missing candidate list")

        if not isinstance(excluded, list):
            raise ValueError("Invalid excluded candidate list")

        review_candidates = []

        for candidate in candidates:
            if candidate.get("module_key") != module_key:
                raise ValueError("Candidate module mismatch")

            if candidate.get("verification_status") != "unverified":
                raise ValueError("Candidate must be unverified")

            review_candidates.append({
                "module_key": module_key,
                "candidate_name": candidate["candidate_name"],
                "rank": candidate["rank"],
                "ranking_score": candidate["ranking_score"],
                "occurrence_count": candidate["occurrence_count"],
                "document_count": candidate["document_count"],
                "sources": copy.deepcopy(candidate["sources"]),
                "verification_status": "unverified",
                "review_decision": "pending",
                "review_notes": "",
            })

        return {
            "schema_version": self.SCHEMA_VERSION,
            "module_key": module_key,
            "summary": {
                "review_candidate_count": len(review_candidates),
                "excluded_candidate_count": len(excluded),
                "pending_review_count": len(review_candidates),
            },
            "review_candidates": review_candidates,
            "excluded_candidates": copy.deepcopy(excluded),
        }

    def build_all_reports(self, ranked_data):
        if not isinstance(ranked_data, dict):
            raise ValueError("Ranked data must be a dictionary")

        modules = ranked_data.get("modules")

        if not isinstance(modules, dict):
            raise ValueError("Missing modules dictionary")

        reports = {}

        for module_key, module_data in modules.items():
            report = self.build_module_report(module_data)

            if report["module_key"] != module_key:
                raise ValueError("Module dictionary key mismatch")

            reports[module_key] = report

        return {
            "schema_version": self.SCHEMA_VERSION,
            "summary": {
                "module_count": len(reports),
                "total_review_candidates": sum(
                    len(report["review_candidates"])
                    for report in reports.values()
                ),
                "total_excluded_candidates": sum(
                    len(report["excluded_candidates"])
                    for report in reports.values()
                ),
            },
            "modules": reports,
        }

    def export_json(self, report_data, output_path):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                report_data,
                file,
                indent=2,
                ensure_ascii=False,
            )

        return path
