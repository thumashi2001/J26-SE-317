
from services.topic_classifier import TopicClassifier
from services.topic_classification_validator import (
    TopicClassificationValidator,
)


class BatchTopicClassifier:
    """Classify and validate multiple examination questions."""

    def __init__(
        self,
        classifier=None,
        validator=None,
        review_repository=None,
        default_threshold=0.38,
        authentic_only=False,
    ):
        self.classifier = (
            classifier if classifier is not None
            else TopicClassifier()
        )

        self.validator = (
            validator if validator is not None
            else TopicClassificationValidator(
                taxonomy=getattr(self.classifier, "taxonomy", None)
            )
        )

        self.review_repository = review_repository
        self.default_threshold = default_threshold
        self.authentic_only = authentic_only

    def _get_existing_review(self, question_id):
        if not self.review_repository or not question_id:
            return None
        try:
            return self.review_repository.get_review(question_id)
        except Exception:
            return None

    def classify_single(self, question_id, module_key, question_text, source_type=None):
        """Classify a single question using classifier or review record."""
        # 1. Check existing lecturer review decision
        review = self._get_existing_review(question_id)
        if review:
            decision = review.get("decision")
            if decision == "approved":
                return {
                    "question_id": question_id,
                    "module_key": module_key,
                    "topic_id": review.get("topic_id"),
                    "subtopic": review.get("subtopic"),
                    "classification_method": "verified",
                    "confidence_score": 1.0,
                    "verification_status": "verified",
                    "review_metadata": {
                        "decision": "approved",
                        "reviewer_id": review.get("reviewer_id"),
                        "reviewed_at": review.get("reviewed_at"),
                        "review_notes": review.get("review_notes"),
                    },
                }, ["Lecturer-verified topic classification."]
            elif decision == "rejected":
                return {
                    "question_id": question_id,
                    "module_key": module_key,
                    "topic_id": None,
                    "subtopic": None,
                    "classification_method": "unclassified",
                    "confidence_score": None,
                    "verification_status": "rejected",
                    "review_metadata": {
                        "decision": "rejected",
                        "reviewer_id": review.get("reviewer_id"),
                        "reviewed_at": review.get("reviewed_at"),
                        "review_notes": review.get("review_notes"),
                    },
                }, ["Lecturer-rejected classification; unclassified."]

        # 2. Check for empty question text
        clean_text = (question_text or "").strip()
        if not clean_text:
            return {
                "question_id": question_id,
                "module_key": module_key,
                "topic_id": None,
                "subtopic": None,
                "classification_method": "unclassified",
                "confidence_score": None,
                "verification_status": "unverified",
            }, ["Question text is empty; topic classification unassigned."]

        # 3. Model or rule-based inference
        if hasattr(self.classifier, "predict"):
            # M17 ML prediction service
            pred = self.classifier.predict(
                module_key=module_key,
                question_text=clean_text,
                threshold=self.default_threshold,
            )
            abstained = pred.get("abstained", False)
            provisional_topic_id = pred.get("provisional_topic_id")

            if abstained or not provisional_topic_id:
                return {
                    "question_id": question_id,
                    "module_key": module_key,
                    "topic_id": None,
                    "subtopic": None,
                    "classification_method": "unclassified",
                    "confidence_score": None,
                    "raw_confidence_score": pred.get("confidence_score"),
                    "verification_status": "unverified",
                    "candidate_topic": pred.get("candidate_topic"),
                    "abstention_threshold": pred.get("abstention_threshold"),
                    "abstained": True,
                    "model_type": pred.get("model_type"),
                }, ["Topic prediction abstained below conservative threshold; pending lecturer review."]

            else:
                return {
                    "question_id": question_id,
                    "module_key": module_key,
                    "topic_id": provisional_topic_id,
                    "subtopic": None,
                    "classification_method": "m17_provisional",
                    "confidence_score": pred.get("confidence_score"),
                    "verification_status": "unverified",
                    "candidate_topic": pred.get("candidate_topic"),
                    "abstention_threshold": pred.get("abstention_threshold"),
                    "abstained": False,
                    "model_type": pred.get("model_type"),
                }, ["Provisional topic suggestion generated by synthetic M17 model; requires lecturer review."]

        elif hasattr(self.classifier, "classify"):
            # Rule-based classifier
            classification = self.classifier.classify(
                question_id=question_id,
                module_key=module_key,
                question_text=clean_text,
            )
            return classification, []
        else:
            raise ValueError("Classifier must have 'predict' or 'classify' method")

    def classify_questions(self, questions):
        if not isinstance(questions, list):
            raise ValueError("Questions must be a list")

        results = []
        summary = {
            "total_questions": len(questions),
            "authentic_processed": 0,
            "synthetic_excluded": 0,
            "classified": 0,
            "unclassified": 0,
            "abstained": 0,
            "lecturer_verified": 0,
            "lecturer_rejected": 0,
            "empty_text": 0,
            "invalid": 0,
        }

        for index, question in enumerate(questions):
            question_id = None

            try:
                if not isinstance(question, dict):
                    raise ValueError("Question must be an object")

                question_id = question.get("question_id")
                module_key = question.get("module_key")
                question_text = question.get("question_text")
                source_type = question.get("source_type")

                if self.authentic_only and source_type == "synthetic":
                    summary["synthetic_excluded"] += 1
                    continue

                if source_type == "authentic" or source_type is None:
                    summary["authentic_processed"] += 1

                if not (question_text or "").strip():
                    summary["empty_text"] += 1

                classification, extra_warnings = self.classify_single(
                    question_id=question_id,
                    module_key=module_key,
                    question_text=question_text,
                    source_type=source_type,
                )

                validation = self.validator.validate(
                    classification
                )

                all_warnings = list(extra_warnings)
                for w in validation.get("warnings", []):
                    if w not in all_warnings:
                        all_warnings.append(w)

                if not validation["valid"]:
                    summary["invalid"] += 1
                    results.append({
                        "question_id": question_id,
                        "valid": False,
                        "classification": classification,
                        "errors": validation["errors"],
                        "warnings": all_warnings,
                    })
                    continue

                verif_status = classification.get("verification_status")
                method = classification.get("classification_method")

                if verif_status == "verified":
                    summary["lecturer_verified"] += 1
                    summary["classified"] += 1
                elif verif_status == "rejected":
                    summary["lecturer_rejected"] += 1
                    summary["unclassified"] += 1
                elif method == "unclassified":
                    summary["unclassified"] += 1
                    if classification.get("abstained"):
                        summary["abstained"] += 1
                else:
                    summary["classified"] += 1

                results.append({
                    "question_id": question_id,
                    "valid": True,
                    "classification": classification,
                    "errors": [],
                    "warnings": all_warnings,
                })

            except (ValueError, TypeError, KeyError) as error:
                summary["invalid"] += 1
                results.append({
                    "question_id": question_id,
                    "valid": False,
                    "classification": None,
                    "errors": [str(error)],
                    "warnings": [],
                })

        return {
            "summary": summary,
            "results": results,
        }

