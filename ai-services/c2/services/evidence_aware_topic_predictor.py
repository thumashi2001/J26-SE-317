
"""M12.1 - Evidence-aware historical topic study priorities.

Read-only. No synthetic questions or future-exam probabilities.
"""

from services.exam_pattern_analyzer import ExamPatternAnalyzer


class EvidenceAwareTopicPredictor:
    def __init__(self, analyzer=None):
        self.analyzer = (
            analyzer if analyzer is not None
            else ExamPatternAnalyzer()
        )

    def predict(self, module_key):
        analysis = self.analyzer.analyze(module_key)

        topics = analysis["topics"]
        verified_count = topics["verified_classified_questions"]
        total_questions = analysis["total_questions"]
        distinct_papers = analysis["distinct_papers"]
        distinct_years = analysis["distinct_years"]

        coverage = (
            round(verified_count / total_questions, 4)
            if total_questions > 0
            else 0.0
        )

        # The existing analyzer supplies the minimum
        # historical evidence readiness gate.
        ready = analysis["prediction_ready"]

        limitations = list(analysis["limitations"])

        # Additional caution: a small verified subset may
        # misrepresent the actual topic distribution.
        if total_questions > 0 and coverage < 0.8:
            limitations.append(
                "Fewer than 80% of authentic questions have "
                "verified topic labels; observed topic "
                "frequencies may be unrepresentative."
            )

        # Do not publish a ranked prediction unless both
        # historical readiness and topic coverage are adequate.
        ranking_available = (
            ready
            and coverage >= 0.8
            and verified_count > 0
        )

        topic_statistics = []

        for item in topics["statistics"]:
            count = item["question_count"]

            topic_statistics.append({
                "topic_id": item["topic_id"],
                "question_count": count,
                "extracted_marks": item["extracted_marks"],
                "share_of_verified_questions": round(
                    count / verified_count, 4
                ) if verified_count else None,
            })

        if not ranking_available:
            status = "insufficient_evidence"
            study_priorities = []
        else:
            status = "historical_ranking_available"
            study_priorities = [
                {
                    "rank": index,
                    **topic,
                }
                for index, topic in enumerate(
                    topic_statistics,
                    start=1,
                )
            ]

        return {
            "module_key": module_key,
            "analysis_type": "evidence_aware_topic_priorities",
            "status": status,
            "prediction_ready": ranking_available,
            "future_exam_probabilities_available": False,
            "historical_evidence": {
                "authentic_questions": total_questions,
                "distinct_papers": distinct_papers,
                "distinct_years": distinct_years,
                "verified_topic_questions": verified_count,
                "unverified_topic_questions": topics[
                    "without_verified_topic"
                ],
                "verified_topic_coverage": coverage,
                "excluded_synthetic_questions": analysis[
                    "excluded"
                ]["synthetic_questions"],
            },
            "topic_statistics": topic_statistics,
            "study_priorities": study_priorities,
            "limitations": limitations,
            "disclaimer": (
                "Topic counts describe available authentic "
                "historical questions. Rankings, when available, "
                "are study-priority indicators only and do not "
                "predict the next examination or guarantee "
                "topic appearance."
            ),
        }
