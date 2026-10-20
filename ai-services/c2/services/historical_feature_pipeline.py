"""M20: Leak-free chronological feature engineering pipeline.

Prepares causal, session-level topic appearance features exclusively from
authentic examination evidence. Guaranteed to prevent future target examination leakage.
"""

from collections import defaultdict
from services.question_classification_review_repository import (
    QuestionClassificationReviewRepository,
)
from services.student_question_bank import StudentQuestionBank
from services.topic_taxonomy import TopicTaxonomy


class HistoricalFeaturePipeline:
    """Extracts causal historical features per examination session and topic."""

    DEFAULT_RECENCY_DECAY = 0.75  # Exponential decay parameter lambda

    def __init__(self, bank=None, taxonomy=None, reviews_repo=None):
        self.bank = bank if bank is not None else StudentQuestionBank()
        self.taxonomy = taxonomy if taxonomy is not None else TopicTaxonomy()
        if reviews_repo is not None:
            self.reviews_repo = reviews_repo
        else:
            try:
                self.reviews_repo = QuestionClassificationReviewRepository()
            except Exception:
                self.reviews_repo = None

    def build_features_for_module(self, module_key, decay_factor=None):
        """Construct leak-free chronological features for a module."""
        if not isinstance(module_key, str) or not module_key.strip():
            raise ValueError("A valid module_key is required")

        decay = decay_factor if decay_factor is not None else self.DEFAULT_RECENCY_DECAY

        # 1. Load taxonomy topics
        module_tax = self.taxonomy.get_module_taxonomy(module_key)
        if not module_tax:
            return {
                "status": "unsupported_module",
                "module_key": module_key,
                "sessions_count": 0,
                "topics_count": 0,
                "sessions": [],
                "feature_records": [],
                "target_session_features": [],
                "reason": f"No topic taxonomy found for module {module_key}.",
            }

        topics_list = module_tax.get("topics", [])
        topic_ids = [t["topic_id"] for t in topics_list]

        # 2. Load questions and classifications
        module_mapping = self.bank.pipeline.load_module_mapping()
        questions = self.bank._load_json(self.bank.questions_path)
        classification_data = self.bank._load_json(self.bank.classifications_path)

        if not isinstance(questions, list) or not isinstance(classification_data, dict):
            raise ValueError("Invalid dataset structure in question/classification repository")

        # Map verified classifications
        verified_classifications = {}
        for result in classification_data.get("results", []):
            if not isinstance(result, dict) or not result.get("valid"):
                continue
            classification = result.get("classification", {})
            qid = result.get("question_id")
            if (
                isinstance(qid, str)
                and classification.get("verification_status") == "verified"
                and classification.get("topic_id")
            ):
                verified_classifications[qid] = classification

        # Overlay genuine lecturer-reviewed classifications
        if self.reviews_repo is not None:
            try:
                for rev in self.reviews_repo.get_all_reviews():
                    if not isinstance(rev, dict):
                        continue
                    qid = rev.get("question_id")
                    if not qid:
                        continue
                    decision = rev.get("decision")
                    if decision == "approved" and rev.get("topic_id"):
                        verified_classifications[qid] = {
                            "question_id": qid,
                            "module_key": rev.get("module_key"),
                            "topic_id": rev.get("topic_id"),
                            "verification_status": "verified",
                            "reviewer_id": rev.get("reviewer_id"),
                        }
                    elif decision == "rejected":
                        verified_classifications.pop(qid, None)
            except Exception:
                pass

        # Filter authentic questions for this module
        selected_questions = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            if q.get("source_type") != "authentic":
                continue
            code = q.get("module_code")
            if module_mapping.get(code) != module_key:
                continue
            selected_questions.append(q)

        # Leaf question deduplication (prevent double counting)
        parent_ids = {q.get("parent_id") for q in selected_questions if q.get("parent_id")}
        leaf_questions = [
            q for q in selected_questions
            if q.get("question_id") and q.get("question_id") not in parent_ids
        ]

        # Check for zero verified labels
        verified_leaf_questions = [
            q for q in leaf_questions
            if q.get("question_id") in verified_classifications
        ]

        if not verified_leaf_questions:
            return {
                "status": "insufficient_verified_evidence",
                "module_key": module_key,
                "sessions_count": 0,
                "topics_count": len(topic_ids),
                "verified_questions_count": 0,
                "total_questions_count": len(leaf_questions),
                "sessions": [],
                "feature_records": [],
                "target_session_features": [],
                "reason": (
                    "No lecturer-verified topic labels available for this module. "
                    "Features cannot be calculated without verified ground truth."
                ),
            }

        # 3. Group verified questions into chronological examination sessions
        sessions_map = defaultdict(lambda: {
            "session_id": None,
            "paper_id": None,
            "calendar_year": None,
            "examination_type": None,
            "questions": [],
            "topic_occurrences": defaultdict(int),
            "topic_marks": defaultdict(float),
            "total_marks": 0.0,
        })

        for q in verified_leaf_questions:
            pid = q.get("paper_id") or "UNKNOWN_PAPER"
            entry = sessions_map[pid]
            entry["session_id"] = pid
            entry["paper_id"] = pid
            entry["calendar_year"] = q.get("calendar_year") or 0
            entry["examination_type"] = q.get("examination_type", "Regular Final Exam")
            entry["questions"].append(q)

            classification = verified_classifications[q["question_id"]]
            tid = classification["topic_id"]
            entry["topic_occurrences"][tid] += 1

            marks = q.get("marks")
            if (
                isinstance(marks, (int, float))
                and not isinstance(marks, bool)
                and marks > 0
                and q.get("marks_status") == "extracted"
            ):
                entry["topic_marks"][tid] += float(marks)
                entry["total_marks"] += float(marks)

        sorted_sessions = sorted(
            sessions_map.values(),
            key=lambda s: (s["calendar_year"], s["paper_id"]),
        )

        result = self._compute_causal_features(
            module_key=module_key,
            sorted_sessions=sorted_sessions,
            topics_list=topics_list,
            decay=decay,
        )
        result["verified_questions_count"] = len(verified_leaf_questions)
        result["total_questions_count"] = len(leaf_questions)
        return result

    build_features = build_features_for_module

    def _compute_causal_features(self, module_key, sorted_sessions, topics_list, decay=0.75):
        """Pure causal feature calculation from a sorted list of examination sessions."""
        topic_ids = [
            t.get("topic_id") if isinstance(t, dict) else t
            for t in topics_list
        ]

        feature_records = []

        # Running history tracking across sessions
        for t_idx, session in enumerate(sorted_sessions):
            prior_sessions = sorted_sessions[:t_idx]
            prior_count = len(prior_sessions)

            session_id = session.get("paper_id") or session.get("session_id")
            year = session.get("calendar_year") or session.get("academic_year") or 0
            exam_type = session.get("examination_type", "Regular Final Exam")
            session_verified_qs = len(session.get("questions", []))

            # Helper to get occurrences dict
            def get_occurrences(s):
                return s.get("topic_occurrences") or s.get("topics_present", {})

            def get_marks(s):
                return s.get("topic_marks") or s.get("topics_marks", {})

            curr_occ_map = get_occurrences(session)
            curr_marks_map = get_marks(session)

            for topic_id in topic_ids:
                curr_occurrences = curr_occ_map.get(topic_id, 0)
                curr_marks = curr_marks_map.get(topic_id, 0.0)
                y_appeared = 1 if curr_occurrences > 0 else 0

                if prior_count == 0:
                    hist_occurrences = 0
                    hist_freq = 0.0
                    recency_weighted_freq = 0.0
                    sessions_since_last = -1
                    consecutive_apps = 0
                    prior_q_count = 0
                    prior_share_of_qs = 0.0
                    prior_marks_share = 0.0
                else:
                    prior_appearances = [
                        1 if get_occurrences(s).get(topic_id, 0) > 0 else 0
                        for s in prior_sessions
                    ]
                    hist_occurrences = sum(prior_appearances)
                    hist_freq = round(hist_occurrences / prior_count, 4)

                    weights = [decay ** (prior_count - 1 - i) for i in range(prior_count)]
                    sum_weights = sum(weights)
                    weighted_sum = sum(
                        weights[i] * prior_appearances[i] for i in range(prior_count)
                    )
                    recency_weighted_freq = round(weighted_sum / sum_weights, 4) if sum_weights > 0 else 0.0

                    if hist_occurrences == 0:
                        sessions_since_last = -1
                    else:
                        last_seen_idx = max(
                            i for i, app in enumerate(prior_appearances) if app == 1
                        )
                        sessions_since_last = prior_count - 1 - last_seen_idx

                    consecutive_apps = 0
                    for app in reversed(prior_appearances):
                        if app == 1:
                            consecutive_apps += 1
                        else:
                            break

                    prior_q_count = sum(
                        get_occurrences(s).get(topic_id, 0) for s in prior_sessions
                    )
                    total_prior_qs = sum(
                        len(s.get("questions", [])) or s.get("total_questions", 1)
                        for s in prior_sessions
                    ) or 1
                    prior_share_of_qs = round(prior_q_count / total_prior_qs, 4)

                    prior_topic_marks = sum(
                        get_marks(s).get(topic_id, 0.0) for s in prior_sessions
                    )
                    total_prior_marks = sum(
                        s.get("total_marks", 0.0) for s in prior_sessions
                    ) or 1.0
                    prior_marks_share = round(prior_topic_marks / total_prior_marks, 4)

                feature_records.append({
                    "session_id": session_id,
                    "calendar_year": year,
                    "examination_type": exam_type,
                    "topic_id": topic_id,
                    "prior_sessions_count": prior_count,
                    "historical_occurrences_count": hist_occurrences,
                    "historical_frequency": hist_freq,
                    "recency_weighted_frequency": recency_weighted_freq,
                    "sessions_since_last_appearance": sessions_since_last,
                    "consecutive_appearances": consecutive_apps,
                    "prior_verified_questions_count": prior_q_count,
                    "prior_share_of_questions": prior_share_of_qs,
                    "prior_marks_share": prior_marks_share,
                    "target_appeared": y_appeared,
                    "target_question_count": curr_occurrences,
                    "target_marks": curr_marks,
                })

        # Target session T+1 features
        total_sessions = len(sorted_sessions)
        target_session_features = []

        def get_all_occ(s):
            return s.get("topic_occurrences") or s.get("topics_present", {})

        def get_all_m(s):
            return s.get("topic_marks") or s.get("topics_marks", {})

        for topic_id in topic_ids:
            all_appearances = [
                1 if get_all_occ(s).get(topic_id, 0) > 0 else 0
                for s in sorted_sessions
            ]
            hist_occurrences = sum(all_appearances)
            hist_freq = round(hist_occurrences / total_sessions, 4) if total_sessions > 0 else 0.0

            weights = [decay ** (total_sessions - 1 - i) for i in range(total_sessions)]
            sum_weights = sum(weights)
            weighted_sum = sum(
                weights[i] * all_appearances[i] for i in range(total_sessions)
            )
            recency_weighted_freq = round(weighted_sum / sum_weights, 4) if sum_weights > 0 else 0.0

            if hist_occurrences == 0:
                sessions_since_last = -1
            else:
                last_seen_idx = max(
                    i for i, app in enumerate(all_appearances) if app == 1
                )
                sessions_since_last = total_sessions - 1 - last_seen_idx

            consecutive_apps = 0
            for app in reversed(all_appearances):
                if app == 1:
                    consecutive_apps += 1
                else:
                    break

            prior_q_count = sum(get_all_occ(s).get(topic_id, 0) for s in sorted_sessions)
            total_prior_qs = sum(
                len(s.get("questions", [])) or s.get("total_questions", 1)
                for s in sorted_sessions
            ) or 1
            prior_share_of_qs = round(prior_q_count / total_prior_qs, 4)

            prior_topic_marks = sum(get_all_m(s).get(topic_id, 0.0) for s in sorted_sessions)
            total_prior_marks = sum(s.get("total_marks", 0.0) for s in sorted_sessions) or 1.0
            prior_marks_share = round(prior_topic_marks / total_prior_marks, 4)

            target_session_features.append({
                "topic_id": topic_id,
                "prior_sessions_count": total_sessions,
                "historical_occurrences_count": hist_occurrences,
                "historical_frequency": hist_freq,
                "recency_weighted_frequency": recency_weighted_freq,
                "sessions_since_last_appearance": sessions_since_last,
                "consecutive_appearances": consecutive_apps,
                "prior_verified_questions_count": prior_q_count,
                "prior_share_of_questions": prior_share_of_qs,
                "prior_marks_share": prior_marks_share,
            })

        return {
            "status": "success",
            "module_key": module_key,
            "sessions_count": len(sorted_sessions),
            "topics_count": len(topic_ids),
            "sessions": [
                {
                    "session_id": s.get("paper_id") or s.get("session_id"),
                    "calendar_year": s.get("calendar_year") or s.get("academic_year"),
                    "examination_type": s.get("examination_type", "Regular Final Exam"),
                    "verified_questions_count": len(s.get("questions", [])) or s.get("total_questions", 0),
                    "confirmed_marks": s.get("total_marks", 0.0),
                    "topics_present": s.get("topics_present") or {k: v for k, v in (s.get("topic_occurrences") or {}).items() if v > 0},
                }
                for s in sorted_sessions
            ],
            "feature_records": feature_records,
            "target_session_features": target_session_features,
            "leakage_safeguard": "strictly_causal_no_future_leakage",
        }
