"""M19.5 - Automated Test Suite for Batch Authentic Historical Past-Paper Ingestion.

Covers:
- Recursive PDF discovery
- Multi-module ingestion
- Multiple academic years
- Duplicate prevention
- Stable source IDs
- Module code mapping
- Question and subquestion extraction
- Marks ambiguity
- Safe repository updates
- Authentic/synthetic separation
- Module-specific question retrieval
- Regression compatibility
"""

import json
from pathlib import Path
import pytest

from services.batch_authentic_ingestion import (
    BatchAuthenticIngestion,
    CODE_TO_MODULE_KEY,
    compute_file_sha256,
)
from services.metadata_parser import extract_metadata
from services.question_detector import detect_questions
from services.question_repository import make_paper_id, build_question_repository
from services.student_question_bank import StudentQuestionBank
from services.personalized_mock_exam import PersonalizedMockExam

BASE_DIR = Path(__file__).resolve().parents[1]
AUTHENTIC_DIR = BASE_DIR / "datasets" / "authentic"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"


@pytest.fixture
def ingestion_service():
    return BatchAuthenticIngestion()


def test_recursive_pdf_discovery(ingestion_service):
    """Test that all 28 authentic past-paper PDFs are discovered recursively."""
    pdfs = ingestion_service.discover_pdfs()
    assert len(pdfs) == 28, f"Expected 28 authentic PDFs, discovered {len(pdfs)}"
    assert any(p.name == "sample.pdf" for p in pdfs)
    assert any("database_systems" in str(p) for p in pdfs)
    assert any("distributed_systems" in str(p) for p in pdfs)
    assert any("software_architecture" in str(p) for p in pdfs)
    assert any("application_frameworks" in str(p) for p in pdfs)


def test_pdf_classification_text_vs_scanned(ingestion_service):
    """Test identification of text-based papers (21) vs scanned bitmap papers (7)."""
    audit = ingestion_service.audit()
    assert audit["total_pdfs"] == 28
    assert audit["text_based_count"] == 21
    assert audit["scanned_count"] == 7
    assert len(audit["quarantined"]) == 7

    for q in audit["quarantined"]:
        assert q["quarantine_reason"] == "scanned_bitmap_no_text_layer"
        assert q["character_count"] < 50
        assert "action_required" in q


def test_duplicate_file_prevention(ingestion_service):
    """Test that all 28 PDF files have distinct SHA-256 hashes."""
    pdfs = ingestion_service.discover_pdfs()
    hashes = [compute_file_sha256(p) for p in pdfs]
    assert len(hashes) == len(set(hashes)), "Duplicate PDF files detected in authentic directory"


def test_stable_paper_ids():
    """Verify that paper IDs are stable, deterministic, and conform to CODE-YEAR-HASH."""
    mock_paper = {
        "metadata": {"module_code": "IT3020", "calendar_year": 2023},
        "source": {"filename": "sample.pdf"},
    }
    paper_id = make_paper_id(mock_paper)
    assert paper_id == "IT3020-2023-a34dce2c9501"

    # Deterministic on same input
    assert make_paper_id(mock_paper) == paper_id


def test_module_code_mapping():
    """Test comprehensive module code resolution including aliases."""
    expected_mappings = {
        "IT3020": "database_systems",
        "SE3060": "database_systems",
        "SE3010": "software_engineering_process_quality_management",
        "SE3020": "distributed_systems",
        "SE3030": "software_architecture",
        "SE3040": "application_frameworks",
        "SE3050": "user_experience_engineering",
        "SE3070": "case_studies_software_engineering",
        "SE3080": "software_project_management",
    }
    for code, expected_key in expected_mappings.items():
        assert CODE_TO_MODULE_KEY.get(code) == expected_key, f"Incorrect mapping for {code}"


def test_authentic_synthetic_separation():
    """Verify strict separation: all questions in questions.json must be authentic."""
    questions_path = PROCESSED_DIR / "questions.json"
    assert questions_path.exists(), "Processed questions.json not found"

    with questions_path.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    assert len(questions) >= 400
    for q in questions:
        assert q.get("source_type") == "authentic", (
            f"Question {q.get('question_id')} has non-authentic source_type: {q.get('source_type')}"
        )
        assert not q.get("question_id", "").startswith("M16-"), (
            f"Synthetic question contaminated authentic repository: {q.get('question_id')}"
        )


def test_multi_module_question_counts():
    """Test that all eight Year 3 SE modules are represented in the authentic repository."""
    questions_path = PROCESSED_DIR / "questions.json"
    with questions_path.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    module_counts = {}
    for q in questions:
        m_code = q.get("module_code")
        m_key = CODE_TO_MODULE_KEY.get(m_code, "unknown")
        module_counts[m_key] = module_counts.get(m_key, 0) + 1

    expected_modules = [
        "application_frameworks",
        "case_studies_software_engineering",
        "database_systems",
        "distributed_systems",
        "software_architecture",
        "software_engineering_process_quality_management",
        "software_project_management",
        "user_experience_engineering",
    ]
    for m in expected_modules:
        assert m in module_counts, f"Module {m} has no authentic questions"
        assert module_counts[m] > 0, f"Module {m} has 0 questions"


def test_multiple_academic_years_represented():
    """Verify that multiple academic calendar years are represented in authentic repository."""
    questions_path = PROCESSED_DIR / "questions.json"
    with questions_path.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    years = {q.get("calendar_year") for q in questions if q.get("calendar_year")}
    assert len(years) >= 3, f"Expected at least 3 distinct years, found {years}"
    assert 2018 in years
    assert 2019 in years
    assert 2022 in years
    assert 2023 in years


def test_marks_ambiguity_flagging():
    """Verify that marks are conservatively classified as extracted, ambiguous, or needs_review."""
    questions_path = PROCESSED_DIR / "questions.json"
    with questions_path.open("r", encoding="utf-8") as f:
        questions = json.load(f)

    statuses = {q.get("marks_status") for q in questions}
    assert "extracted" in statuses
    # Ambiguous or needs_review must be flagged
    assert any(q.get("marks_status") in ("ambiguous", "needs_review", "missing") for q in questions)

    # If status is extracted, marks must be positive number
    for q in questions:
        if q.get("marks_status") == "extracted":
            assert isinstance(q.get("marks"), (int, float))
            assert q.get("marks") > 0


def test_student_question_bank_all_modules():
    """Test that StudentQuestionBank retrieves authentic questions for all 8 modules."""
    sqb = StudentQuestionBank()
    for m_key in CODE_TO_MODULE_KEY.values():
        res = sqb.list_questions(module_key=m_key, page=1, page_size=5)
        assert res["total"] > 0, f"StudentQuestionBank returned 0 questions for {m_key}"
        assert len(res["questions"]) <= 5
        for q in res["questions"]:
            assert q["module_key"] == m_key
            assert q["source_type"] == "authentic"
            assert q["verification_status"] == "unverified" or q["verification_status"] == "verified"


def test_authentic_mock_generation_multi_module():
    """Test that authentic mock generator generates valid mock papers for eligible modules."""
    pme = PersonalizedMockExam()
    # Test on multiple modules that have at least 20 marks of extracted questions
    test_modules = [
        "database_systems",
        "distributed_systems",
        "software_architecture",
        "application_frameworks",
        "case_studies_software_engineering",
    ]
    for m in test_modules:
        paper = pme.generate(module_key=m, target_marks=20, max_questions=5)
        assert len(paper["questions"]) > 0, f"No mock questions generated for {m}"
        assert paper["total_marks"] <= 20
        assert paper["module_key"] == m
        for q in paper["questions"]:
            assert q["source_type"] == "authentic"
            assert q["marks"] > 0
            assert isinstance(q["question_id"], str)


def test_quarantined_papers_registry():
    """Verify quarantined_papers.json format and contents."""
    quarantined_path = PROCESSED_DIR / "quarantined_papers.json"
    assert quarantined_path.exists()

    with quarantined_path.open("r", encoding="utf-8") as f:
        quarantined = json.load(f)

    assert len(quarantined) == 7
    for q in quarantined:
        assert "filename" in q
        assert "quarantine_reason" in q
        assert "action_required" in q
        assert q["quarantine_reason"] == "scanned_bitmap_no_text_layer"


def test_idempotent_ingestion(ingestion_service):
    """Verify that re-running ingestion does not duplicate questions or papers."""
    report = ingestion_service.ingest_all(dry_run=True)
    summary = report["summary"]
    # In dry run against the populated repository, newly ingested records should be 0
    assert summary["new_question_records_ingested"] == 0
    assert summary["total_question_records"] == 443
