
import re
from copy import deepcopy


class SyllabusTopicCandidateFilter:
    """Filter obvious noise from extracted syllabus topic candidates."""

    NOISE_PHRASES = {
        "all rights reserved",
        "thank you for your attention",
        "click here to continue",
        "end of presentation",
        "any questions",
        "questions and answers",
        "learning outcomes",
        "learning objectives",
        "table of contents",
        "course information",
        "contact information",
        "references",
        "bibliography",
        "acknowledgements",
    }
    SHORT_TECHNICAL_TERMS = {
        "sql",
        "api",
        "uml",
        "xml",
        "css",
        "git",
        "jwt",
        "orm",
        "oop",
        "erd",
        "ux",
        "ui",
    }

    NOISE_PATTERNS = [
        re.compile(r"https?://|www\.", re.IGNORECASE),
        re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE),
        re.compile(
            r"^(?:figure|fig\.?|table|image|diagram)\s*\d+"
            r"(?:[.: -]|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(?:page|slide)\s+\d+\s*(?:of\s+\d+)?$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(?:copyright|©|\(c\))\s*",
            re.IGNORECASE,
        ),
        re.compile(
            r"^(?:example|exercise|activity|quiz)\s*\d+"
            r"(?:[.: -]|$)",
            re.IGNORECASE,
        ),
    ]
    QUALITY_NOISE_PATTERNS = [
        # XML/HTML fragments.
        re.compile(r"^\s*</?[a-z][\w:-]*(?:\s[^>]*)?>\s*$", re.I),

        # SQL/code fragments beginning with punctuation.
        re.compile(r"^\s*\(\s*[a-z_]\w*\s+(?:number|varchar2?|nvarchar|int|integer|char)\b", re.I),

        # Standalone MongoDB operators.
        re.compile(r"^\s*\$[a-z][a-z0-9_]*\s*$", re.I),

        # SQL commands and code-like fragments.
        re.compile(r"^\s*(?:select|insert|update|delete|create|alter|drop)\s+.*[;()]$", re.I),

        # Course metadata.
        re.compile(r"^\s*\d+(?:st|nd|rd|th)\s+year\b", re.I),
        re.compile(r"^\s*semester\s+\d+\s*$", re.I),

        # Standalone slide continuation labels.
        re.compile(r"^\s*\(?\s*(?:contd?\.?|continued)\s*\)?$", re.I),

        # Numbered infrastructure inventory labels.
        re.compile(
            r"^\s*\d+\s+(?:iis\s+web\s+servers?|firewalls?|"
            r"networks?|redis\s+servers?|elasticsearch\s+servers?|"
            r"cisco\s+routers?|haproxy\s+load\s+balancers?|"
            r"microsoft\s+sql\s+servers?)\s*$",
            re.I,
        ),

        # Text that begins like an incomplete explanatory sentence.
        re.compile(
            r"^\s*(?:a|an|the)\s+(?:collection|group|set|number|"
            r"way|process)\s+of\b",
            re.I,
        ),

        # Some presentation fragments.
        re.compile(r"^\s*\(\s*(?:discussed|assuming|creates)\b", re.I),

        # XML/HTML tags, including quoted fragments.
        re.compile(
            r"""^\s*['"`]?\s*</?[A-Za-z][\w:-]*(?:\s[^>]*)?>\s*$""",
            re.I,
        ),

        # MongoDB operators followed by explanatory fragments.
        re.compile(
            r"^\s*\$[a-z][a-z0-9_]*\s*:",
            re.I,
        ),

        # SQL conditions and code expressions.
        re.compile(
            r"^\s*\(?\s*[\w.]+\s*(?:=|<>|<=|>=)\s*['\w]",
            re.I,
        ),

        # SQL schema fragments.
        re.compile(
            r"^\s*\(?\s*[A-Za-z_]\w*\s+PRIMARY\s+KEY\s*\)?$",
            re.I,
        ),

        # Incomplete quoted fragments.
        re.compile(
            r"""^\s*["'`].*["'`]?\s*$""",
            re.I,
        ),

        # Infrastructure inventory counts.
        re.compile(
            r"^\s*\d+\s+(?:tag engine|haproxy|redis|web|database)"
            r"\s+servers?\b",
            re.I,
        ),

        # Letter-spaced presentation headings.
        re.compile(
            r"^(?:[A-Za-z]\s+){4,}[A-Za-z]$",
        ),

        # Dialogue or presentation speaker labels.
        re.compile(
            r"^[A-Za-z]:\s+",
        ),
        # MongoDB operators followed by descriptions.
        re.compile(
            r"^\s*\$[a-z][a-z0-9_]*\b",
            re.I,
        ),

        # XPath and XML query expressions.
        re.compile(
            r"^\s*(?:/|//)[A-Za-z/*@\[\]]",
            re.I,
        ),

        # Mathematical expressions enclosed in parentheses.
        re.compile(
            r"^\s*\([^)]*(?:<=|>=|<|>)\s*[^)]*\)?$",
        ),

        # Incomplete parenthesized explanatory fragments.
        re.compile(
            r"^\s*\((?:note that|except root|use of|execution)\b",
            re.I,
        ),

        # Common infrastructure inventory descriptions.
        re.compile(
            r"^\s*\d+\s+.*(?:servers?|load balancers?|routers?)\b",
            re.I,
        ),

        # Letter-spaced presentation text.
        re.compile(
            r"^(?:[A-Za-z]\s+){3,}[A-Za-z]+$",
        ),

        # Incomplete explanatory sentences.
        re.compile(
            r"^\s*(?:a decade ago|a paradigm shift|"
            r"a key architectural decision|"
            r"about finding opportunities)\b",
            re.I,
        ),
    ]

    def __init__(self, min_length=4, max_length=100, max_words=12):
        if (
            not isinstance(min_length, int)
            or not isinstance(max_length, int)
            or not isinstance(max_words, int)
            or isinstance(min_length, bool)
            or isinstance(max_length, bool)
            or isinstance(max_words, bool)
            or min_length < 1
            or max_length < min_length
            or max_words < 1
        ):
            raise ValueError("Invalid filtering limits")

        self.min_length = min_length
        self.max_length = max_length
        self.max_words = max_words

    @staticmethod
    def normalize(text):
        return " ".join(text.lower().split())

    def get_rejection_reason(self, candidate_name):
        """Return a rejection reason, or None if candidate passes."""

        if not isinstance(candidate_name, str):
            return "invalid_text"

        text = " ".join(candidate_name.split())

        if not text:
            return "empty_text"

        is_short_technical_term = (
            self.normalize(text) in self.SHORT_TECHNICAL_TERMS
        )

        if len(text) > self.max_length:
            return "invalid_length"

        if (
            len(text) < self.min_length
            and not is_short_technical_term
        ):
            return "invalid_length"

        if len(text.split()) > self.max_words:
            return "too_many_words"

        if not re.search(r"[A-Za-z]", text):
            return "no_alphabetic_content"

        if self.normalize(text) in self.NOISE_PHRASES:
            return "generic_noise_phrase"

        if text.endswith(("?", "!", ";")):
            return "sentence_or_question"

        for pattern in self.NOISE_PATTERNS:
            if pattern.search(text):
                return "noise_pattern"

        for pattern in self.QUALITY_NOISE_PATTERNS:
            if pattern.search(text):
                return "quality_noise_pattern"

        if text.endswith((",", ":", "=", "(", "/")):
            return "incomplete_fragment"

        if (
            text.startswith("(")
            and text.endswith(")")
            and len(text.split()) <= 3
            and self.normalize(text.strip("()")) in {
                "data file",
                "direct search",
                "easier modifications",
                "discussed later",
            }
        ):
            return "presentation_fragment"

        return None

    def filter(self, extraction_result):
        """Filter one module's candidate extraction result."""

        if not isinstance(extraction_result, dict):
            raise ValueError("Extraction result must be an object")

        if extraction_result.get("schema_version") != "1.0":
            raise ValueError("Unsupported extraction schema version")

        module_key = extraction_result.get("module_key")

        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Invalid module key")

        candidates = extraction_result.get("candidates")

        if not isinstance(candidates, list):
            raise ValueError("Candidates must be a list")

        if extraction_result.get("candidate_count") != len(candidates):
            raise ValueError("Candidate count mismatch")

        kept = []
        rejected = []

        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("Invalid candidate record")

            if candidate.get("module_key") != module_key:
                raise ValueError("Candidate module mismatch")

            if candidate.get("verification_status") != "unverified":
                raise ValueError(
                    "Filtering requires unverified candidates"
                )

            if not isinstance(candidate.get("sources"), list):
                raise ValueError("Candidate sources must be a list")

            record = deepcopy(candidate)

            reason = self.get_rejection_reason(
                record.get("candidate_name")
            )

            if reason is None:
                kept.append(record)
            else:
                rejected.append({
                    "candidate": record,
                    "rejection_reason": reason,
                })

        summary = {
            "total_candidates": len(candidates),
            "kept": len(kept),
            "rejected": len(rejected),
        }

        return {
            "schema_version": "1.0",
            "module_key": module_key,
            "summary": summary,
            "candidates": kept,
            "rejected_candidates": rejected,
        }

    def filter_all(self, extraction_result):
        """Filter candidate collections for all modules."""

        if not isinstance(extraction_result, dict):
            raise ValueError("Extraction result must be an object")

        if extraction_result.get("schema_version") != "1.0":
            raise ValueError("Unsupported extraction schema version")

        modules = extraction_result.get("modules")

        if not isinstance(modules, dict):
            raise ValueError("Modules must be an object")

        results = {}

        summary = {
            "total_modules": len(modules),
            "total_candidates": 0,
            "kept": 0,
            "rejected": 0,
        }

        for module_key, module_result in sorted(modules.items()):
            filtered = self.filter(module_result)

            if filtered["module_key"] != module_key:
                raise ValueError("Module key mismatch")

            results[module_key] = filtered

            for field in ("total_candidates", "kept", "rejected"):
                summary[field] += filtered["summary"][field]

        return {
            "schema_version": "1.0",
            "summary": summary,
            "modules": results,
        }
