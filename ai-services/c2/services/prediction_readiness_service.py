"""M20: Module-level examination topic prediction readiness assessment."""

from services.exam_pattern_analyzer import ExamPatternAnalyzer
from services.topic_taxonomy import TopicTaxonomy


# Readiness State Definitions
STATUS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
STATUS_AWAITING_VERIFICATION = "awaiting_lecturer_verification"
STATUS_HISTORICAL_ANALYSIS_READY = "historical_analysis_ready"
STATUS_EXPERIMENTAL_PREDICTION_READY = "experimental_prediction_ready"
STATUS_VALIDATED_PREDICTION_READY = "validated_prediction_ready"

ALL_READINESS_STATUSES = [
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_AWAITING_VERIFICATION,
    STATUS_HISTORICAL_ANALYSIS_READY,
    STATUS_EXPERIMENTAL_PREDICTION_READY,
    STATUS_VALIDATED_PREDICTION_READY,
]


class PredictionReadinessAssessor:
    """
    Assesses whether an authentic past-paper module dataset has sufficient
    verified chronological evidence to support descriptive frequency analysis,
    experimental topic prediction, or validated future-exam estimation.
    """

    MIN_PAPERS_FOR_PREDICTION = 3
    MIN_YEARS_FOR_PREDICTION = 2
    MIN_COVERAGE_THRESHOLD = 0.80
    MIN_SESSIONS_FOR_EXPERIMENTAL = 4
    MIN_SESSIONS_FOR_VALIDATION = 6

    def __init__(self, analyzer=None, taxonomy=None):
        self.analyzer = (
            analyzer if analyzer is not None
            else ExamPatternAnalyzer()
        )
        self.taxonomy = (
            taxonomy if taxonomy is not None
            else TopicTaxonomy()
        )

    def assess_module(self, module_key, pattern_analysis=None, evaluation_report=None):
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("A valid module_key is required")

        analysis = (
            pattern_analysis
            if pattern_analysis is not None
            else self.analyzer.analyze(module_key)
        )

        total_questions = analysis.get("total_questions", 0)
        distinct_papers = analysis.get("distinct_papers", 0)
        distinct_years = [str(y) for y in analysis.get("distinct_years", [])]
        unavailable_years = [str(y) for y in analysis.get("unavailable_years", [])]
        papers_inventory = analysis.get("papers_inventory", [])

        topics = analysis.get("topics", {})
        verified_count = topics.get("verified_classified_questions", 0)
        provisional_count = topics.get("provisional_classified_questions", 0)
        unverified_count = topics.get("unclassified_questions", 0)

        coverage = (
            round(verified_count / total_questions, 4)
            if total_questions > 0
            else 0.0
        )

        # Check syllabus taxonomy verification status
        module_tax = self.taxonomy.get_module_taxonomy(module_key)
        taxonomy_verified = (
            module_tax is not None
            and module_tax.get("verification_status") == "verified"
            and len(module_tax.get("topics", [])) > 0
        )
        taxonomy_topics_count = len(module_tax.get("topics", [])) if module_tax else 0

        missing_requirements = []
        reasons_unavailable = []
        permitted_outputs = ["historical_inventory", "authentic_practice"]

        # Rule 1: Insufficient basic papers or questions
        if distinct_papers < 2 or len(distinct_years) < 1 or total_questions == 0:
            status = STATUS_INSUFFICIENT_EVIDENCE
            if total_questions == 0:
                missing_requirements.append("Authentic examination question repository")
                reasons_unavailable.append("Zero authentic past-paper questions ingested for this module.")
            else:
                missing_requirements.append("Minimum 2 distinct historical examination sessions")
                reasons_unavailable.append(
                    f"Only {distinct_papers} examination paper available; longitudinal analysis requires multiple sessions."
                )

        # Rule 2: Sufficient papers exist, but awaiting lecturer verification
        elif not taxonomy_verified:
            status = STATUS_AWAITING_VERIFICATION
            missing_requirements.append("Lecturer-approved syllabus topic taxonomy")
            missing_requirements.append("Lecturer verification of historical question classifications")
            reasons_unavailable.append(
                "Curriculum topic taxonomy is currently unverified by lecturers. Syllabus approval is required before topic classification can be locked."
            )
            reasons_unavailable.append(
                f"Currently 0 of {total_questions} questions have verified topic assignments. Unverified provisional ML outputs cannot be treated as ground truth."
            )
            permitted_outputs.append("provisional_suggestions")

        elif coverage < self.MIN_COVERAGE_THRESHOLD or verified_count == 0:
            status = STATUS_AWAITING_VERIFICATION
            missing_requirements.append(
                f"Verified topic coverage >= {int(self.MIN_COVERAGE_THRESHOLD * 100)}% (current: {coverage * 100:.1f}%)"
            )
            reasons_unavailable.append(
                f"Only {verified_count} of {total_questions} questions ({coverage * 100:.1f}%) are lecturer-verified. Incomplete verification risks severe sampling bias."
            )
            permitted_outputs.append("provisional_suggestions")

        # Rule 3: Taxonomy verified & coverage >= 80%, but fewer than 3 papers or 1 year
        elif distinct_papers < self.MIN_PAPERS_FOR_PREDICTION or len(distinct_years) < self.MIN_YEARS_FOR_PREDICTION:
            status = STATUS_HISTORICAL_ANALYSIS_READY
            missing_requirements.append(
                f"Minimum {self.MIN_PAPERS_FOR_PREDICTION} distinct examination sessions (current: {distinct_papers})"
            )
            if len(distinct_years) < self.MIN_YEARS_FOR_PREDICTION:
                missing_requirements.append(
                    f"Minimum {self.MIN_YEARS_FOR_PREDICTION} distinct academic years (current: {len(distinct_years)})"
                )
            reasons_unavailable.append(
                "Evidence supports descriptive historical frequency analysis, but independent historical sessions are insufficient for predictive modeling."
            )
            permitted_outputs.append("descriptive_topic_frequency")

        # Rule 4 & 5: Prediction readiness
        else:
            # Automatic promotion to validated_prediction_ready is strictly forbidden by session count alone.
            # It requires verified out-of-sample walk-forward evaluation, adequate independent observations,
            # and defensible empirical probability calibration (Brier score evaluated).
            has_valid_evaluation = (
                isinstance(evaluation_report, dict)
                and evaluation_report.get("is_evaluable") is True
                and evaluation_report.get("status") == "evaluated"
                and evaluation_report.get("calibration_verified") is True
            )

            if distinct_papers >= self.MIN_SESSIONS_FOR_VALIDATION and has_valid_evaluation:
                status = STATUS_VALIDATED_PREDICTION_READY
                permitted_outputs.extend([
                    "descriptive_topic_frequency",
                    "experimental_topic_priorities",
                    "calibrated_appearance_probabilities",
                ])
            elif distinct_papers >= self.MIN_SESSIONS_FOR_EXPERIMENTAL:
                status = STATUS_EXPERIMENTAL_PREDICTION_READY
                permitted_outputs.extend([
                    "descriptive_topic_frequency",
                    "experimental_topic_priorities",
                ])
                if distinct_papers >= self.MIN_SESSIONS_FOR_VALIDATION:
                    missing_requirements.append(
                        "Demonstrated out-of-sample walk-forward validation and empirical probability calibration"
                    )
                    reasons_unavailable.append(
                        "Session count threshold is met, but validated prediction requires genuine out-of-sample evaluation "
                        "and probability calibration on verified historical examination sessions."
                    )
            else:
                status = STATUS_HISTORICAL_ANALYSIS_READY
                missing_requirements.append(
                    f"Minimum {self.MIN_SESSIONS_FOR_EXPERIMENTAL} historical sessions for experimental train/test splits (current: {distinct_papers})"
                )
                reasons_unavailable.append(
                    "Session count allows descriptive historical analysis, but cannot support chronological train/test separation."
                )
                permitted_outputs.append("descriptive_topic_frequency")

        is_prediction_eligible = status in {
            STATUS_EXPERIMENTAL_PREDICTION_READY,
            STATUS_VALIDATED_PREDICTION_READY,
        }

        return {
            "module_key": module_key,
            "status": status,
            "readiness_status": status,
            "is_prediction_eligible": is_prediction_eligible,
            "verified_question_count": verified_count,
            "provisional_question_count": provisional_count,
            "unverified_question_count": unverified_count,
            "total_eligible_question_count": total_questions,
            "distinct_historical_papers": distinct_papers,
            "available_years": distinct_years,
            "unavailable_years": unavailable_years,
            "evidence_coverage": coverage,
            "coverage_threshold": self.MIN_COVERAGE_THRESHOLD,
            "min_papers_threshold": self.MIN_PAPERS_FOR_PREDICTION,
            "min_years_threshold": self.MIN_YEARS_FOR_PREDICTION,
            "taxonomy_verified": taxonomy_verified,
            "taxonomy_topics_count": taxonomy_topics_count,
            "papers_inventory": papers_inventory,
            "missing_requirements": missing_requirements,
            "reasons_unavailable": reasons_unavailable,
            "permitted_outputs": permitted_outputs,
            "evaluation_eligible": is_prediction_eligible and distinct_papers >= 4,
            "heuristics_metadata": {
                "nature": "configurable_research_heuristics",
                "scientific_guarantee": False,
                "explanation": (
                    "Thresholds (80% verified coverage, minimum 3 papers / 2 years for historical analysis, "
                    "minimum 4 sessions for experimental splits, minimum 6 sessions for walk-forward validation) "
                    "are configurable research heuristics designed to prevent premature fitting on small cohorts, "
                    "not scientifically established universal guarantees of predictive validity. "
                    "Validation strictly requires demonstrated out-of-sample accuracy and probability calibration."
                ),
                "coverage_threshold": self.MIN_COVERAGE_THRESHOLD,
                "min_papers_threshold": self.MIN_PAPERS_FOR_PREDICTION,
                "min_years_threshold": self.MIN_YEARS_FOR_PREDICTION,
                "min_sessions_for_experimental": self.MIN_SESSIONS_FOR_EXPERIMENTAL,
                "min_sessions_for_validation": self.MIN_SESSIONS_FOR_VALIDATION,
            },
            "academic_integrity_notice": (
                "Readiness requires independent examination sessions, approved syllabus taxonomies, "
                "and authentic lecturer verification. Question count is not equated with independent observation count."
            ),
        }

    assess = assess_module

    def assess_all_modules(self):
        """Assess readiness across all eight supported Year 3 modules."""
        module_mapping = self.analyzer.bank.pipeline.load_module_mapping()
        unique_modules = sorted(list(set(module_mapping.values())))

        reports = {}
        for mod in unique_modules:
            reports[mod] = self.assess_module(mod)

        return {
            "schema_version": "1.0",
            "evaluated_modules_count": len(reports),
            "modules": reports,
            "summary": {
                "insufficient_evidence": sum(1 for r in reports.values() if r["readiness_status"] == STATUS_INSUFFICIENT_EVIDENCE),
                "awaiting_verification": sum(1 for r in reports.values() if r["readiness_status"] == STATUS_AWAITING_VERIFICATION),
                "historical_analysis_ready": sum(1 for r in reports.values() if r["readiness_status"] == STATUS_HISTORICAL_ANALYSIS_READY),
                "experimental_prediction_ready": sum(1 for r in reports.values() if r["readiness_status"] == STATUS_EXPERIMENTAL_PREDICTION_READY),
                "validated_prediction_ready": sum(1 for r in reports.values() if r["readiness_status"] == STATUS_VALIDATED_PREDICTION_READY),
            },
        }
