
import copy
import math
import re
from collections import defaultdict


class SyllabusTopicCandidateRanker:
    """
    Rank filtered syllabus topic candidates for manual review.

    Ranking scores indicate review priority, not verification
    confidence. Administrative candidates are excluded from the
    ranked list but preserved separately for auditing.
    """

    SCHEMA_VERSION = "1.0"

    ADMINISTRATIVE_PATTERNS = [
        re.compile(r"^subject name$", re.I),
        re.compile(r"^semester\s+\d+\s*,?\s*\d{4}$", re.I),
        re.compile(r"^department of software(?: engineering)?$", re.I),
        re.compile(r"^sliit(?:\s*-\s*faculty of computing)?$", re.I),
        re.compile(
            r"^references?\s*(?:&|and)\s*further reading$",
            re.I,
        ),
        re.compile(r"^acknowledg(?:e)?ments?$", re.I),
        re.compile(r"^thank(?:\s+you)?\s*[\u2026.!]*$", re.I),
        re.compile(r"^this lecture\s*[\u2026.!]*$", re.I),
        re.compile(r"^this week$", re.I),
        re.compile(r"^example$", re.I),

        # Lecturer attribution: requires capitalized name components.
        re.compile(
            r"^by\s+[A-Z][a-z]+"
            r"(?:\s+(?:[A-Z]\.?|[A-Z][a-z]+)){1,4}$"
        ),

        # Lecturer titles: require a full name.
        re.compile(
            r"^(?:Mr|Mrs|Ms|Dr|Prof)\.\s+"
            r"[A-Z][a-z]+\s+[A-Z][a-z]+$"
        ),
    ]

    def is_administrative_candidate(self, name):
        """
        Identify obvious administrative or presentation text.
        """
        text = name.strip()

        return any(
            pattern.fullmatch(text)
            for pattern in self.ADMINISTRATIVE_PATTERNS
        )

    def normalize(self, text):
        """
        Normalize candidate names for duplicate grouping.
        """
        text = text.strip().casefold()
        text = re.sub(r"\s+", " ", text)
        return text

    def heading_quality_score(self, name):
        """
        Calculate heading quality out of 40 points.
        """
        text = name.strip()
        words = text.split()

        if not text:
            return 0

        score = 0

        if 2 <= len(words) <= 6:
            score += 20
        elif len(words) == 1:
            score += 15
        elif len(words) <= 10:
            score += 10

        if 5 <= len(text) <= 60:
            score += 10
        elif len(text) <= 90:
            score += 5

        if not re.search(r"[.!?;]$", text):
            score += 10

        return min(score, 40)

    def occurrence_score(self, count):
        """
        Calculate occurrence frequency score out of 30 points.
        """
        if count <= 0:
            return 0

        return min(
            30,
            round(
                30 * math.log1p(count) / math.log1p(10)
            ),
        )

    def document_coverage_score(self, count):
        """
        Calculate distinct document coverage score out of 30.
        """
        if count <= 0:
            return 0

        return min(30, count * 10)

    def rank_module(self, module_data):
        """
        Rank candidates within one module.

        Administrative candidates are excluded from ranking
        but preserved in excluded_candidates.
        """
        if not isinstance(module_data, dict):
            raise ValueError(
                "module_data must be a dictionary"
            )

        module_key = module_data.get("module_key")
        candidates = module_data.get("candidates")

        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Missing module_key")

        if not isinstance(candidates, list):
            raise ValueError("Missing candidates list")

        grouped = defaultdict(list)

        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("Invalid candidate")

            if candidate.get("module_key") != module_key:
                raise ValueError("Candidate module mismatch")

            name = candidate.get("candidate_name")

            if not isinstance(name, str) or not name.strip():
                raise ValueError("Invalid candidate name")

            if candidate.get("verification_status") != "unverified":
                raise ValueError(
                    "Ranking expects unverified candidates"
                )

            sources = candidate.get("sources")

            if not isinstance(sources, list):
                raise ValueError("Invalid candidate sources")

            # Validate all source references, including those
            # belonging to administrative candidates.
            for source in sources:
                if not isinstance(source, dict):
                    raise ValueError("Invalid source reference")

                filename = source.get("filename")
                line_number = source.get("line_number")

                if (
                    not isinstance(filename, str)
                    or not filename.strip()
                    or not isinstance(line_number, int)
                    or isinstance(line_number, bool)
                    or line_number < 1
                ):
                    raise ValueError("Invalid source reference")

            grouped[self.normalize(name)].append(candidate)

        ranked_candidates = []
        excluded_candidates = []

        for normalized_name, matching_candidates in grouped.items():
            representative = matching_candidates[0]
            name = representative["candidate_name"]

            if self.is_administrative_candidate(name):
                excluded_candidates.extend(
                    copy.deepcopy(matching_candidates)
                )
                continue

            source_map = {}

            for candidate in matching_candidates:
                for source in candidate["sources"]:
                    key = (
                        source["filename"],
                        source["line_number"],
                    )
                    source_map[key] = copy.deepcopy(source)

            sources = sorted(
                source_map.values(),
                key=lambda item: (
                    item["filename"].casefold(),
                    item["line_number"],
                ),
            )

            distinct_documents = {
                source["filename"]
                for source in sources
            }

            occurrence_count = len(sources)
            document_count = len(distinct_documents)

            quality = self.heading_quality_score(name)
            frequency = self.occurrence_score(
                occurrence_count
            )
            coverage = self.document_coverage_score(
                document_count
            )

            priority_score = (
                quality + frequency + coverage
            )

            ranked = copy.deepcopy(representative)

            ranked["sources"] = sources
            ranked["normalized_candidate_name"] = (
                normalized_name
            )
            ranked["occurrence_count"] = occurrence_count
            ranked["document_count"] = document_count
            ranked["ranking_score"] = priority_score

            ranked["ranking_breakdown"] = {
                "heading_quality": quality,
                "occurrence_frequency": frequency,
                "document_coverage": coverage,
            }

            # Never automatically verify a candidate.
            ranked["verification_status"] = "unverified"

            ranked_candidates.append(ranked)

        ranked_candidates.sort(
            key=lambda candidate: (
                -candidate["ranking_score"],
                -candidate["document_count"],
                -candidate["occurrence_count"],
                candidate["normalized_candidate_name"],
            )
        )

        for position, candidate in enumerate(
            ranked_candidates,
            start=1,
        ):
            candidate["rank"] = position

        input_count = len(candidates)
        ranked_count = len(ranked_candidates)
        excluded_count = len(excluded_candidates)

        merged_count = (
            input_count - excluded_count - ranked_count
        )

        return {
            "schema_version": self.SCHEMA_VERSION,
            "module_key": module_key,
            "summary": {
                "input_candidate_count": input_count,
                "ranked_candidate_count": ranked_count,
                "excluded_candidate_count": excluded_count,
                "merged_duplicate_count": merged_count,
            },
            "candidates": ranked_candidates,
            "excluded_candidates": excluded_candidates,
        }

    def rank_all(self, filtered_data):
        """
        Rank candidates across all modules.
        """
        if not isinstance(filtered_data, dict):
            raise ValueError(
                "filtered_data must be a dictionary"
            )

        modules = filtered_data.get("modules")

        if not isinstance(modules, dict):
            raise ValueError("Missing modules dictionary")

        ranked_modules = {}

        total_input = 0
        total_ranked = 0
        total_excluded = 0

        for module_key, module_data in modules.items():
            ranked = self.rank_module(module_data)

            if ranked["module_key"] != module_key:
                raise ValueError(
                    "Module dictionary key mismatch"
                )

            ranked_modules[module_key] = ranked

            summary = ranked["summary"]

            total_input += summary["input_candidate_count"]
            total_ranked += summary["ranked_candidate_count"]
            total_excluded += summary["excluded_candidate_count"]

        total_merged = (
            total_input - total_excluded - total_ranked
        )

        return {
            "schema_version": self.SCHEMA_VERSION,
            "summary": {
                "module_count": len(ranked_modules),
                "input_candidate_count": total_input,
                "ranked_candidate_count": total_ranked,
                "excluded_candidate_count": total_excluded,
                "merged_duplicate_count": total_merged,
            },
            "modules": ranked_modules,
        }
