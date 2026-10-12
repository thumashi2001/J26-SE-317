
from collections import defaultdict


class ClassificationReport:
    """Generate coverage reports from batch classification results."""

    def generate(self, batch_result, questions=None):
        if not isinstance(batch_result, dict):
            raise ValueError("Batch result must be an object")

        results = batch_result.get("results")

        if not isinstance(results, list):
            raise ValueError("Batch results must contain a results list")

        if questions is not None:
            if not isinstance(questions, list):
                raise ValueError("Questions must be a list")

            if len(questions) != len(results):
                raise ValueError(
                    "Question count does not match classification results"
                )

        summary = {
            "total_questions": len(results),
            "classified": 0,
            "unclassified": 0,
            "invalid": 0,
        }

        modules = defaultdict(
            lambda: {
                "total_questions": 0,
                "classified": 0,
                "unclassified": 0,
                "invalid": 0,
            }
        )

        warnings = []

        for index, result in enumerate(results):
            if not isinstance(result, dict):
                raise ValueError("Invalid classification result")

            classification = result.get("classification")

            module_key = None

            if isinstance(classification, dict):
                module_key = classification.get("module_key")

            if questions is not None:
                question = questions[index]

                if not isinstance(question, dict):
                    raise ValueError("Invalid question record")

                module_key = question.get(
                    "module_key", module_key
                )

            if not isinstance(module_key, str) or not module_key:
                module_key = "unknown"

            module = modules[module_key]
            module["total_questions"] += 1

            if result.get("valid") is not True:
                category = "invalid"

            elif not isinstance(classification, dict):
                category = "invalid"

            elif classification.get("classification_method") == "unclassified":
                category = "unclassified"

            elif classification.get("topic_id") is not None:
                category = "classified"

            else:
                category = "invalid"

            summary[category] += 1
            module[category] += 1

        def percentage(count, total):
            if total == 0:
                return 0.0

            return round((count / total) * 100, 2)

        total = summary["total_questions"]

        summary["classification_coverage_percentage"] = percentage(
            summary["classified"], total
        )

        summary["unclassified_percentage"] = percentage(
            summary["unclassified"], total
        )

        summary["invalid_percentage"] = percentage(
            summary["invalid"], total
        )

        module_reports = {}

        for module_key, counts in sorted(modules.items()):
            module_total = counts["total_questions"]

            module_reports[module_key] = {
                **counts,
                "classification_coverage_percentage": percentage(
                    counts["classified"], module_total
                ),
            }

        if total == 0:
            warnings.append("No questions available for reporting")

        if summary["unclassified"] > 0:
            warnings.append(
                "Some questions remain unclassified. "
                "Check syllabus taxonomy coverage and topic matching."
            )

        if summary["invalid"] > 0:
            warnings.append(
                "Invalid classification records were detected"
            )

        return {
            "schema_version": "1.0",
            "summary": summary,
            "modules": module_reports,
            "warnings": warnings,
        }
