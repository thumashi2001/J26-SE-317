"""M20.5 — Taxonomy-Aware Hybrid Topic Candidate Ranker.

Combines three transparent signals:
1. Signal A: Existing trained M17 scikit-learn model confidence (reused without retraining).
2. Signal B: Taxonomy keyword and technical terminology matching.
3. Signal C: TF-IDF semantic cosine similarity against curriculum reference texts.

Strict Research Integrity Constraints:
- Combined score is NOT a calibrated probability; labeled explicitly as 'hybrid_ranking_score'.
- Separates human review candidate suggestions from formal automated classification.
- Preserves the 0.38 M17 threshold for formal automated classification.
- Returns top-3 ranked topic candidates with detailed signal breakdowns and explanations.
- Deterministic execution without external API dependencies or heavy auto-downloads.
"""

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.authentic_question_preprocessor import AuthenticQuestionPreprocessor
from services.m17_topic_prediction_service import (
    M17TopicPredictionService,
    ModelNotFoundError,
    _slug,
)

BASE_DIR = Path(__file__).resolve().parents[1]
CURRICULUM_TAXONOMY_PATH = BASE_DIR / "config" / "curriculum_taxonomies.json"
MODULES_PATH = BASE_DIR / "config" / "modules.json"

CANONICAL_MODULE_ALIASES = {
    "case_studies_in_software_engineering": "case_studies_software_engineering",
    "software_engineering_process_and_quality_management": "software_engineering_process_quality_management",
}


class HybridTopicCandidateRanker:
    """Ranks curriculum topic candidates for authentic examination questions."""

    def __init__(
        self,
        curriculum_path: Optional[Path] = None,
        m17_predictor: Optional[M17TopicPredictionService] = None,
        modules_path: Optional[Path] = None,
        m17_formal_threshold: float = 0.38,
        suggestion_threshold: float = 0.20,
        low_confidence_threshold: float = 0.05,
    ):
        self.curriculum_path = Path(curriculum_path or CURRICULUM_TAXONOMY_PATH)
        self.modules_path = Path(modules_path or MODULES_PATH)
        self.m17_predictor = m17_predictor or M17TopicPredictionService()
        self.m17_formal_threshold = m17_formal_threshold
        self.suggestion_threshold = suggestion_threshold
        self.low_confidence_threshold = low_confidence_threshold

        self.curriculum_data = self._load_curriculum()
        self.module_mapping = self._load_module_mapping()
        self._tfidf_models: Dict[str, Tuple[TfidfVectorizer, Any, List[Dict[str, Any]]]] = {}
        self._init_tfidf_models()

    def _load_curriculum(self) -> Dict[str, Dict[str, Any]]:
        if not self.curriculum_path.exists():
            raise FileNotFoundError(
                f"Curriculum taxonomy not found at {self.curriculum_path}"
            )
        with self.curriculum_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        modules_map = {}
        for mod in data.get("modules", []):
            key = mod.get("module_key")
            modules_map[key] = mod
            for alias in mod.get("aliases", []):
                modules_map[alias] = mod
        return modules_map

    def _load_module_mapping(self) -> Dict[str, str]:
        if not self.modules_path.exists():
            return {}
        with self.modules_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        mapping = {}
        for mod in data.get("modules", []):
            key = mod.get("module_key")
            code = mod.get("module_code")
            if code:
                mapping[code.lower()] = key
                mapping[code] = key
            for alias in mod.get("aliases", []):
                mapping[alias.lower()] = key
                mapping[alias] = key
            mapping[key.lower()] = key
            mapping[key] = key
        return mapping

    def canonicalize_module_key(self, module_key_or_code: str) -> str:
        if not isinstance(module_key_or_code, str) or not module_key_or_code.strip():
            raise ValueError("Module identifier must be a non-empty string")
        raw = module_key_or_code.strip()
        norm = raw.lower()
        if raw in self.module_mapping:
            return self.module_mapping[raw]
        if norm in self.module_mapping:
            return self.module_mapping[norm]
        norm = CANONICAL_MODULE_ALIASES.get(norm, norm)
        if norm in self.curriculum_data:
            return self.curriculum_data[norm]["module_key"]
        return norm

    def _init_tfidf_models(self) -> None:
        """Pre-compute TF-IDF vectorizers for each module's curriculum topics."""
        for mod_key, mod_data in self.curriculum_data.items():
            if mod_key in self._tfidf_models:
                continue
            topics = mod_data.get("topics", [])
            corpus = []
            for t in topics:
                text_parts = [
                    t.get("topic_name", ""),
                    " ".join(t.get("subtopics", [])),
                    " ".join(t.get("keywords", [])),
                    t.get("reference_text", ""),
                ]
                corpus.append(" ".join(text_parts))

            if not corpus:
                continue

            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                lowercase=True,
                max_features=2500,
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)
            self._tfidf_models[mod_key] = (vectorizer, tfidf_matrix, topics)

    def _compute_keyword_score(
        self,
        text_lower: str,
        topic: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        """Compute keyword and technical terminology match score and list matches."""
        matched_terms = []
        keywords = topic.get("keywords", [])
        subtopics = topic.get("subtopics", [])
        topic_name = topic.get("topic_name", "")

        candidates = list(keywords)
        candidates.append(topic_name)
        for st in subtopics:
            candidates.append(st)

        # Sort longer phrases first to capture exact expressions
        candidates.sort(key=lambda s: len(s.split()), reverse=True)

        seen_terms = set()
        total_score = 0.0

        for term in candidates:
            t_clean = term.strip().lower()
            if not t_clean or len(t_clean) < 2 or t_clean in seen_terms:
                continue

            # Word boundary regex for clean phrase matching
            pattern = r"(?:\b|_)" + re.escape(t_clean) + r"(?:\b|_)"
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                seen_terms.add(t_clean)
                matched_terms.append(t_clean)
                # Multi-word matches carry higher informational weight
                words_count = len(t_clean.split())
                weight = 1.0 + (0.5 * (words_count - 1))
                total_score += weight * min(matches, 3)

        # Non-linear saturation: 1 match -> ~0.35, 2 matches -> ~0.58, 4 matches -> ~0.82
        normalized_score = 1.0 - math.exp(-0.40 * total_score)
        return round(float(normalized_score), 4), matched_terms[:10]

    def _compute_tfidf_similarity(
        self,
        clean_text: str,
        module_key: str,
    ) -> Dict[str, float]:
        """Compute cosine similarity between question text and each topic's reference text."""
        canonical_key = self.canonicalize_module_key(module_key)
        if canonical_key not in self._tfidf_models:
            return {}

        vectorizer, matrix, topics = self._tfidf_models[canonical_key]
        if not clean_text.strip():
            return {t["topic_id"]: 0.0 for t in topics}

        try:
            q_vec = vectorizer.transform([clean_text])
            sims = cosine_similarity(q_vec, matrix)[0]
            return {
                topics[i]["topic_id"]: round(float(sims[i]), 4)
                for i in range(len(topics))
            }
        except Exception:
            return {t["topic_id"]: 0.0 for t in topics}

    def _get_m17_signal(
        self,
        module_key: str,
        question_text: str,
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, float]]:
        """Extract existing M17 prediction and topic confidence scores."""
        canonical_key = self.canonicalize_module_key(module_key)
        m17_scores = {}
        m17_result = None

        if not self.m17_predictor:
            return None, m17_scores

        try:
            m17_result = self.m17_predictor.predict(
                module_key=canonical_key,
                question_text=question_text,
                threshold=self.m17_formal_threshold,
            )
            # Check model pipeline classes if available for full probability distribution
            model_pkg = self.m17_predictor.load_model(canonical_key)
            pipeline = model_pkg.get("pipeline")
            classes = model_pkg.get("classes", [])
            clf = pipeline.named_steps.get("clf") if pipeline else None

            if clf and hasattr(clf, "predict_proba"):
                probas = pipeline.predict_proba([question_text])[0]
                for idx, cls_name in enumerate(classes):
                    slug_id = _slug(str(cls_name))
                    m17_scores[slug_id] = round(float(probas[idx]), 4)
            elif m17_result:
                best_topic = m17_result.get("candidate_topic")
                conf = m17_result.get("confidence_score") or 0.0
                if best_topic:
                    m17_scores[_slug(best_topic)] = conf

        except (ModelNotFoundError, Exception):
            m17_result = None
            m17_scores = {}

        return m17_result, m17_scores

    def rank_candidates(
        self,
        module_key: str,
        question_text: str,
        question_id: Optional[str] = None,
        source_type: Optional[str] = "authentic",
    ) -> Dict[str, Any]:
        """Generate top-3 ranked topic candidates with conservative suggestion status."""
        canonical_key = self.canonicalize_module_key(module_key)
        prep = AuthenticQuestionPreprocessor.preprocess(question_text)
        original_text = prep["original_text"]
        normalized_text = prep["normalized_text"]
        is_empty = prep["is_empty"]

        if canonical_key not in self.curriculum_data:
            raise ValueError(f"Unknown module for topic ranking: '{module_key}'")

        module_info = self.curriculum_data[canonical_key]
        topics = module_info.get("topics", [])

        # Base structure
        result: Dict[str, Any] = {
            "question_id": question_id,
            "module_key": canonical_key,
            "original_text_reference": original_text[:120] + "..." if len(original_text) > 120 else original_text,
            "cleaned_text": normalized_text,
            "source_type": source_type,
            "ranker_version": "m20.5_hybrid_v1",
            "score_type": "hybrid_ranking_score",
            "is_calibrated_probability": False,
            "candidate_topics": [],
            "suggestion_status": "abstained",
            "abstained": True,
            "abstention_reason": None,
            "taxonomy_verification_status": "unverified",
            "human_verification_status": "unverified",
            "m17_prediction": None,
            # Formal automated classification fields (strict M17 0.38 threshold preservation)
            "formal_classification": {
                "topic_id": None,
                "classification_method": "unclassified",
                "confidence_score": None,
                "verification_status": "unverified",
                "abstained": True,
            },
        }

        if is_empty or not normalized_text.strip():
            result["abstention_reason"] = "Question text is empty or contains no usable alphanumeric content"
            return result

        # 1. Compute Signal C (TF-IDF)
        tfidf_scores = self._compute_tfidf_similarity(normalized_text, canonical_key)

        # 2. Compute Signal A (M17 Prediction)
        m17_result, m17_topic_scores = self._get_m17_signal(canonical_key, normalized_text)
        result["m17_prediction"] = m17_result

        # Update formal classification fields based strictly on M17 0.38 threshold
        if (
            m17_result
            and not m17_result.get("abstained")
            and m17_result.get("provisional_topic_id")
            and (m17_result.get("confidence_score") or 0.0) >= self.m17_formal_threshold
        ):
            result["formal_classification"] = {
                "topic_id": m17_result.get("provisional_topic_id"),
                "classification_method": "m17_provisional",
                "confidence_score": m17_result.get("confidence_score"),
                "verification_status": "unverified",
                "abstained": False,
            }

        # 3. Score all curriculum topics
        candidate_list = []
        has_m17 = bool(m17_topic_scores)

        for topic in topics:
            t_id = topic["topic_id"]
            t_name = topic["topic_name"]
            t_slug = _slug(t_name)

            # Signal B: Keyword match
            kw_score, matched_terms = self._compute_keyword_score(normalized_text, topic)

            # Signal C: TF-IDF similarity
            tfidf_score = tfidf_scores.get(t_id, 0.0)

            # Signal A: M17 score
            m17_score = m17_topic_scores.get(t_slug, m17_topic_scores.get(t_id, 0.0))

            # Hybrid score synthesis: transparent weighted combination
            if has_m17:
                combined_score = (0.42 * kw_score) + (0.33 * tfidf_score) + (0.25 * m17_score)
            else:
                combined_score = (0.55 * kw_score) + (0.45 * tfidf_score)

            combined_score = round(float(combined_score), 4)

            # Synthesize human-readable explanation
            reasons = []
            if matched_terms:
                reasons.append(f"Matched terminology: {', '.join(repr(m) for m in matched_terms[:4])}")
            if tfidf_score > 0.08:
                reasons.append(f"TF-IDF similarity: {tfidf_score:.2f}")
            if m17_score > 0.05:
                reasons.append(f"M17 model score: {m17_score:.2f}")

            explanation = (
                "; ".join(reasons)
                if reasons
                else "Low semantic relevance to topic curriculum reference."
            )

            candidate_list.append({
                "topic_id": t_id,
                "topic_name": t_name,
                "combined_score": combined_score,
                "method_scores": {
                    "keyword_term_match": kw_score,
                    "tfidf_semantic": tfidf_score,
                    "m17_model": m17_score,
                },
                "matched_terms": matched_terms,
                "explanation": explanation,
                "provisional_topic_id": f"provisional_{t_slug}",
            })

        # Sort descending by combined_score, then tie-break by topic_id
        candidate_list.sort(key=lambda c: (-c["combined_score"], c["topic_id"]))
        top_candidates = candidate_list[:3]

        best_score = top_candidates[0]["combined_score"] if top_candidates else 0.0
        best_candidate = top_candidates[0] if top_candidates else None

        # Conservative Abstention / Suggestion Rules
        if best_candidate and best_score >= self.suggestion_threshold:
            # Strong suggestion for lecturer review
            result["suggestion_status"] = "suggested_for_review"
            result["abstained"] = False
            result["abstention_reason"] = None
        elif best_candidate and best_score >= self.low_confidence_threshold:
            # Low confidence suggestion: visible for human review but flagged
            result["suggestion_status"] = "low_confidence_review"
            result["abstained"] = False
            result["abstention_reason"] = (
                f"Candidate match score ({best_score:.2f}) below standard suggestion threshold "
                f"({self.suggestion_threshold:.2f}); flagged for lecturer review"
            )
        else:
            # Abstention: no candidate surpasses minimum relevance
            result["suggestion_status"] = "abstained"
            result["abstained"] = True
            result["abstention_reason"] = (
                f"Top candidate match score ({best_score:.2f}) is below minimum abstention threshold "
                f"({self.low_confidence_threshold:.2f})"
            )

        result["candidate_topics"] = top_candidates
        return result
