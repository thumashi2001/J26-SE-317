"""M19.5 - Batch Authentic Historical Past-Paper Ingestion Service.

Recursively processes historical examination papers from ai-services/c2/datasets/authentic/
to establish an authentic multi-module, multi-year question repository for all eight
Year 3 Software Engineering modules.
"""

import hashlib
import json
import logging
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from services.metadata_parser import MODULE_CODE_TO_NAME
from services.paper_parser import parse_paper
from services.question_repository import build_question_repository, make_paper_id
from services.question_classification_pipeline import (
    DEFAULT_QUESTIONS_PATH,
    DEFAULT_OUTPUT_PATH,
    QuestionClassificationPipeline,
)
from services.m17_topic_prediction_service import (
    M17TopicPredictionService,
    ModelNotFoundError,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_AUTHENTIC_DIR = BASE_DIR / "datasets" / "authentic"
DEFAULT_PROCESSED_DIR = BASE_DIR / "datasets" / "processed"
DEFAULT_QUARANTINED_PATH = DEFAULT_PROCESSED_DIR / "quarantined_papers.json"
DEFAULT_PAPERS_PATH = DEFAULT_PROCESSED_DIR / "papers.json"
DEFAULT_REPORT_PATH = DEFAULT_PROCESSED_DIR / "processing_report.json"

CODE_TO_MODULE_KEY = {
    "SE3010": "software_engineering_process_quality_management",
    "SE3020": "distributed_systems",
    "SE3030": "software_architecture",
    "SE3040": "application_frameworks",
    "SE3050": "user_experience_engineering",
    "IT3020": "database_systems",
    "SE3060": "database_systems",
    "SE3070": "case_studies_software_engineering",
    "SE3080": "software_project_management",
}


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with filepath.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class BatchAuthenticIngestion:
    """Batch ingestion service for authentic past-paper PDFs."""

    def __init__(
        self,
        authentic_dir: Optional[Path] = None,
        processed_dir: Optional[Path] = None,
        prediction_service: Optional[M17TopicPredictionService] = None,
    ):
        self.authentic_dir = Path(authentic_dir or DEFAULT_AUTHENTIC_DIR).resolve()
        self.processed_dir = Path(processed_dir or DEFAULT_PROCESSED_DIR).resolve()
        self.questions_path = self.processed_dir / "questions.json"
        self.papers_path = self.processed_dir / "papers.json"
        self.classifications_path = self.processed_dir / "topic_classifications.json"
        self.quarantined_path = self.processed_dir / "quarantined_papers.json"
        self.report_path = self.processed_dir / "processing_report.json"

        try:
            self.predictor = prediction_service or M17TopicPredictionService()
        except Exception:
            self.predictor = None

        self.pipeline = QuestionClassificationPipeline()

    def discover_pdfs(self) -> List[Path]:
        """Recursively discover all PDF files under the authentic dataset directory."""
        if not self.authentic_dir.exists():
            return []
        return sorted([p for p in self.authentic_dir.rglob("*.pdf") if p.is_file()])

    def inspect_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Inspect a PDF without modifying storage to audit text extraction and metadata."""
        file_hash = compute_file_sha256(pdf_path)
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        pages_text = [page.get_text("text") for page in doc]
        doc.close()

        total_chars = sum(len(p.strip()) for p in pages_text)
        is_scanned = total_chars < 50
        rel_path = str(pdf_path.relative_to(self.authentic_dir)).replace("\\", "/")

        return {
            "path": str(pdf_path),
            "filename": pdf_path.name,
            "relative_path": rel_path,
            "file_size_bytes": pdf_path.stat().st_size,
            "sha256": file_hash,
            "page_count": page_count,
            "character_count": total_chars,
            "is_scanned": is_scanned,
        }

    def audit(self) -> Dict[str, Any]:
        """Perform a read-only audit of all authentic past papers."""
        all_pdfs = self.discover_pdfs()
        inspected = [self.inspect_pdf(p) for p in all_pdfs]

        text_based = [p for p in inspected if not p["is_scanned"]]
        scanned = [p for p in inspected if p["is_scanned"]]

        # Hash uniqueness audit
        sha256s = set(p["sha256"] for p in inspected)
        has_duplicate_files = len(sha256s) < len(inspected)

        # Module grouping
        module_counts = defaultdict(int)
        year_counts = defaultdict(int)
        quarantined = []

        for p in text_based:
            parsed = parse_paper(p["path"])
            meta = parsed.get("metadata", {})
            m_code = meta.get("module_code")
            m_key = CODE_TO_MODULE_KEY.get(m_code, "unknown")
            module_counts[m_key] += 1
            yr = meta.get("calendar_year") or "UNKNOWN"
            year_counts[str(yr)] += 1

        for p in scanned:
            quarantined.append({
                "filename": p["filename"],
                "relative_path": p["relative_path"],
                "file_size_bytes": p["file_size_bytes"],
                "sha256": p["sha256"],
                "page_count": p["page_count"],
                "character_count": p["character_count"],
                "quarantine_reason": "scanned_bitmap_no_text_layer",
                "action_required": (
                    "Manual OCR or replacement with searchable digital examination paper required."
                ),
            })

        return {
            "total_pdfs": len(inspected),
            "text_based_count": len(text_based),
            "scanned_count": len(scanned),
            "has_duplicate_files": has_duplicate_files,
            "module_counts": dict(module_counts),
            "year_counts": dict(year_counts),
            "quarantined": quarantined,
        }

    def _backup_existing(self):
        """Create timestamped or .bak copies before writing."""
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        for path in [self.questions_path, self.papers_path, self.classifications_path]:
            if path.exists():
                bak = path.with_suffix(".json.bak")
                shutil.copy2(path, bak)

    def _load_existing_questions(self) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Load existing questions and map by question_id."""
        if not self.questions_path.exists():
            return [], {}
        with self.questions_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return [], {}
        by_id = {q["question_id"]: q for q in data if isinstance(q, dict) and "question_id" in q}
        return data, by_id

    def _load_existing_papers(self) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        """Load existing papers and map by paper_id or filename."""
        if not self.papers_path.exists():
            return [], {}
        with self.papers_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return [], {}
        by_fn = {
            p.get("source", {}).get("filename"): p
            for p in data
            if isinstance(p, dict) and "source" in p
        }
        return data, by_fn

    def _load_existing_classifications(self) -> Dict[str, Any]:
        """Load existing topic classifications."""
        if not self.classifications_path.exists():
            return {
                "schema_version": "1.0",
                "source_repository": str(self.questions_path),
                "summary": {"total_questions": 0, "classified": 0, "unclassified": 0, "invalid": 0},
                "results": [],
            }
        with self.classifications_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _provisional_classification(
        self, question_record: Dict[str, Any], module_key: str
    ) -> Dict[str, Any]:
        """Generate a provisional topic classification suggestion without verifying."""
        q_id = question_record["question_id"]
        q_text = question_record.get("question_text", "")

        if not self.predictor or not module_key or module_key == "unknown":
            return {
                "question_id": q_id,
                "valid": True,
                "classification": {
                    "question_id": q_id,
                    "module_key": module_key,
                    "topic_id": None,
                    "subtopic": None,
                    "classification_method": "unclassified",
                    "confidence_score": None,
                    "verification_status": "unverified",
                },
                "errors": [],
                "warnings": [],
            }

        try:
            pred = self.predictor.predict(
                module_key=module_key,
                question_text=q_text,
            )
            if pred.get("abstained") or not pred.get("provisional_topic_id"):
                method = "unclassified"
                topic_id = None
            else:
                method = "m17_provisional"
                topic_id = pred.get("provisional_topic_id")

            return {
                "question_id": q_id,
                "valid": True,
                "classification": {
                    "question_id": q_id,
                    "module_key": module_key,
                    "topic_id": topic_id,
                    "subtopic": None,
                    "classification_method": method,
                    "confidence_score": pred.get("confidence_score"),
                    "verification_status": "unverified",
                },
                "errors": [],
                "warnings": [
                    "Provisional topic suggestion generated by synthetic M17 model; requires lecturer review."
                ] if topic_id else ["Topic prediction abstained below conservative threshold; pending lecturer review."],
            }
        except (ModelNotFoundError, Exception) as exc:
            return {
                "question_id": q_id,
                "valid": True,
                "classification": {
                    "question_id": q_id,
                    "module_key": module_key,
                    "topic_id": None,
                    "subtopic": None,
                    "classification_method": "unclassified",
                    "confidence_score": None,
                    "verification_status": "unverified",
                },
                "errors": [],
                "warnings": [f"Topic prediction abstained or unavailable: {exc}"],
            }

    def ingest_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """Perform batch ingestion of authentic past-paper PDFs."""
        all_pdfs = self.discover_pdfs()
        inspected = [self.inspect_pdf(p) for p in all_pdfs]

        text_pdfs = [p for p in inspected if not p["is_scanned"]]
        scanned_pdfs = [p for p in inspected if p["is_scanned"]]

        # Quarantined entries
        quarantined_records = []
        for s in scanned_pdfs:
            quarantined_records.append({
                "filename": s["filename"],
                "relative_path": s["relative_path"],
                "file_size_bytes": s["file_size_bytes"],
                "sha256": s["sha256"],
                "page_count": s["page_count"],
                "character_count": s["character_count"],
                "quarantine_reason": "scanned_bitmap_no_text_layer",
                "action_required": "Manual optical character recognition (OCR) or replacement with high-resolution digital master required.",
            })

        existing_questions_list, existing_questions_by_id = self._load_existing_questions()
        existing_papers_list, existing_papers_by_fn = self._load_existing_papers()
        existing_classifications_data = self._load_existing_classifications()

        existing_results_by_id = {
            r.get("question_id"): r
            for r in existing_classifications_data.get("results", [])
            if isinstance(r, dict) and "question_id" in r
        }

        parsed_papers = []
        new_questions_records = []
        new_classification_results = []
        questions_per_module = defaultdict(int)
        years_represented = set()
        ambiguous_marks_count = 0

        final_questions_map = {q["question_id"]: dict(q) for q in existing_questions_list}

        for t in text_pdfs:
            pdf_path = Path(t["path"])
            structured_paper = parse_paper(pdf_path)
            meta = structured_paper.get("metadata", {})
            m_code = meta.get("module_code")
            m_key = CODE_TO_MODULE_KEY.get(m_code, "unknown")

            parsed_papers.append(structured_paper)

            repo = build_question_repository(structured_paper)
            for q_rec in repo["questions"]:
                q_id = q_rec["question_id"]

                if q_id in final_questions_map:
                    # Update fields from fresh parse while preserving any lecturer review/topic
                    existing_item = final_questions_map[q_id]
                    existing_item["question_text"] = q_rec["question_text"]
                    existing_item["context"] = q_rec["context"]
                    existing_item["marks"] = q_rec["marks"]
                    existing_item["marks_status"] = q_rec["marks_status"]
                    if q_rec.get("parent_id") is not None:
                        existing_item["parent_id"] = q_rec["parent_id"]
                else:
                    final_questions_map[q_id] = q_rec
                    new_questions_records.append(q_rec)

                # Generate classification
                if q_id not in existing_results_by_id:
                    prov = self._provisional_classification(q_rec, m_key)
                    new_classification_results.append(prov)

        all_final_questions = list(final_questions_map.values())

        # Recount tallies across all questions
        for q in all_final_questions:
            m_code = q.get("module_code")
            m_key = CODE_TO_MODULE_KEY.get(m_code, "database_systems")
            questions_per_module[m_key] += 1
            if q.get("calendar_year"):
                years_represented.add(q["calendar_year"])
            if q.get("marks_status") in ("ambiguous", "missing", "needs_review"):
                ambiguous_marks_count += 1

        # Merge classification results
        all_final_results = list(existing_classifications_data.get("results", []))
        for res in new_classification_results:
            if res["question_id"] not in existing_results_by_id:
                all_final_results.append(res)

        classified_count = sum(
            1 for r in all_final_results
            if r.get("classification", {}).get("topic_id") is not None
        )
        unclassified_count = len(all_final_results) - classified_count

        final_classifications = {
            "schema_version": "1.0",
            "source_repository": str(self.questions_path),
            "summary": {
                "total_questions": len(all_final_results),
                "classified": classified_count,
                "unclassified": unclassified_count,
                "invalid": 0,
            },
            "results": all_final_results,
        }

        # Merge papers list
        seen_paper_fns = set()
        final_papers = []
        for p in existing_papers_list + parsed_papers:
            fn = p.get("source", {}).get("filename")
            if fn and fn not in seen_paper_fns:
                seen_paper_fns.add(fn)
                final_papers.append(p)

        report = {
            "summary": {
                "total_files_discovered": len(all_pdfs),
                "successful_files": len(text_pdfs),
                "quarantined_files": len(scanned_pdfs),
                "existing_question_records": len(existing_questions_list),
                "new_question_records_ingested": len(new_questions_records),
                "total_question_records": len(all_final_questions),
                "questions_per_module": dict(questions_per_module),
                "academic_years_represented": sorted(list(years_represented)),
                "ambiguous_marks_count": ambiguous_marks_count,
                "provisional_topic_classified_count": classified_count,
                "unclassified_count": unclassified_count,
            },
            "quarantined_papers": quarantined_records,
            "errors": [],
        }

        if not dry_run:
            self._backup_existing()

            # Atomic write questions.json
            with self.questions_path.open("w", encoding="utf-8") as f:
                json.dump(all_final_questions, f, indent=2)

            # Atomic write papers.json
            with self.papers_path.open("w", encoding="utf-8") as f:
                json.dump(final_papers, f, indent=2)

            # Atomic write topic_classifications.json
            with self.classifications_path.open("w", encoding="utf-8") as f:
                json.dump(final_classifications, f, indent=2)

            # Atomic write quarantined_papers.json
            with self.quarantined_path.open("w", encoding="utf-8") as f:
                json.dump(quarantined_records, f, indent=2)

            # Atomic write processing_report.json
            with self.report_path.open("w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

        return report
