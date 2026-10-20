"""M20.5 — Authentic Question Preprocessing Service.

Specialized preprocessing for authentic undergraduate examination questions.
Handles question numbering, marks annotations, examination instructions,
repeated PDF headers/footers, OCR noise, SQL statements, and code fragments
while strictly preserving original question text and domain-specific technical terminology.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# Regex patterns for authentic question artifacts
_QUESTION_NUMBER_PREFIX = re.compile(
    r"^(?:(?:Q(?:uestion)?\s*\d+\s*[\(\.\:\-]?\s*(?:[a-z0-9ivx]+\s*[\)\.\:\-]?)?)|"
    r"(?:\(?[a-z0-9ivx]+\)\s*[\.\:\-]?)|"
    r"(?:(?:Part|Section)\s+[A-Za-z0-9]+\s*[\.\:\-]?)|"
    r"(?:\d+\.(?:\d+\.)?\s*))\s*",
    re.IGNORECASE,
)

_MARKS_ANNOTATION = re.compile(
    r"(?:\(?\[?\s*(?:Total\s*[:\-])?\s*\d+(?:\.\d+)?\s*(?:marks?|Marks?|mks?|Mks?|points?|Points?)\s*\]?\)?)|"
    r"(?:\[\s*\d+(?:\.\d+)?\s*\])|"
    r"(?:\(\s*\d+(?:\.\d+)?\s*\)\s*$)",
    re.IGNORECASE,
)

_EXAM_PREAMBLE = re.compile(
    r"(?:(?:Answer\s+(?:all|any|both|either)\s+(?:questions?|parts?|sections?))|"
    r"(?:Time\s+Allowed\s*[:\-]\s*\d+\s*(?:Hours?|Minutes?))|"
    r"(?:Calculators\s+are\s+(?:permitted|prohibited|allowed))|"
    r"(?:All\s+questions\s+carry\s+equal\s+marks)|"
    r"(?:This\s+paper\s+contains\s+\d+\s+pages?))\b",
    re.IGNORECASE,
)

_PDF_HEADER_FOOTER = re.compile(
    r"(?:Page\s+\d+\s+of\s+\d+)|"
    r"(?:SLIIT\s*(?:Faculty\s+of\s+Computing)?)|"
    r"(?:(?:Final|Mid\s+Semester)\s+Examination\s*[\-–—]?\s*(?:June|October|November|December|January|February|March|April|May)?\s*(?:Intake)?\s*(?:\d{4})?)|"
    r"(?:(?:Year|Semester)\s+\d+\s*(?:Examination)?)|"
    r"(?:oog8\\|C\{|C\s*\{)",
    re.IGNORECASE,
)

# Common OCR errors in Sri Lankan CS/SE past-paper scans
_OCR_FIXES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b8\+\s*tree\b", re.IGNORECASE), "B+ tree"),
    (re.compile(r"\b8\s*tree\b", re.IGNORECASE), "B-tree"),
    (re.compile(r"\b8\+tree\b", re.IGNORECASE), "B+ tree"),
    (re.compile(r"\bporn\.xml\b", re.IGNORECASE), "pom.xml"),
    (re.compile(r"\bIntexpret\b", re.IGNORECASE), "Interpret"),
    (re.compile(r"\bpz\.d\b", re.IGNORECASE), "pid"),
    (re.compile(r"\bpcrr/s\b", re.IGNORECASE), "parts"),
    (re.compile(r"\bczge\b", re.IGNORECASE), "page"),
    (re.compile(r"\bRESTful\s+AP\b", re.IGNORECASE), "RESTful API"),
    (re.compile(r"\bSpring\s+Boot\s+simplify\b", re.IGNORECASE), "Spring Boot simplifies"),
]

# Domain technical acronyms that must NEVER be stripped or lower-cased destructively
PROTECTED_TECHNICAL_ACRONYMS = {
    "ACID", "REST", "UML", "JWT", "API", "SQL", "DBMS", "MVC", "ORM",
    "CI/CD", "COCOMO", "HTA", "WCAG", "JSON", "XML", "HTTP", "HTTPS",
    "SOAP", "WSDL", "RPC", "gRPC", "DOM", "CSS", "HTML", "SOLID", "GRASP",
    "GoF", "ERD", "DFD", "SRS", "BCNF", "2PL", "WAL", "CTE", "MVCC",
    "RDBMS", "NoSQL", "DTO", "DAO", "IoC", "DI", "TDD", "BDD", "FPA",
    "WBS", "CPM", "PERT", "LOC", "KLOC", "SLA", "QoS", "MTBF", "MTTR",
    "ATAM", "CBAM", "ADD", "SOA", "DDD", "CLI", "GUI", "SUS", "NPS",
    "SaaS", "PaaS", "IaaS", "TCP", "UDP", "IP", "DNS", "CORS", "CSRF",
    "XSS", "OAuth", "SSO", "B-Tree", "B+ Tree",
}

# SQL syntax indicators
_SQL_KEYWORDS = re.compile(
    r"\b(SELECT|FROM|WHERE|INSERT\s+INTO|UPDATE|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE|"
    r"DROP\s+TABLE|GROUP\s+BY|ORDER\s+BY|HAVING|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|"
    r"FULL\s+OUTER\s+JOIN|UNION|UNION\s+ALL|EXISTS|NOT\s+EXISTS|COUNT\(|SUM\(|AVG\(|"
    r"MIN\(|MAX\(|PRIMARY\s+KEY|FOREIGN\s+KEY|REFERENCES|CASCADE|VIEW|TRIGGER)\b",
    re.IGNORECASE,
)

# Code syntax indicators
_CODE_KEYWORDS = re.compile(
    r"\b(public\s+class|private\s+|protected\s+|function\s*\(|const\s+[a-zA-Z0-9_]+\s*=|"
    r"let\s+[a-zA-Z0-9_]+\s*=|async\s+function|await\s+|return\s+|import\s+.*from|"
    r"export\s+default|def\s+[a-zA-Z0-9_]+\s*\(|class\s+[a-zA-Z0-9_]+[:\(]|"
    r"@Autowired|@RestController|@GetMapping|@PostMapping|@Entity|@Table)\b",
    re.IGNORECASE,
)


class AuthenticQuestionPreprocessor:
    """Preprocessor for authentic examination questions."""

    def __init__(self, preserve_technical_acronyms: bool = True):
        self.preserve_technical_acronyms = preserve_technical_acronyms

    @classmethod
    def preprocess(cls, question_text: Optional[str], preserve_technical_acronyms: bool = True) -> Dict[str, Any]:
        """Preprocess an authentic question text.

        Returns a dictionary containing:
        - original_text: unmodified original text
        - normalized_text: clean, lower-cased text suitable for TF-IDF / vector models
        - cleaned_display_text: cleaned text preserving formatting for lecturer UI
        - is_empty: whether the question text is empty
        - extracted_marks: any marks mention stripped from text
        - detected_features: technical metadata about the question text
        """
        raw = question_text or ""
        original_text = raw
        clean_raw = raw.strip()

        if not clean_raw:
            return {
                "original_text": original_text,
                "normalized_text": "",
                "cleaned_display_text": "",
                "is_empty": True,
                "extracted_marks": None,
                "detected_features": {
                    "has_sql": False,
                    "has_code": False,
                    "has_question_number": False,
                    "has_marks_annotation": False,
                    "has_ocr_noise": False,
                    "technical_terms": [],
                },
            }

        # 1. Detect features on original text before cleaning
        has_sql = bool(_SQL_KEYWORDS.search(clean_raw))
        has_code = bool(_CODE_KEYWORDS.search(clean_raw))
        has_qnum = bool(_QUESTION_NUMBER_PREFIX.search(clean_raw))

        marks_match = _MARKS_ANNOTATION.search(clean_raw)
        has_marks = bool(marks_match)
        extracted_marks = marks_match.group(0).strip() if marks_match else None

        # Detect technical acronyms present in the question
        found_terms = [
            term for term in PROTECTED_TECHNICAL_ACRONYMS
            if re.search(rf"\b{re.escape(term)}\b", clean_raw, re.IGNORECASE)
        ]

        # 2. Apply text cleaning (preserving case for display)
        display_cleaned = clean_raw

        # Normalize line endings and unicode spaces/dashes/quotes
        display_cleaned = display_cleaned.replace("\r\n", "\n").replace("\r", "\n")
        display_cleaned = re.sub(r"[\u2018\u2019]", "'", display_cleaned)
        display_cleaned = re.sub(r"[\u201C\u201D]", '"', display_cleaned)
        display_cleaned = re.sub(r"[\u2013\u2014]", "-", display_cleaned)
        display_cleaned = display_cleaned.replace("\u00A0", " ")

        # Fix known OCR scanning errors
        has_ocr_noise = False
        for pattern, replacement in _OCR_FIXES:
            if pattern.search(display_cleaned):
                has_ocr_noise = True
                display_cleaned = pattern.sub(replacement, display_cleaned)

        # Strip PDF headers/footers
        display_cleaned = _PDF_HEADER_FOOTER.sub(" ", display_cleaned)

        # Strip repeated question number prefix
        display_cleaned = _QUESTION_NUMBER_PREFIX.sub("", display_cleaned)

        # Strip marks annotations (e.g., "(5 Marks)")
        display_cleaned = _MARKS_ANNOTATION.sub(" ", display_cleaned)

        # Collapse whitespace while preserving single newlines for readable code/SQL
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in display_cleaned.split("\n")]
        display_cleaned = "\n".join(line for line in lines if line)

        # 3. Create normalized text for semantic & ML models
        # Lower-cased, single-spaced string, punctuation handled defensively
        norm_text = display_cleaned.lower()
        # Collapse multiple spaces and linebreaks into single spaces
        norm_text = re.sub(r"\s+", " ", norm_text).strip()

        # If normalization completely emptied the text, fallback to lower-cased original
        if not norm_text and clean_raw:
            norm_text = re.sub(r"\s+", " ", clean_raw.lower()).strip()

        return {
            "original_text": original_text,
            "normalized_text": norm_text,
            "cleaned_display_text": display_cleaned,
            "is_empty": False,
            "extracted_marks": extracted_marks,
            "detected_features": {
                "has_sql": has_sql,
                "has_code": has_code,
                "has_question_number": has_qnum,
                "has_marks_annotation": has_marks,
                "has_ocr_noise": has_ocr_noise,
                "technical_terms": found_terms,
            },
        }

    @staticmethod
    def normalize_for_similarity(text: str) -> str:
        """Convenience method returning lower-cased single-spaced cleaned text."""
        p = AuthenticQuestionPreprocessor()
        res = p.preprocess(text)
        return res["normalized_text"]
