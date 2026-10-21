
from services.topic_classifier import TopicClassifier
from services.topic_classification_validator import (
    TopicClassificationValidator,
)


class BatchTopicClassifier:
    """Classify and validate multiple examination questions."""

    def __init__(self, classifier=None, validator=None):
        self.classifier = (
            classifier if classifier is not None
            else TopicClassifier()
        )

        self.validator = (
            validator if validator is not None
            else TopicClassificationValidator(
                taxonomy=self.classifier.taxonomy
            )
        )

    def classify_questions(self, questions):
        if not isinstance(questions, list):
            raise ValueError("Questions must be a list")

        results = []
        summary = {
            "total_questions": len(questions),
            "classified": 0,
            "unclassified": 0,
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

                classification = self.classifier.classify(
                    question_id=question_id,
                    module_key=module_key,
                    question_text=question_text,
                )

                validation = self.validator.validate(
                    classification
                )

                if not validation["valid"]:
                    summary["invalid"] += 1
                    results.append({
                        "question_id": question_id,
                        "valid": False,
                        "classification": classification,
                        "errors": validation["errors"],
                        "warnings": validation["warnings"],
                    })
                    continue

                if (
                    classification["classification_method"]
                    == "unclassified"
                ):
                    summary["unclassified"] += 1
                else:
                    summary["classified"] += 1

                results.append({
                    "question_id": question_id,
                    "valid": True,
                    "classification": classification,
                    "errors": [],
                    "warnings": validation["warnings"],
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
