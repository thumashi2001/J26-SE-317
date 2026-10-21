
import re
from services.topic_taxonomy import TopicTaxonomy


class TopicClassifier:
    """Rule-based topic classification using syllabus taxonomies."""

    def __init__(self, taxonomy=None, min_confidence=0.5):
        self.taxonomy = taxonomy or TopicTaxonomy()

        if not 0 <= min_confidence <= 1:
            raise ValueError("Invalid confidence threshold")

        self.min_confidence = min_confidence

    @staticmethod
    def normalize(text):
        if not isinstance(text, str):
            raise ValueError("Text must be a string")

        return " ".join(
            re.findall(r"[a-z0-9]+", text.lower())
        )

    @staticmethod
    def contains_phrase(text, phrase):
        return (
            f" {phrase} " in f" {text} "
            if phrase else False
        )

    
    def classify(self, question_id, module_key, question_text):
        if not isinstance(question_id, str) or not question_id.strip():
            raise ValueError("Invalid question ID")

        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("Invalid module key")

        if not isinstance(question_text, str) or not question_text.strip():
            raise ValueError("Invalid question text")

        taxonomy = self.taxonomy.get_module_taxonomy(module_key)

        if taxonomy is None:
            raise ValueError(f"Unknown module: {module_key}")

        result = {
            "question_id": question_id,
            "module_key": module_key,
            "topic_id": None,
            "subtopic": None,
            "classification_method": "unclassified",
            "confidence_score": None,
            "verification_status": "unverified",
        }

        if not self.taxonomy.is_module_ready(module_key):
            return result

        normalized_question = self.normalize(question_text)
        candidates = []

        for topic in taxonomy["topics"]:
            terms = [
                topic["topic_name"],
                *topic["subtopics"],
            ]

            normalized_terms = {
                self.normalize(term)
                for term in terms
                if isinstance(term, str) and term.strip()
            }

            if not normalized_terms:
                continue

            matched_terms = sum(
                self.contains_phrase(normalized_question, term)
                for term in normalized_terms
            )

            if matched_terms == 0:
                continue

            score = matched_terms / len(normalized_terms)
            candidates.append((score, topic))

        if not candidates:
            return result

        candidates.sort(
            key=lambda item: (-item[0], item[1]["topic_id"])
        )

        best_score, best_topic = candidates[0]

        if best_score < self.min_confidence:
            return result

        if (
            len(candidates) > 1
            and abs(best_score - candidates[1][0]) < 1e-9
        ):
            return result

        result.update({
            "topic_id": best_topic["topic_id"],
            "subtopic": None,
            "classification_method": "rule_based",
            "confidence_score": round(best_score, 4),
        })

        return result
