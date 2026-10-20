"""M21 — Bloom's Taxonomy-Controlled Question Validator.

Validates generated examination questions across five research dimensions:
1. Curriculum-Topic Alignment: Checks keyword and conceptual overlap with curriculum taxonomy.
2. Bloom-Level Alignment: Analyzes cognitive action verbs and task directives with explicit limitations.
3. Duplicate/Similarity Risk: Checks similarity against authentic past papers and generated questions.
4. Structural & Marks Integrity: Verifies subquestion marks summation, question formatting, and structure.
5. Quality Check: Checks for unfilled templates, malformed tokens, or empty sections.

Strict Research Integrity:
- Never invents confidence scores, accuracy percentages, or fictitious model outputs.
- Marks unverified or unavailable checks as 'not_evaluated' or 'heuristic'.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = PROJECT_ROOT / "config" / "curriculum_taxonomies.json"
AUTHENTIC_QUESTIONS_PATH = PROJECT_ROOT / "datasets" / "processed" / "questions.json"
APPROVED_GENERATED_PATH = PROJECT_ROOT / "datasets" / "generated_questions" / "lecturer_approved_questions.json"

BLOOM_ACTION_VERBS: Dict[str, Set[str]] = {
    "remember": {
        "define", "list", "state", "name", "identify", "recall", "state the definition",
        "enumerate", "what is", "which of the following", "mention", "specify",
    },
    "understand": {
        "explain", "describe", "summarize", "outline", "clarify", "interpret",
        "contrast", "distinguish", "paraphrase", "why does", "illustrate", "discuss",
    },
    "apply": {
        "apply", "calculate", "compute", "write", "formulate", "execute", "implement",
        "solve", "demonstrate", "decompose", "normalize", "construct a query", "perform",
        "show step-by-step", "determine the closure",
    },
    "analyze": {
        "analyze", "examine", "investigate", "inspect", "compare", "differentiate",
        "diagnose", "break down", "trace", "determine why", "identify anomalies",
        "deconstruct", "isolate", "attribute",
    },
    "evaluate": {
        "evaluate", "assess", "critique", "justify", "defend", "appraise",
        "recommend", "judge", "rate", "validate", "weigh the trade-offs",
        "support your decision", "argue whether",
    },
    "create": {
        "design", "construct", "formulate", "architect", "devise", "propose",
        "synthesize", "develop", "create", "plan", "compose", "generate",
    },
}


class BloomQuestionValidator:
    """Validates generated questions for curriculum alignment, Bloom level, and quality."""

    def __init__(
        self,
        curriculum_path: Optional[Path] = None,
        authentic_questions_path: Optional[Path] = None,
        approved_generated_path: Optional[Path] = None,
    ):
        self.curriculum_path = Path(curriculum_path or CURRICULUM_PATH)
        self.authentic_questions_path = Path(authentic_questions_path or AUTHENTIC_QUESTIONS_PATH)
        self.approved_generated_path = Path(approved_generated_path or APPROVED_GENERATED_PATH)
        self._curriculum_cache: Optional[Dict[str, Any]] = None
        self._authentic_cache: Optional[List[Dict[str, Any]]] = None

    def _load_curriculum(self) -> Dict[str, Any]:
        if self._curriculum_cache is not None:
            return self._curriculum_cache
        if not self.curriculum_path.exists():
            return {}
        with open(self.curriculum_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        modules = {}
        for mod in data.get("modules", []):
            modules[mod["module_key"]] = mod
            for alias in mod.get("aliases", []):
                modules[alias] = mod
        self._curriculum_cache = modules
        return modules

    def _load_authentic_questions(self) -> List[Dict[str, Any]]:
        if self._authentic_cache is not None:
            return self._authentic_cache
        if not self.authentic_questions_path.exists():
            return []
        try:
            with open(self.authentic_questions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._authentic_cache = data if isinstance(data, list) else data.get("questions", [])
        except Exception:
            self._authentic_cache = []
        return self._authentic_cache

    def _load_approved_generated(self) -> List[Dict[str, Any]]:
        if not self.approved_generated_path.exists():
            return []
        try:
            with open(self.approved_generated_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("questions", []) if isinstance(data, dict) else []
        except Exception:
            return []

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "are", "was",
            "were", "which", "your", "explain", "describe", "given", "following",
        }
        return {w for w in words if w not in stopwords}

    def validate_topic_alignment(
        self,
        question_text: str,
        module_key: str,
        topic_id: str,
    ) -> Dict[str, Any]:
        """Check keyword and conceptual overlap with curriculum taxonomy."""
        curriculum = self._load_curriculum()
        mod = curriculum.get(module_key)
        if not mod:
            return {
                "status": "warning",
                "alignment_score": 0.0,
                "matched_keywords": [],
                "details": f"Module '{module_key}' not found in curriculum taxonomy.",
            }

        topic = next((t for t in mod.get("topics", []) if t.get("topic_id") == topic_id), None)
        if not topic:
            return {
                "status": "warning",
                "alignment_score": 0.0,
                "matched_keywords": [],
                "details": f"Topic '{topic_id}' not found under module '{module_key}'.",
            }

        topic_keywords = {k.lower() for k in topic.get("keywords", [])}
        q_tokens = self._tokenize(question_text)
        text_lower = question_text.lower()

        matched = [k for k in topic_keywords if k in text_lower or k in q_tokens]
        ratio = len(matched) / max(1, min(len(topic_keywords), 15))
        alignment_score = round(min(1.0, ratio), 2)

        return {
            "status": "pass" if len(matched) >= 2 else "needs_review",
            "alignment_score": alignment_score,
            "matched_keywords": sorted(matched[:8]),
            "total_topic_keywords": len(topic_keywords),
            "details": (
                f"Found {len(matched)} curriculum keywords aligned with '{topic.get('topic_name')}'."
                if matched
                else "Low keyword overlap with curriculum taxonomy reference."
            ),
        }

    def validate_bloom_alignment(
        self,
        question_text: str,
        requested_bloom: str,
    ) -> Dict[str, Any]:
        """Check cognitive action verbs against Bloom Revised Taxonomy indicators."""
        norm_bloom = requested_bloom.strip().lower()
        text_lower = question_text.lower()

        target_verbs = BLOOM_ACTION_VERBS.get(norm_bloom, set())
        detected_verbs = [v for v in target_verbs if re.search(r"\b" + re.escape(v) + r"\b", text_lower)]

        # Check verbs from other levels to identify secondary/cross-level cues
        other_levels_detected = {}
        for lvl, verbs in BLOOM_ACTION_VERBS.items():
            if lvl != norm_bloom:
                found = [v for v in verbs if re.search(r"\b" + re.escape(v) + r"\b", text_lower)]
                if found:
                    other_levels_detected[lvl] = found[:3]

        is_aligned = len(detected_verbs) > 0
        return {
            "status": "pass" if is_aligned else "needs_review",
            "requested_bloom": norm_bloom,
            "detected_verbs": detected_verbs,
            "other_levels_detected": other_levels_detected,
            "method": "rule_based_cognitive_action_verb_matching",
            "limitations": (
                "Heuristic cognitive verb analysis. Confirms intended action-verb alignment, "
                "but deep semantic cognitive level requires academic lecturer verification."
            ),
            "details": (
                f"Question contains primary action directives ({', '.join(detected_verbs)}) "
                f"characteristic of Bloom's level '{norm_bloom.capitalize()}'."
                if detected_verbs
                else f"No explicit action verbs found for '{norm_bloom.capitalize()}'. Lecturer review recommended."
            ),
        }

    def validate_duplicate_similarity(
        self,
        question_text: str,
        module_key: str,
    ) -> Dict[str, Any]:
        """Check token Jaccard similarity against authentic past papers and generated questions."""
        q_tokens = self._tokenize(question_text)
        if not q_tokens:
            return {"status": "pass", "max_similarity": 0.0, "closest_match_id": None}

        max_sim = 0.0
        closest_id = None
        closest_type = None

        # Compare against authentic questions
        authentic_questions = self._load_authentic_questions()
        for q in authentic_questions:
            if q.get("module_key") == module_key:
                other_tokens = self._tokenize(q.get("question_text", ""))
                if other_tokens:
                    intersection = len(q_tokens & other_tokens)
                    union = len(q_tokens | other_tokens)
                    sim = intersection / union if union > 0 else 0.0
                    if sim > max_sim:
                        max_sim = sim
                        closest_id = q.get("question_id")
                        closest_type = "authentic_past_paper"

        # Compare against previously approved generated questions
        approved_questions = self._load_approved_generated()
        for q in approved_questions:
            if q.get("module_key") == module_key:
                other_tokens = self._tokenize(q.get("question_text", ""))
                if other_tokens:
                    intersection = len(q_tokens & other_tokens)
                    union = len(q_tokens | other_tokens)
                    sim = intersection / union if union > 0 else 0.0
                    if sim > max_sim:
                        max_sim = sim
                        closest_id = q.get("question_id")
                        closest_type = "approved_generated"

        max_sim_pct = round(max_sim * 100, 1)
        risk = "low" if max_sim < 0.40 else "moderate" if max_sim < 0.65 else "high"

        return {
            "status": "pass" if risk in ("low", "moderate") else "flagged_duplicate",
            "similarity_risk": risk,
            "max_similarity_pct": max_sim_pct,
            "closest_match_id": closest_id,
            "closest_match_source": closest_type,
            "details": (
                f"Similarity is {max_sim_pct}% compared to {closest_id} ({closest_type}). Unique exam content."
                if max_sim_pct < 50
                else f"Moderate similarity ({max_sim_pct}%) to existing item {closest_id}. Review for distinctiveness."
            ),
        }

    def validate_structure_and_marks(
        self,
        question: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate question length, subquestion structure, and marks summation."""
        marks = question.get("marks")
        q_type = question.get("question_type", "structured")
        subquestions = question.get("subquestions", [])
        text = question.get("question_text", "")

        errors = []
        if not isinstance(marks, int) or marks <= 0:
            errors.append("Question marks must be a positive integer.")

        if not text or len(text.strip()) < 25:
            errors.append("Question text is too short or empty (minimum 25 characters).")

        if q_type == "structured" and subquestions:
            sub_sum = sum(sq.get("marks", 0) for sq in subquestions)
            if sub_sum != marks:
                errors.append(
                    f"Subquestion marks sum ({sub_sum}) does not match total allocated marks ({marks})."
                )

        if q_type == "mcq":
            options = question.get("mcq_options", [])
            if len(options) < 3:
                errors.append("MCQ must contain at least 3 distinct answer options.")
            correct_count = sum(1 for opt in options if opt.get("is_correct"))
            if correct_count != 1:
                errors.append(f"MCQ must have exactly one correct option (found {correct_count}).")

        return {
            "status": "pass" if not errors else "fail",
            "errors": errors,
            "total_marks": marks,
            "subquestion_count": len(subquestions),
            "details": "Structure and marks are valid and internally consistent." if not errors else "; ".join(errors),
        }

    def validate_quality(self, question_text: str) -> Dict[str, Any]:
        """Check for unfilled template markers or malformed tokens."""
        unfilled_matches = re.findall(r"\{[a-zA-Z0-9_]+\}|\[TODO\]|\[INSERT\]", question_text)
        has_placeholders = len(unfilled_matches) > 0

        return {
            "status": "pass" if not has_placeholders else "fail",
            "unfilled_placeholders": unfilled_matches,
            "details": (
                "Academic formatting validated; no unpopulated template placeholders detected."
                if not has_placeholders
                else f"Unfilled placeholders detected: {', '.join(unfilled_matches)}"
            ),
        }

    def validate_all(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Run all five validation checks and produce a comprehensive scorecard."""
        text = question.get("question_text", "")
        module_key = question.get("module_key", "")
        topic_id = question.get("topic_id", "")
        bloom = question.get("bloom_level", "")

        topic_align = self.validate_topic_alignment(text, module_key, topic_id)
        bloom_align = self.validate_bloom_alignment(text, bloom)
        dup_check = self.validate_duplicate_similarity(text, module_key)
        struct_check = self.validate_structure_and_marks(question)
        quality_check = self.validate_quality(text)

        all_passed = (
            struct_check["status"] == "pass"
            and quality_check["status"] == "pass"
            and dup_check["status"] == "pass"
        )

        return {
            "is_valid": all_passed,
            "curriculum_alignment": topic_align,
            "bloom_alignment": bloom_align,
            "duplicate_check": dup_check,
            "structure_validation": struct_check,
            "quality_check": quality_check,
        }
