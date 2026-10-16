
import re
from collections import defaultdict


class SyllabusTopicCandidateExtractor:
    """
    Extract potential syllabus topics from lecture documents.

    Candidates are unverified until reviewed against
    authentic lecturer-provided syllabus evidence.
    """

    MIN_LENGTH = 4
    MAX_LENGTH = 100
    MAX_WORDS = 12

    GENERIC_HEADINGS = {
        "introduction",
        "overview",
        "summary",
        "conclusion",
        "references",
        "thank you",
        "questions",
        "learning outcomes",
        "learning objectives",
        "contents",
        "agenda",
        "recap",
    }

    def normalize(self, text):
        if not isinstance(text, str):
            raise ValueError("Topic text must be a string")

        return " ".join(text.lower().split())

    def clean_heading(self, text):
        text = text.strip()

        # Remove common heading prefixes.
        text = re.sub(
            r"^(?:lecture|week|topic|chapter|unit|slide)"
            r"\s*\d+\s*[:.\-–]\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Remove bullet or numbering prefixes.
        text = re.sub(
            r"^\s*(?:[•\-*]|\d+[.)])\s*",
            "",
            text,
        )

        return " ".join(text.split())

    def is_candidate(self, text):
        if not isinstance(text, str):
            return False

        text = self.clean_heading(text)

        if not (
            self.MIN_LENGTH <= len(text) <= self.MAX_LENGTH
        ):
            return False

        if len(text.split()) > self.MAX_WORDS:
            return False

        if not re.search(r"[A-Za-z]", text):
            return False

        if self.normalize(text) in self.GENERIC_HEADINGS:
            return False

        # Avoid obvious sentences and questions.
        if text.endswith((".", "?", "!", ";")):
            return False

        return True

    def extract(self, module_key, documents):
        """
        Extract and deduplicate candidate headings
        from one module's lecture documents.
        """
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Invalid module key")

        if not isinstance(documents, list):
            raise ValueError("Documents must be a list")

        candidates = {}

        for document in documents:
            if not isinstance(document, dict):
                raise ValueError("Invalid lecture document")

            filename = document.get("filename")
            text = document.get("text")

            if not isinstance(filename, str) or not filename.strip():
                raise ValueError("Invalid source filename")

            if not isinstance(text, str):
                raise ValueError("Invalid lecture text")

            # First-pass heuristic: short, standalone lines
            # are treated as possible headings.
            for line_number, line in enumerate(
                text.splitlines(), start=1
            ):
                heading = self.clean_heading(line)

                if not self.is_candidate(heading):
                    continue

                key = self.normalize(heading)

                if key not in candidates:
                    candidates[key] = {
                        "module_key": module_key,
                        "candidate_name": heading,
                        "verification_status": "unverified",
                        "extraction_method": "rule_based",
                        "sources": [],
                    }

                source = {
                    "filename": filename,
                    "line_number": line_number,
                }

                if source not in candidates[key]["sources"]:
                    candidates[key]["sources"].append(source)

        results = sorted(
            candidates.values(),
            key=lambda item: item["candidate_name"].lower(),
        )

        return {
            "schema_version": "1.0",
            "module_key": module_key,
            "candidate_count": len(results),
            "candidates": results,
        }

    def extract_all(self, module_processing_result):
        """
        Extract topic candidates for all processed modules.
        """
        if not isinstance(module_processing_result, dict):
            raise ValueError("Invalid module processing result")

        modules = module_processing_result.get("modules")

        if not isinstance(modules, dict):
            raise ValueError("Modules must be an object")

        results = {}
        total_candidates = 0

        for module_key, module_data in sorted(modules.items()):
            if not isinstance(module_data, dict):
                raise ValueError("Invalid module data")

            documents = module_data.get("documents")

            result = self.extract(module_key, documents)
            results[module_key] = result
            total_candidates += result["candidate_count"]

        return {
            "schema_version": "1.0",
            "summary": {
                "total_modules": len(results),
                "total_candidates": total_candidates,
            },
            "modules": results,
        }
