
"""M11.1: Read-only historical examination pattern analysis."""

import json
from collections import Counter, defaultdict
from pathlib import Path

from services.student_question_bank import StudentQuestionBank


class ExamPatternAnalyzer:
    """
    Analyze authentic examination questions only.

    Synthetic questions are excluded. Topic statistics use
    verified topic classifications only. No future-exam
    probabilities are calculated.
    """

    def __init__(
        self,
        questions_path=None,
        classifications_path=None,
        modules_path=None,
    ):
        self.bank = StudentQuestionBank(
            questions_path=questions_path,
            classifications_path=classifications_path,
            modules_path=modules_path,
        )

    @staticmethod
    def _read_json(path):
        with Path(path).open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _valid_marks(question):
        marks = question.get("marks")

        if isinstance(marks, bool):
            return None

        if not isinstance(marks, (int, float)):
            return None

        if marks <= 0:
            return None

        if question.get("marks_status") != "extracted":
            return None

        return marks

    def analyze(self, module_key):
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("A valid module_key is required")

        questions = self._read_json(self.bank.questions_path)
        classification_data = self._read_json(
            self.bank.classifications_path
        )

        if not isinstance(questions, list):
            raise ValueError("Question repository must be a list")

        if not isinstance(classification_data, dict):
            raise ValueError("Classification repository must be an object")

        module_mapping = self.bank.pipeline.load_module_mapping()

        valid_classifications = {}

        for result in classification_data.get("results", []):
            if not isinstance(result, dict):
                continue

            classification = result.get("classification")

            if (
                result.get("valid") is True
                and isinstance(classification, dict)
                and isinstance(result.get("question_id"), str)
            ):
                valid_classifications[
                    result["question_id"]
                ] = classification

        selected = []
        excluded_synthetic = 0
        excluded_other_sources = 0

        for question in questions:
            if not isinstance(question, dict):
                continue

            question_module = module_mapping.get(
                question.get("module_code")
            )

            if question_module != module_key:
                continue

            source_type = question.get("source_type")

            if source_type == "synthetic":
                excluded_synthetic += 1
                continue

            if source_type != "authentic":
                excluded_other_sources += 1
                continue

            selected.append(question)

        # Avoid counting duplicate repository records twice.
        unique_questions = {}
        for question in selected:
            question_id = question.get("question_id")
            if isinstance(question_id, str) and question_id:
                unique_questions.setdefault(question_id, question)

        selected = list(unique_questions.values())

        # Avoid double-counting parent questions and their child subquestions.
        parent_ids = {q.get("parent_id") for q in selected if q.get("parent_id")}
        leaf_questions = [
            q for q in selected
            if q.get("question_id") not in parent_ids
        ]
        selected = leaf_questions

        paper_ids = set()
        paper_metadata = {}
        years = Counter()
        marks_distribution = Counter()
        topic_counts = Counter()
        topic_papers = defaultdict(set)
        topic_yearly = defaultdict(lambda: Counter())
        topic_marks = defaultdict(float)

        provisional_topic_counts = Counter()
        provisional_confidence = defaultdict(list)
        provisional_display_names = {}

        total_extracted_marks = 0
        questions_with_valid_marks = 0
        verified_topic_questions = 0
        provisional_topic_questions = 0
        unclassified_questions = 0

        for question in selected:
            paper_id = question.get("paper_id")
            year = question.get("calendar_year")
            marks = self._valid_marks(question)

            if paper_id:
                pid_str = str(paper_id)
                paper_ids.add(pid_str)
                if pid_str not in paper_metadata:
                    paper_metadata[pid_str] = {
                        "paper_id": pid_str,
                        "calendar_year": year,
                        "source_filename": question.get("source_filename"),
                        "question_count": 0,
                        "extracted_marks_sum": 0,
                    }
                paper_metadata[pid_str]["question_count"] += 1
                if marks is not None:
                    paper_metadata[pid_str]["extracted_marks_sum"] += marks

            if isinstance(year, int) and not isinstance(year, bool):
                years[str(year)] += 1

            if marks is not None:
                questions_with_valid_marks += 1
                total_extracted_marks += marks
                marks_distribution[str(marks)] += 1

            classification = valid_classifications.get(
                question.get("question_id"), {}
            )

            topic_id = classification.get("topic_id")
            verification_status = classification.get(
                "verification_status"
            )

            if (
                isinstance(topic_id, str)
                and topic_id.strip()
                and verification_status == "verified"
            ):
                verified_topic_questions += 1
                topic_counts[topic_id] += 1
                if paper_id:
                    topic_papers[topic_id].add(str(paper_id))
                if isinstance(year, int) and not isinstance(year, bool):
                    topic_yearly[topic_id][str(year)] += 1

                if marks is not None:
                    topic_marks[topic_id] += marks
            elif (
                isinstance(topic_id, str)
                and topic_id.strip()
                and verification_status != "verified"
            ):
                # Provisional AI topic proposal
                provisional_topic_questions += 1
                provisional_topic_counts[topic_id] += 1
                conf = classification.get("confidence_score") or classification.get("raw_confidence_score")
                if conf is not None:
                    provisional_confidence[topic_id].append(conf)
                candidate_name = classification.get("candidate_topic") or topic_id
                provisional_display_names[topic_id] = candidate_name
            else:
                unclassified_questions += 1

        distinct_years = sorted(years.keys())

        # Year span and unavailable examination years
        if distinct_years:
            try:
                min_yr = int(distinct_years[0])
                max_yr = int(distinct_years[-1])
                full_span = [str(y) for y in range(min_yr, max_yr + 1)]
                unavailable_years = [y for y in full_span if y not in distinct_years]
            except (ValueError, TypeError):
                unavailable_years = []
        else:
            unavailable_years = []

        total_papers_count = len(paper_ids)

        topic_statistics = [
            {
                "topic_id": topic_id,
                "question_count": count,
                "extracted_marks": topic_marks[topic_id],
                "papers_count": len(topic_papers[topic_id]),
                "paper_coverage": round(
                    len(topic_papers[topic_id]) / total_papers_count, 4
                ) if total_papers_count > 0 else 0.0,
                # Explicit occurrences for every available year (0 if none in that year)
                "yearly_occurrences": {
                    yr: topic_yearly[topic_id].get(yr, 0)
                    for yr in distinct_years
                },
            }
            for topic_id, count in sorted(
                topic_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

        provisional_statistics = [
            {
                "topic_id": topic_id,
                "candidate_name": provisional_display_names.get(topic_id, topic_id),
                "question_count": count,
                "average_confidence": round(
                    sum(provisional_confidence[topic_id]) / len(provisional_confidence[topic_id]), 4
                ) if provisional_confidence[topic_id] else None,
            }
            for topic_id, count in sorted(
                provisional_topic_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

        limitations = []

        if not selected:
            limitations.append(
                "No authentic examination questions are available."
            )

        if len(paper_ids) < 3:
            limitations.append(
                "Fewer than three distinct authentic papers are "
                "available; historical evidence is limited."
            )

        if len(distinct_years) < 2:
            limitations.append(
                "Multiple examination years are required for "
                "year-over-year trend analysis."
            )

        if verified_topic_questions == 0:
            limitations.append(
                "No verified topic classifications are available; "
                "topic frequency analysis is unavailable."
            )

        if questions_with_valid_marks < len(selected):
            limitations.append(
                "Some question marks are missing or not confirmed "
                "as extracted; marks totals are incomplete."
            )

        return {
            "module_key": module_key,
            "analysis_type": "descriptive_historical",
            "source_filter": "authentic",
            "total_questions": len(selected),
            "distinct_papers": len(paper_ids),
            "paper_ids": sorted(list(paper_ids)),
            "distinct_years": distinct_years,
            "unavailable_years": unavailable_years,
            "questions_by_year": dict(sorted(years.items())),
            "papers_inventory": sorted(
                list(paper_metadata.values()),
                key=lambda p: (p.get("calendar_year") or 0, p.get("paper_id") or ""),
            ),
            "marks": {
                "questions_with_extracted_marks":
                    questions_with_valid_marks,
                "sum_of_extracted_question_marks":
                    total_extracted_marks,
                "ambiguous_marks_questions":
                    len(selected) - questions_with_valid_marks,
                "distribution": dict(
                    sorted(
                        marks_distribution.items(),
                        key=lambda item: float(item[0]),
                    )
                ),
            },
            "topics": {
                "verified_classified_questions":
                    verified_topic_questions,
                "provisional_classified_questions":
                    provisional_topic_questions,
                "without_verified_topic":
                    unclassified_questions + provisional_topic_questions,
                "unclassified_questions":
                    unclassified_questions,
                "statistics": topic_statistics,
                "provisional_statistics": provisional_statistics,
            },
            "excluded": {
                "synthetic_questions": excluded_synthetic,
                "other_source_questions": excluded_other_sources,
            },
            "prediction_ready": (
                len(paper_ids) >= 3
                and len(distinct_years) >= 2
                and verified_topic_questions > 0
            ),
            "limitations": limitations,
        }

