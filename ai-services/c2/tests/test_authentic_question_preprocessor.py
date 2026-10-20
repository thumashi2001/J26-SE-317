"""Tests for AuthenticQuestionPreprocessor (M20.5 Phase 2)."""

import pytest
from services.authentic_question_preprocessor import (
    AuthenticQuestionPreprocessor,
    PROTECTED_TECHNICAL_ACRONYMS,
)


@pytest.fixture
def preprocessor():
    return AuthenticQuestionPreprocessor()


def test_empty_question_text(preprocessor):
    res = preprocessor.preprocess("")
    assert res["is_empty"] is True
    assert res["normalized_text"] == ""
    assert res["cleaned_display_text"] == ""
    assert res["extracted_marks"] is None


def test_whitespace_only_question_text(preprocessor):
    res = preprocessor.preprocess("   \n\t  ")
    assert res["is_empty"] is True
    assert res["normalized_text"] == ""


def test_strips_question_numbering(preprocessor):
    raw = "Q1(a) Explain the fundamental principles of RESTful architecture."
    res = preprocessor.preprocess(raw)
    assert res["original_text"] == raw
    assert not res["cleaned_display_text"].startswith("Q1(a)")
    assert "fundamental principles of restful architecture" in res["normalized_text"]
    assert res["detected_features"]["has_question_number"] is True


def test_strips_nested_part_id(preprocessor):
    raw = "(b)(i) Describe two benefits of microservices decomposition."
    res = preprocessor.preprocess(raw)
    assert not res["cleaned_display_text"].startswith("(b)(i)")
    assert "benefits of microservices decomposition" in res["normalized_text"]


def test_strips_marks_annotation(preprocessor):
    raw = "Critically analyse Oracle Object relational data model and XML data model. (5 Marks) 25 marks"
    res = preprocessor.preprocess(raw)
    assert "(5 Marks)" not in res["cleaned_display_text"]
    assert "5 marks" not in res["normalized_text"]
    assert res["detected_features"]["has_marks_annotation"] is True
    assert res["extracted_marks"] is not None


def test_fixes_ocr_scan_artifacts(preprocessor):
    raw = "Provide four reasons to justify why most commercial databases support 8+ tree indexes. (5 marks) Page 3 of 6 oog8\\"
    res = preprocessor.preprocess(raw)
    assert "b+ tree" in res["normalized_text"]
    assert "Page 3 of 6" not in res["cleaned_display_text"]
    assert "oog8\\" not in res["cleaned_display_text"]
    assert res["detected_features"]["has_ocr_noise"] is True


def test_fixes_pom_xml_ocr(preprocessor):
    raw = "Discover the role of the porn.xml file in Maven and how does it help to manage dependencies. (3 Marks)"
    res = preprocessor.preprocess(raw)
    assert "pom.xml" in res["cleaned_display_text"]
    assert "pom.xml" in res["normalized_text"]


def test_preserves_sql_statements(preprocessor):
    raw = """Write a SQL statement to find active employees:
SELECT emp_id, first_name, department_id
FROM employees
WHERE status = 'ACTIVE'
GROUP BY department_id
HAVING COUNT(*) > 5;"""
    res = preprocessor.preprocess(raw)
    assert res["detected_features"]["has_sql"] is True
    assert "select" in res["normalized_text"]
    assert "from employees" in res["normalized_text"]
    assert "group by" in res["normalized_text"]
    assert "having count" in res["normalized_text"]


def test_preserves_code_fragments(preprocessor):
    raw = """Explain the role of dependency injection in this Spring component:
@RestController
public class OrderService {
    @Autowired
    private OrderRepository orderRepo;
}"""
    res = preprocessor.preprocess(raw)
    assert res["detected_features"]["has_code"] is True
    assert "@restcontroller" in res["normalized_text"]
    assert "orderrepository" in res["normalized_text"]


def test_preserves_technical_acronyms(preprocessor):
    raw = "How do ACID properties and Two-Phase Locking (2PL) prevent dirty reads in a RDBMS using WAL?"
    res = preprocessor.preprocess(raw)
    terms = res["detected_features"]["technical_terms"]
    assert "ACID" in terms
    assert "2PL" in terms
    assert "WAL" in terms
    assert "RDBMS" in terms
    # Ensure they remain intact in normalized text
    assert "acid" in res["normalized_text"]
    assert "2pl" in res["normalized_text"]
    assert "wal" in res["normalized_text"]


def test_preserves_original_text_unmodified(preprocessor):
    raw = "  Q2(c)   [10 marks]  Explain B+ tree structure.   "
    res = preprocessor.preprocess(raw)
    assert res["original_text"] == raw
