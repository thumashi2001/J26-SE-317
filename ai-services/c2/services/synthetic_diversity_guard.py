
"""M11.3.3B - Synthetic question diversity and uniqueness controls.

Read-only auditing. Does not generate, approve, or export papers.
"""

from collections import Counter

from services.synthetic_content_bank import SyntheticContentBank


class SyntheticDiversityGuard:
    def __init__(self, content_bank=None):
        self.content_bank = (
            content_bank if content_bank is not None
            else SyntheticContentBank()
        )

    @staticmethod
    def _questions(paper):
        if not isinstance(paper, dict):
            raise ValueError("Paper must be an object")

        sections = paper.get("questions")

        if not isinstance(sections, list):
            raise ValueError("Missing paper questions")

        questions = []

        for section in sections:
            if not isinstance(section, dict):
                raise ValueError("Invalid main question")

            subs = section.get("subquestions")

            if not isinstance(subs, list):
                raise ValueError("Invalid subquestions")

            for sub in subs:
                if not isinstance(sub, dict):
                    raise ValueError("Invalid subquestion")

                question = sub.get("question")

                if not isinstance(question, dict):
                    raise ValueError("Invalid question record")

                questions.append(question)

        return questions

    @staticmethod
    def _signature(question):
        """Extract source scenario/task identity, not only text."""
        provenance = question.get("generation_provenance")

        if not isinstance(provenance, dict):
            raise ValueError("Missing generation provenance")

        if provenance.get("generator") != (
            "c2_synthetic_content_adapter_v1"
        ):
            raise ValueError(
                "Question is not from the evidence content adapter"
            )

        fields = (
            "content_bank_id",
            "topic_index",
            "scenario_index",
            "task_index",
        )

        values = []

        for field in fields:
            value = provenance.get(field)

            if field.endswith("_index"):
                if type(value) is not int or value <= 0:
                    raise ValueError(
                        f"Invalid provenance field: {field}"
                    )
            elif not isinstance(value, str) or not value:
                raise ValueError(
                    f"Invalid provenance field: {field}"
                )

            values.append(value)

        return tuple(values)

    def capacity_report(self, module_key):
        bank = self.content_bank.load()

        module = next(
            (
                item for item in bank["modules"]
                if item["module_key"] == module_key
            ),
            None,
        )

        if module is None:
            raise ValueError(
                f"Unknown content bank module: {module_key}"
            )

        topic_count = len(module["topics"])

        scenario_count = sum(
            len(topic["scenarios"])
            for topic in module["topics"]
        )

        task_count = sum(
            len(topic["tasks"])
            for topic in module["topics"]
        )

        pair_count = sum(
            len(topic["scenarios"]) * len(topic["tasks"])
            for topic in module["topics"]
        )

        return {
            "module_key": module_key,
            "topic_count": topic_count,
            "scenario_count": scenario_count,
            "authored_task_count": task_count,
            "distinct_pair_capacity": pair_count,
            "max_questions_with_unique_scenarios": scenario_count,
            "academically_verified": False,
            "production_ready": False,
        }

    def preflight(self, module_key, question_count):
        if type(question_count) is not int or question_count <= 0:
            raise ValueError(
                "question_count must be a positive integer"
            )

        capacity = self.capacity_report(module_key)

        return {
            **capacity,
            "requested_question_count": question_count,
            "enough_distinct_pairs": (
                capacity["distinct_pair_capacity"]
                >= question_count
            ),
            "enough_distinct_scenarios": (
                capacity["scenario_count"]
                >= question_count
            ),
            "ready_for_unique_scenario_paper": (
                capacity["scenario_count"]
                >= question_count
            ),
        }

    def audit_paper(self, paper):
        questions = self._questions(paper)

        if not questions:
            raise ValueError("Paper has no questions")

        module_key = paper.get("module_key")

        if not isinstance(module_key, str) or not module_key:
            raise ValueError("Missing paper module key")

        bank = self.content_bank.load()

        module = next(
            (
                item for item in bank["modules"]
                if item["module_key"] == module_key
            ),
            None,
        )

        if module is None:
            raise ValueError("Unknown paper module")

        signatures = []
        scenario_signatures = []
        question_ids = []
        question_texts = []

        for question in questions:
            if question.get("module_key") != module_key:
                raise ValueError("Question module mismatch")

            if question.get("source_type") != "synthetic":
                raise ValueError("Question is not synthetic")

            if (
                question.get("verification_status") != "unverified"
                or question.get("human_review_status") != "pending"
            ):
                raise ValueError("Question review status invalid")

            signature = self._signature(question)
            bank_id, topic_index, scenario_index, task_index = (
                signature
            )

            if bank_id != bank["bank_id"]:
                raise ValueError("Content bank ID mismatch")

            if not 1 <= topic_index <= len(module["topics"]):
                raise ValueError("Invalid topic index")

            topic = module["topics"][topic_index - 1]

            if not 1 <= scenario_index <= len(topic["scenarios"]):
                raise ValueError("Invalid scenario index")

            if not 1 <= task_index <= len(topic["tasks"]):
                raise ValueError("Invalid task index")

            expected_text = (
                f"Scenario: {topic['scenarios'][scenario_index - 1]}"
                f"\nTask: {topic['tasks'][task_index - 1]}"
            )

            if question.get("question_text") != expected_text:
                raise ValueError(
                    "Question text does not match bank provenance"
                )

            signatures.append(signature)
            scenario_signatures.append(signature[:3])
            question_ids.append(question.get("question_id"))
            question_texts.append(question.get("question_text"))

        duplicate_pairs = [
            signature
            for signature, count in Counter(signatures).items()
            if count > 1
        ]

        duplicate_scenarios = [
            signature
            for signature, count in Counter(
                scenario_signatures
            ).items()
            if count > 1
        ]

        duplicate_ids = len(question_ids) != len(
            set(question_ids)
        )

        duplicate_texts = len(question_texts) != len(
            set(question_texts)
        )

        errors = []

        if duplicate_pairs:
            errors.append("Repeated scenario/task pair")

        if duplicate_scenarios:
            errors.append("Repeated scenario within paper")

        if duplicate_ids:
            errors.append("Duplicate question ID")

        if duplicate_texts:
            errors.append("Duplicate question text")

        return {
            "paper_id": paper.get("paper_id"),
            "module_key": module_key,
            "question_count": len(questions),
            "unique_scenario_count": len(
                set(scenario_signatures)
            ),
            "unique_pair_count": len(set(signatures)),
            "duplicate_scenario_count": len(
                duplicate_scenarios
            ),
            "duplicate_pair_count": len(duplicate_pairs),
            "valid": not errors,
            "errors": errors,
            "pair_signatures": signatures,
            "scenario_signatures": scenario_signatures,
        }

    def audit_batch(self, papers):
        if not isinstance(papers, list):
            raise ValueError("papers must be a list")

        reports = []
        seen_pairs = set()
        seen_paper_ids = set()
        errors = []

        for index, paper in enumerate(papers, start=1):
            report = self.audit_paper(paper)
            reports.append(report)

            paper_id = report["paper_id"]

            if not isinstance(paper_id, str) or not paper_id:
                errors.append(
                    f"Paper {index}: missing paper ID"
                )
            elif paper_id in seen_paper_ids:
                errors.append(
                    f"Paper {index}: duplicate paper ID"
                )

            seen_paper_ids.add(paper_id)

            if not report["valid"]:
                errors.append(
                    f"Paper {index}: "
                    + "; ".join(report["errors"])
                )

            for signature in report["pair_signatures"]:
                if signature in seen_pairs:
                    errors.append(
                        f"Paper {index}: repeated pair across batch"
                    )

                seen_pairs.add(signature)

        return {
            "paper_count": len(papers),
            "unique_pair_count": len(seen_pairs),
            "valid": not errors,
            "errors": errors,
            "papers": reports,
            "academic_review_status": "pending",
        }
